"""ICE daemon AI for Quantum Grid 2099: BLACKOUT PROTOCOL.

Turn-based: every successful player action (move or rotate) ticks every
daemon exactly one step. Daemons are light-transparent and cannot stand
on walls, emitters, teleport pads, the extraction node, or each other.

    SENTINEL   patrols a fixed axis, bouncing when blocked.
    HUNTER     chases the probe within 6 cells (greedy step) at HALF SPEED
               (acts every other tick), else wanders.
    CORRUPTOR  walks to the nearest mirror, flips it, then backs off for
               a few ticks (cooldown) so runners can restore optics.
    WRAITH     phase ghost: slides THROUGH walls and hardware, drifting
               toward the probe within 8 cells at one step per THIRD
               tick. Cover means nothing; keep moving.
    LANCER     lane charger: locks onto any probe sharing its row/column
               with clear sight and dashes TWO cells per tick; without a
               lane it slows to an every-other-tick wander.
    VOLT       static ward: never moves. Every other tick it pulses a
               charge field into its four open adjacent cells - a probe
               standing in the field takes the strike (and the pulse
               stuns the ward for four ticks: your window to work).

Probe contact (player steps onto a daemon, or a daemon steps onto the
player, or a volt field zaps the player) triggers an ICE STRIKE: -25%
bandwidth, and the striking daemon is knocked back one cell and stunned
for 4 ticks. The probe keeps its position - recovery is about escaping
the daemon's range, not a walk of shame to the entry point.
"""

from .physics import DIR4

ICE_STRIKE_COST = 25
HUNTER_SENSE_RANGE = 6
WRAITH_SENSE_RANGE = 8
DAEMON_STUN_TICKS = 4
VOLT_PULSE_CADENCE = 2  # pulse every other tick
VOLT_FIELD_TICKS = 2  # renders the charge field stays visible

ENEMY_BLOCKED_TERRAIN = ("#", ">", "<", "^", "v", "T", "U", "E")

# Cells that break a lancer's line of sight (optical hardware + structure).
SIGHT_BLOCKERS = ("#", ">", "<", "^", "v", "/", "\\", "+")


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


def _wraith_free(layout, occupied: set[tuple[int, int]], pos) -> bool:
    """True if a wraith may occupy `pos`: it phases through walls and
    hardware, stopped only by the perimeter and other daemons."""
    x, y = pos
    if not (1 <= x < layout.width - 1 and 1 <= y < layout.height - 1):
        return False
    return pos not in occupied


def _lane_sight(
    layout, origin: tuple[int, int], target: tuple[int, int], mirrors
) -> tuple[int, int] | None:
    """Direction from `origin` along which `target` is visible with clear
    line of sight. Walls, emitters and optics block sight; pads, shards,
    receptors and the exit do not. Returns (dx, dy) or None."""
    for dx, dy in DIR4:
        x, y = origin
        while True:
            x += dx
            y += dy
            if not (0 <= x < layout.width and 0 <= y < layout.height):
                break
            spot = (x, y)
            if spot == target:
                return (dx, dy)
            if spot in mirrors or layout.rows[y][x] in SIGHT_BLOCKERS:
                break
    return None


def _step_sentinel(
    layout, en: dict, occupied: set[tuple[int, int]]
) -> tuple[int, int] | None:
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


