"""ICE daemon AI for Quantum Grid 2099: BLACKOUT PROTOCOL.

Turn-based: every successful player action (move or rotate) ticks every
daemon exactly one step. Daemons are light-transparent and cannot stand
on walls, emitters, teleport pads, the extraction node, or each other.

    SENTINEL   patrols a fixed axis, bouncing when blocked.
    HUNTER     chases the probe within 7 cells (greedy step), else wanders.
    CORRUPTOR  walks to the nearest mirror and flips it while adjacent.

Probe contact (player steps onto a daemon, or a daemon steps onto the
player) triggers an ICE STRIKE: -25% bandwidth and the probe is recalled
to its entry point.
"""

from .physics import DIR4

ICE_STRIKE_COST = 25
HUNTER_SENSE_RANGE = 7

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


def _step_corruptor(layout, en: dict, mirrors, occupied: set[tuple[int, int]]) -> tuple[int, int] | None:
    """Walk to the nearest mirror; flip it when adjacent. Returns new pos or None."""
    px, py = _pos(en)
    # Adjacent mirror (or underfoot): flip it in place.
    for dx, dy in DIR4:
        if (px + dx, py + dy) in mirrors:
            mirrors[(px + dx, py + dy)] = (
                "/" if mirrors[(px + dx, py + dy)] == "\\" else "\\"
            )
            en["cooldown"] = 2
            return None
    if en.get("cooldown", 0) > 0:
        en["cooldown"] -= 1
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


def step_daemons(game) -> bool:
    """Tick every daemon one step. Returns True if the probe was struck.

    Called by Game after every successful player action. Handles daemon-
    daemon collision (later daemons respect earlier positions this tick)
    and probe contact.
    """
    struck = False
    occupied = {en["pos"] for en in game.daemons}
    for en in game.daemons:
        occupied.discard(en["pos"])
        prev = en["pos"]
        if en["kind"] == "sentinel":
            new = _step_sentinel(game.layout, en, occupied)
        elif en["kind"] == "hunter":
            new = _step_hunter(game.layout, en, game.player, occupied, game.rng)
        elif en["kind"] == "corruptor":
            new = _step_corruptor(game.layout, en, game.mirrors, occupied)
        else:  # pragma: no cover - kinds are fixed at spawn
            new = None
        if new is None:
            occupied.add(prev)
            continue
        occupied.add(new)
        if new == game.player:
            struck = True
    return struck
