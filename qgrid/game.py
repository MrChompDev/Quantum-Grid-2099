"""Game state, player actions, bandwidth management and win/lose logic."""

from .levels import EMITTER_CHARS, EXIT, LEVELS, WALL, LevelDef, parse_level
from .physics import DIR4, trace_beam

BANDWIDTH_MAX = 100
BANDWIDTH_STEP = 1
BONUS = 20

DIR_VECTORS: dict[str, tuple[int, int]] = {
    "w": (0, -1),
    "s": (0, 1),
    "a": (-1, 0),
    "d": (1, 0),
}


class Game:
    def __init__(self, level_index: int, bandwidth: int, unlocked: int = 0):
        self.level_index = level_index
        self.defn: LevelDef = LEVELS[level_index]
        self.layout = parse_level(self.defn.rows, self.defn.name)
        self.player = self.layout.player_start
        self.mirrors = dict(self.layout.mirrors)
        self.bandwidth = bandwidth
        self.snapshot = bandwidth
        self.unlocked = unlocked
        self.game_over = False
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
        self.bandwidth = max(0, self.bandwidth - BANDWIDTH_STEP)
        self.refresh()
        terrain = self._terrain(nx, ny)
        if terrain == EXIT and not self.exit_active():
            self.msg = "Extraction node offline. Power all receptors first."
        else:
            self._note_power_delta(prev, "Probe repositioned.")
        if self.bandwidth <= 0:
            self.game_over = True
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
        self.bandwidth = max(0, self.bandwidth - BANDWIDTH_STEP)
        self.refresh()
        self._note_power_delta(prev, "Optical unit rotated. Beam re-routed.")
        if self.bandwidth <= 0:
            self.game_over = True
        return True

    def restart(self) -> None:
        """Reset the current node to its entry state and restore bandwidth."""
        self.player = self.layout.player_start
        self.mirrors = dict(self.layout.mirrors)
        self.bandwidth = self.snapshot
        self.game_over = False
        self.refresh()
        self.msg = f"Node reset. Bandwidth restored to {self.snapshot}%."

    def finish_level(self) -> int:
        """Apply the extraction bonus and unlock the next node."""
        self.bandwidth = min(BANDWIDTH_MAX, self.bandwidth + BONUS)
        self.unlocked = max(self.unlocked, self.level_index + 1)
        return self.bandwidth


def start_bandwidth(defn: LevelDef, carry: int) -> int:
    """Compute the bandwidth a player enters a node with."""
    if defn.bandwidth_start is not None:
        return defn.bandwidth_start
    return max(min(carry, BANDWIDTH_MAX), defn.bandwidth_floor)
