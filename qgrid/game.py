"""Game state, player actions, bandwidth, ICE daemons, shards and scoring."""

import random

from . import enemies as ice
from .levels import (
    EMITTER_CHARS,
    EXIT,
    LEVELS,
    SHARD,
    SPLITTER,
    WALL,
    LevelDef,
    parse_level,
)
from .lore import GHOST_TRANSMISSIONS
from .physics import DIR4, trace_beam

BANDWIDTH_MAX = 100
BANDWIDTH_STEP = 1
SHARD_SCORE = 250
EFFICIENCY_BONUS = 20  # points per action saved under 2x par

DIR_VECTORS: dict[str, tuple[int, int]] = {
    "w": (0, -1),
    "s": (0, 1),
    "a": (-1, 0),
    "d": (1, 0),
}


class Game:
    def __init__(
        self,
        level_index: int,
        bandwidth: int,
        unlocked: int = 0,
        rng_seed: int | None = None,
    ):
        self.level_index = level_index
        self.defn: LevelDef = LEVELS[level_index]
        self.layout = parse_level(self.defn.rows, self.defn.name)
        self.player = self.layout.player_start
        self.mirrors = dict(self.layout.mirrors)
        self.bandwidth = bandwidth
        self.snapshot = bandwidth
        self.unlocked = unlocked
        self.game_over = False
        self.actions = 0
        self.strikes = 0
        self.shards_taken: set[tuple[int, int]] = set()
        self.shards_banked: set[tuple[int, int]] = set()  # carried from prior runs
        self.rng = random.Random(
            rng_seed if rng_seed is not None else level_index * 7919 + 2099
        )
        self.daemons: list[dict] = [
            {
                "kind": kind,
                "pos": pos,
                "dir": self.rng.choice(DIR4),
                "cooldown": 0,
            }
            for pos, kind in self.layout.enemies
        ]
        self.msg = (
            "Inspect the optical layout. Move adjacent to a mirror and rotate it."
        )
        self.trace = trace_beam(self.layout, self.player, self.mirrors)

    # ------------------------------------------------------------------ state

    def refresh(self) -> None:
        self.trace = trace_beam(self.layout, self.player, self.mirrors)

    def all_powered(self) -> bool:
        return self.trace.powered == set(self.layout.receptors)

    def exit_active(self) -> bool:
        return self.all_powered()

    def check_win(self) -> bool:
        return self.player == self.layout.exit_pos and self.exit_active()

    def _terrain(self, x: int, y: int) -> str:
        return self.layout.rows[y][x]

    def passable(self, x: int, y: int) -> bool:
        if not (0 <= x < self.layout.width and 0 <= y < self.layout.height):
            return False
        terrain = self._terrain(x, y)
        return terrain != WALL and terrain not in EMITTER_CHARS

    def _note_power_delta(self, prev: set[tuple[int, int]], verb: str) -> None:
        total = len(self.layout.receptors)
        if self.all_powered():
            self.msg = "ALL RECEPTORS ONLINE - Extraction node E is active. Extract!"
            return
        fresh = self.trace.powered - prev
        remaining = total - len(self.trace.powered)
        if fresh:
            ordered = [p for p in self.layout.receptors if p in fresh]
            idx = self.layout.receptors.index(ordered[0]) + 1
            self.msg = (
                f"Receptor {idx} powered. {remaining} target"
                f"{'s' if remaining != 1 else ''} remaining."
            )
        else:
            self.msg = f"{verb} Target node unpowered. Re-route beam line."

    # ------------------------------------------------------------------ turns

    def _tick(self) -> None:
        """Advance the world one turn after a successful player action."""
        if self.daemons and ice.step_daemons(self):
            self._ice_strike()
        if self.bandwidth <= 0:
            self.game_over = True

    def _ice_strike(self) -> None:
        """A daemon touched the probe: bandwidth cost + recall to entry point."""
        self.bandwidth = max(0, self.bandwidth - ice.ICE_STRIKE_COST)
        self.player = self.layout.player_start
        self.strikes += 1
        self.refresh()
        self.msg = (
            f"ICE STRIKE! -{ice.ICE_STRIKE_COST}% bandwidth. Probe recalled to entry point."
        )

    # ---------------------------------------------------------------- actions

    def do_move(self, dx: int, dy: int) -> str:
        """Attempt to move the probe. Returns 'ok' or 'blocked'."""
        nx, ny = self.player[0] + dx, self.player[1] + dy
        if not (0 <= nx < self.layout.width and 0 <= ny < self.layout.height):
            self.msg = "Blocked: grid boundary."
            return "blocked"
        terrain = self._terrain(nx, ny)
        if terrain == WALL:
            self.msg = "Blocked: mainframe wall."
            return "blocked"
        if terrain in EMITTER_CHARS:
            self.msg = "Blocked: laser emitter housing."
            return "blocked"
        prev = set(self.trace.powered)
        self.player = (nx, ny)
        self.actions += 1
        self.bandwidth = max(0, self.bandwidth - BANDWIDTH_STEP)
        # Teleport pads fold the probe across the room (no extra cost:
        # the fold is part of the step, matching the BFS solver's model).
        if (nx, ny) in self.layout.pads:
            self.player = self.layout.pads[(nx, ny)]
        self.refresh()
        self._pickup_shard()
        terrain = self._terrain(self.player[0], self.player[1])
        if terrain == EXIT and not self.exit_active():
            self.msg = "Extraction node offline. Power all receptors first."
        else:
            self._note_power_delta(prev, "Probe repositioned.")
        self._tick()
        return "ok"

    def do_rotate(self) -> bool:
        """Rotate an adjacent (or underfoot) mirror. Returns True on success."""
        px, py = self.player
        target = None
        if (px, py) in self.mirrors:
            target = (px, py)
        else:
            for dx, dy in DIR4:
                if (px + dx, py + dy) in self.mirrors:
                    target = (px + dx, py + dy)
                    break
        if target is None:
            self.msg = "No optical unit in range. Move adjacent to a mirror."
            return False
        prev = set(self.trace.powered)
        self.mirrors[target] = "/" if self.mirrors[target] == "\\" else "\\"
        self.actions += 1
        self.bandwidth = max(0, self.bandwidth - BANDWIDTH_STEP)
        self.refresh()
        self._note_power_delta(prev, "Optical unit rotated. Beam re-routed.")
        self._tick()
        return True

    def _pickup_shard(self) -> None:
        pos = self.player
        if pos in self.shards_banked or pos not in self.layout.shards:
            return
        self.shards_taken.add(pos)
        n = len(self.shards_taken)
        line = GHOST_TRANSMISSIONS[(self.level_index + n) % len(GHOST_TRANSMISSIONS)]
        self.msg = f"DATASHARD {n} acquired. MIRAGE>> {line}"

    def restart(self) -> None:
        """Reset the current node to its entry state and restore bandwidth."""
        self.player = self.layout.player_start
        self.mirrors = dict(self.layout.mirrors)
        self.bandwidth = self.snapshot
        self.game_over = False
        self.actions = 0
        self.strikes = 0
        self.shards_taken = set()
        self.rng = random.Random(self.level_index * 7919 + 2099)
        self.daemons = [
            {
                "kind": kind,
                "pos": pos,
                "dir": self.rng.choice(DIR4),
                "cooldown": 0,
            }
            for pos, kind in self.layout.enemies
        ]
        self.refresh()
        self.msg = f"Node reset. Bandwidth restored to {self.snapshot}%."

    # ----------------------------------------------------------------- score

    def score(self) -> int:
        par = self.defn.par or self.actions or 1
        efficiency = max(0, 2 * par - self.actions) * EFFICIENCY_BONUS
        return (
            self.bandwidth * 10
            + len(self.shards_taken) * SHARD_SCORE
            + efficiency
        )

    def finish_level(self) -> int:
        """Refresh bandwidth to full and unlock the next node."""
        self.shards_banked |= self.shards_taken
        self.bandwidth = BANDWIDTH_MAX
        self.unlocked = max(self.unlocked, self.level_index + 1)
        return self.bandwidth


def start_bandwidth(defn: LevelDef, carry: int) -> int:
    """Compute the bandwidth a player enters a node with."""
    if defn.bandwidth_start is not None:
        return defn.bandwidth_start
    return max(min(carry, BANDWIDTH_MAX), defn.bandwidth_floor)