def _step_hunter(
    layout, en: dict, player, occupied: set[tuple[int, int]], rng
) -> tuple[int, int] | None:
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
    layout, en: dict, mirrors, player, occupied: set[tuple[int, int]], rng
) -> tuple[int, int] | None:
    """Flip an adjacent mirror, wander off for a few ticks (cooldown), then
    seek a DIFFERENT mirror - no single optic ever gets pinned (with two or
    more mirrors, every mirror gets stability windows). A mirror the probe
    is holding (standing on or adjacent to) is protected: the runner's
    hands are literally on the optic. Returns new pos or None."""
    px, py = _pos(en)
    last = en.get("last_target")
    if en.get("cooldown", 0) > 0:
        en["cooldown"] -= 1
        # wander AWAY from the last flipped mirror
        options = []
        if last is not None:
            if px != last[0]:
                options.append((1 if px > last[0] else -1, 0))
            if py != last[1]:
                options.append((0, 1 if py > last[1] else -1))
        if not options:
            options = [rng.choice(DIR4)]
        if len(options) > 1 and rng.random() < 0.5:
            options = options[::-1]
        for dx, dy in options:
            cand = (px + dx, py + dy)
            if not cell_blocked_for_enemy(layout, occupied, cand):
                en["pos"] = cand
                return cand
        return None
    # Flip an adjacent mirror - but never the one we just flipped (unless
    # it is the only mirror on the node), and never one the probe holds.
    for dx, dy in DIR4:
        spot = (px + dx, py + dy)
        if spot in mirrors and (spot != last or len(mirrors) == 1):
            if player is not None and _holds(mirrors, player, spot):
                continue
            mirrors[spot] = "/" if mirrors[spot] == "\\" else "\\"
            en["last_target"] = spot
            en["cooldown"] = 8
            en["dir"] = rng.choice(DIR4)
            return None
    if not mirrors:
        return None
    # Seek the nearest mirror we may actually touch: not the last target,
    # not one the probe holds. If every optic is held, the corruptor
    # idles - the runner earned that window.
    held = lambda m: player is not None and _holds(mirrors, player, m)
    candidates = [m for m in mirrors if m != last and not held(m)]
    if not candidates:
        candidates = [m for m in mirrors if not held(m)]
    if not candidates:
        return None
    target = min(
        candidates,
        key=lambda m: (abs(m[0] - px) + abs(m[1] - py), m[0], m[1]),
    )
    en["last_target"] = target
    options = []
    if target[0] != px:
        options.append(((1 if target[0] > px else -1), 0))
    if target[1] != py:
        options.append((0, (1 if target[1] > py else -1)))
    options.sort(
        key=lambda d: -(abs(target[0] - (px + d[0])) + abs(target[1] - (py + d[1])))
    )
    for dx, dy in options:
        cand = (px + dx, py + dy)
        if not cell_blocked_for_enemy(layout, occupied, cand):
            en["pos"] = cand
            return cand
    # Path to the target is fenced off: drift instead of deadlocking.
    dx, dy = rng.choice(DIR4)
    cand = (px + dx, py + dy)
    if not cell_blocked_for_enemy(layout, occupied, cand):
        en["pos"] = cand
        return cand
    return None


def _holds(mirrors, player: tuple[int, int], spot: tuple[int, int]) -> bool:
    """True if the probe stands on or beside `spot` (its grip protects the
    optic from corruption)."""
    return abs(player[0] - spot[0]) + abs(player[1] - spot[1]) <= 1


def _step_wraith(
    layout, en: dict, player, occupied: set[tuple[int, int]], rng
) -> tuple[int, int] | None:
    """Phase ghost: drifts toward the probe within 8 cells, else wanders -
    straight through walls, mirrors and hardware. Blocked only by the
    perimeter and other daemons. Returns new pos or None."""
    px, py = _pos(en)
    if player is not None:
        gx, gy = player
        dist = abs(gx - px) + abs(gy - py)
        if dist <= WRAITH_SENSE_RANGE and dist > 0:
            options = []
            if gx != px:
                options.append(((1 if gx > px else -1), 0))
            if gy != py:
                options.append((0, (1 if gy > py else -1)))
            options.sort(key=lambda d: -(abs(gx - (px + d[0])) + abs(gy - (py + d[1]))))
            for dx, dy in options:
                cand = (px + dx, py + dy)
                if _wraith_free(layout, occupied, cand):
                    en["pos"] = cand
                    en["dir"] = (dx, dy)
                    return cand
            return None
    # Drift: keep heading through the structure, re-aim when fenced in.
    if rng.random() < 0.35:
        en["dir"] = rng.choice(DIR4)
    dx, dy = en["dir"]
    cand = (px + dx, py + dy)
    if not _wraith_free(layout, occupied, cand):
        en["dir"] = rng.choice(DIR4)
        return None
    en["pos"] = cand
    return cand


def _step_lancer(
    layout, en: dict, player, mirrors, occupied: set[tuple[int, int]], rng
) -> tuple[int, int] | None:
    """Lane charger: locks onto a probe sharing its row/column with clear
    sight and dashes TWO cells per tick toward it; otherwise wanders at
    half speed. Returns new pos or None."""
    px, py = _pos(en)
    if player is not None:
        lane = _lane_sight(layout, (px, py), player, mirrors)
        if lane is not None:
            dx, dy = lane
            en["dir"] = (dx, dy)
            cur = (px, py)
            for _ in range(2):  # the dash: two cells per tick
                cand = (cur[0] + dx, cur[1] + dy)
                if cand != player and cell_blocked_for_enemy(layout, occupied, cand):
                    break  # slammed into cover mid-dash
                cur = cand
                en["pos"] = cand
                if cand == player:
                    break  # contact - strike resolves upstream
            return en["pos"] if en["pos"] != (px, py) else None
    # Patrol: keep heading, bounce off blockers, occasionally turn.
    if en.get("clock", 0) % 2 == 1:
        return None  # slow mode: acts every other tick
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


