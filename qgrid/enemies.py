"""ICE daemon AI for Quantum Grid 2099: BLACKOUT PROTOCOL.

Turn-based: every successful player action (move or rotate) ticks every
daemon exactly one step. Daemons are light-transparent and cannot stand
on walls, emitters, teleport pads, the extraction node, or each other.

    SENTINEL   patrols a fixed axis, bouncing when blocked.
    HUNTER     chases the probe within 6 cells (greedy step) at HALF SPEED
               (acts every other tick), else wanders.
    CORRUPTOR  walks to the nearest mirror, flips it, then backs off for
               a few ticks (cooldown) so runners can restore optics.

Probe contact (player steps onto a daemon, or a daemon steps onto the
player) triggers an ICE STRIKE: -25% bandwidth, and the striking daemon
is knocked back one cell and stunned for 4 ticks. The probe keeps its
position - recovery is about escaping the daemon's range, not a walk of
shame to the entry point.
"""

from .physics import DIR4

ICE_STRIKE_COST = 25
HUNTER_SENSE_RANGE = 6
DAEMON_STUN_TICKS = 4

ENEMY_BLOCKED_TERRAIN = ("#", ">", "<", "^", "v", "T", "U", "E")


def _pos(en: dict) -> tuple[int, int]:
    return en["pos"]


def cell_blocked_for_enemy(layout, occupied: set[tuple[int, int]], pos) -> bool:
    """True if a daemon cannot occupy `pos` (walls, hardware, pads, exit, allies)."""
    x, y = pos
    if not (0 <= x < layout.width and 0 <= y < layout.height):
        return True
    if layout.rows[y][x] in ENEMY_BLOCKED_TERRAIN:
        return True
    return pos in occupied


def _step_sentinel(layout, en: dict, occupied: set[tuple[int, int]]) -> tuple[int, int] | None:
    """Walk one step along the patrol axis; reverse when blocked. Returns new pos."""
    px, py = _pos(en)
    dx, dy = en["dir"]
    cand = (px + dx, py + dy)
    if cell_blocked_for_enemy(layout, occupied, cand):
        en["dir"] = (-dx, -dy)
        cand = (px - dx, py - dy)
        if cell_blocked_for_enemy(layout, occupied, cand):
            return None
    en["pos"] = cand
    return cand


def _step_hunter(layout, en: dict, player, occupied: set[tuple[int, int]], rng) -> tuple[int, int] | None:
    """Greedy chase within sense range, else deterministic wander. Returns new pos."""
    px, py = _pos(en)
    if player is not None:
        gx, gy = player
        dist = abs(gx - px) + abs(gy - py)
        if dist <= HUNTER_SENSE_RANGE and dist > 0:
            # Prefer the axis with the larger gap; fall back to the other.
            options = []
            if gx != px:
                options.append(((1 if gx > px else -1), 0))
            if gy != py:
                options.append((0, (1 if gy > py else -1)))
            options.sort(key=lambda d: -(abs(gx - (px + d[0])) + abs(gy - (py + d[1]))))
            for dx, dy in options:
                cand = (px + dx, py + dy)
                if not cell_blocked_for_enemy(layout, occupied, cand):
                    en["pos"] = cand
                    en["dir"] = (dx, dy)
                    return cand
            return None
    # Wander: keep heading, bounce off blockers, occasionally turn.
    if rng.random() < 0.35:
        en["dir"] = rng.choice(DIR4)
    dx, dy = en["dir"]
    cand = (px + dx, py + dy)
    if cell_blocked_for_enemy(layout, occupied, cand):
        en["dir"] = (-dx, -dy)
        cand = (px - dx, py - dy)
        if cell_blocked_for_enemy(layout, occupied, cand):
            en["dir"] = rng.choice(DIR4)
            return None
    en["pos"] = cand
    return cand


def _step_corruptor(
    layout, en: dict, mirrors, occupied: set[tuple[int, int]], rng
) -> tuple[int, int] | None:
    """Flip an adjacent mirror, then wander off for a few ticks (cooldown) so
    runners get a window to restore their optics. Returns new pos or None."""
    px, py = _pos(en)
    if en.get("cooldown", 0) > 0:
        en["cooldown"] -= 1
        dx, dy = en["dir"]
        cand = (px + dx, py + dy)
        if cell_blocked_for_enemy(layout, occupied, cand):
            en["dir"] = (-dx, -dy)
            cand = (px - dx, py - dy)
            if cell_blocked_for_enemy(layout, occupied, cand):
                return None
        en["pos"] = cand
        return cand
    # Adjacent mirror (or underfoot): flip it, then back off.
    for dx, dy in DIR4:
        if (px + dx, py + dy) in mirrors:
            mirrors[(px + dx, py + dy)] = (
                "/" if mirrors[(px + dx, py + dy)] == "\\" else "\\"
            )
            en["cooldown"] = 4
            en["dir"] = rng.choice(DIR4)
            return None
    if not mirrors:
        return None
    # Close on the nearest mirror (greedy; ties broken by distance then x, y).
    target = min(
        mirrors,
        key=lambda m: (abs(m[0] - px) + abs(m[1] - py), m[0], m[1]),
    )
    options = []
    if target[0] != px:
        options.append(((1 if target[0] > px else -1), 0))
    if target[1] != py:
        options.append((0, (1 if target[1] > py else -1)))
    options.sort(key=lambda d: -(abs(target[0] - (px + d[0])) + abs(target[1] - (py + d[1]))))
    for dx, dy in options:
        cand = (px + dx, py + dy)
        if not cell_blocked_for_enemy(layout, occupied, cand):
            en["pos"] = cand
            return cand
    return None


def step_daemons(game) -> list[tuple[dict, tuple[int, int]]]:
    """Tick every daemon one step. Returns (daemon, origin) strike pairs.

    Called by Game after every successful player action. Handles daemon-
    daemon collision (later daemons respect earlier positions this tick),
    stun timers and probe contact.
    """
    strikes: list[tuple[dict, tuple[int, int]]] = []
    occupied = {en["pos"] for en in game.daemons}
    for en in game.daemons:
        occupied.discard(en["pos"])
        prev = en["pos"]
        if en.get("stun", 0) > 0:
            en["stun"] -= 1
            occupied.add(prev)
            continue
        if en["kind"] == "hunter":
            # Hunters are fast-minded but slow-footed: they act every other
            # tick, so a running probe can always outrun them.
            en["clock"] = 1 - en.get("clock", 0)
            if en["clock"] == 0:
                occupied.add(prev)
                continue
        if en["kind"] == "sentinel":
            new = _step_sentinel(game.layout, en, occupied)
        elif en["kind"] == "hunter":
            new = _step_hunter(game.layout, en, game.player, occupied, game.rng)
        elif en["kind"] == "corruptor":
            new = _step_corruptor(game.layout, en, game.mirrors, occupied, game.rng)
        else:  # pragma: no cover - kinds are fixed at spawn
            new = None
        if new is None:
            occupied.add(prev)
            continue
        occupied.add(new)
        if new == game.player:
            strikes.append((en, prev))
    return strikes


def knock_back(en: dict, origin: tuple[int, int], player: tuple[int, int], game) -> None:
    """Push a striking daemon off the probe: prefer the cell it came from,
    else any free neighbor. Falls back to stun only."""
    candidates = [origin] if origin != player else []
    px, py = en["pos"]
    candidates += [
        (px + dx, py + dy)
        for dx, dy in DIR4
        if (px + dx, py + dy) != player
    ]
    occupied = {o["pos"] for o in game.daemons} | {game.player}
    for cand in candidates:
        if not cell_blocked_for_enemy(game.layout, occupied, cand):
            en["pos"] = cand
            return