def _volt_field(
    layout, en: dict, occupied: set[tuple[int, int]]
) -> list[tuple[int, int]]:
    """The four adjacent cells a volt charges when it pulses: open floor
    only (walls and hardware ground the charge)."""
    px, py = _pos(en)
    cells = []
    for dx, dy in DIR4:
        cand = (px + dx, py + dy)
        x, y = cand
        if not (0 <= x < layout.width and 0 <= y < layout.height):
            continue
        if layout.rows[y][x] in ENEMY_BLOCKED_TERRAIN or cand in occupied:
            continue
        cells.append(cand)
    return cells


def _step_volt(layout, en: dict, player, occupied: set[tuple[int, int]], game) -> bool:
    """Static ward: never moves. Every other tick it pulses its charge
    field; returns True when the probe was caught in the pulse (the
    caller records the strike). The field glints either way."""
    en["clock"] = en.get("clock", 0) + 1
    if (en["clock"] - 1) % VOLT_PULSE_CADENCE:
        return False
    field = _volt_field(layout, en, occupied)
    for cell in field:  # telegraph the pulse even when it misses
        game.flash[cell] = max(game.flash.get(cell, 0), VOLT_FIELD_TICKS)
    return player in field


def step_daemons(game) -> list[tuple[dict, tuple[int, int]]]:
    """Tick every daemon one step. Returns (daemon, origin) strike pairs.

    Called by Game after every successful player action. Handles daemon-
    daemon collision (later daemons respect earlier positions this tick),
    stun timers, pulse fields and probe contact.
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
            new = _step_corruptor(
                game.layout, en, game.mirrors, game.player, occupied, game.rng
            )
        elif en["kind"] == "wraith":
            # Phasing ghosts are patient: one step every third tick.
            en["clock"] = (en.get("clock", 0) + 1) % 3
            if en["clock"] != 1:
                occupied.add(prev)
                continue
            new = _step_wraith(game.layout, en, game.player, occupied, game.rng)
        elif en["kind"] == "lancer":
            new = _step_lancer(
                game.layout, en, game.player, game.mirrors, occupied, game.rng
            )
            en["clock"] = en.get("clock", 0) + 1
        elif en["kind"] == "volt":
            # Static ward: it never moves. A pulse that catches the probe
            # in its field is recorded directly as a strike.
            if _step_volt(game.layout, en, game.player, occupied, game):
                strikes.append((en, prev))
            occupied.add(prev)
            continue
        else:  # pragma: no cover - kinds are fixed at spawn
            new = None
        if new is None:
            occupied.add(prev)
            continue
        occupied.add(new)
        if new == game.player:
            strikes.append((en, prev))
    return strikes


def knock_back(
    en: dict, origin: tuple[int, int], player: tuple[int, int], game
) -> None:
    """Push a striking daemon off the probe: prefer the cell it came from,
    else any free neighbor. Falls back to stun only. Static wards (volts)
    never move - the stun alone opens the window."""
    if en["kind"] == "volt":
        return
    candidates = [origin] if origin != player else []
    px, py = en["pos"]
    candidates += [
        (px + dx, py + dy) for dx, dy in DIR4 if (px + dx, py + dy) != player
    ]
    occupied = {o["pos"] for o in game.daemons} | {game.player}
    for cand in candidates:
        if not cell_blocked_for_enemy(game.layout, occupied, cand):
            en["pos"] = cand
            return


def threat_near(game) -> bool:
    """True while any live daemon poses near-term danger: hunters within
    sense range, wraiths closing in, lancers with a lane on the probe,
    volts adjacent. Drives the danger-music mode and the red equalizer."""
    px, py = game.player
    for en in game.daemons:
        if en.get("stun", 0) > 0:
            continue
        ex, ey = en["pos"]
        dist = abs(ex - px) + abs(ey - py)
        kind = en["kind"]
        if kind == "hunter" and dist <= HUNTER_SENSE_RANGE:
            return True
        if kind == "wraith" and dist <= 4:
            return True
        if kind in ("lancer", "volt") and dist <= 1:
            return True
        if (
            kind == "lancer"
            and dist <= 6
            and _lane_sight(game.layout, (ex, ey), (px, py), game.mirrors)
        ):
            return True
    return False
