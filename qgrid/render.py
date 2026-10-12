"""ANSI rendering engine for Quantum Grid 2099: BLACKOUT PROTOCOL.

Cyber-blue theme: blue probe on black, green laser fire, red emitters,
magenta ICE. Renders adaptive terminal frames (minimum 80x24):

  - The grid auto-upscales to chunky 2x2 pixel-blocks when the terminal
    is large enough (the 8-bit look), with diagonal 2x2 mirrors.
  - Beam trails shimmer (single/double line glyphs) every other frame.
  - Transient effects: flash bursts (power/shard/teleport/strike) and
    screen-shake on ICE strikes.

Every frame is drawn with a cursor-home redraw (\\033[H) plus
clear-to-end-of-line (\\033[K) per row to avoid flicker; full clears
(\\033[2J) are used only on screen transitions. Animated screens
(title, victory, ...) take a frame counter for blink/sweep effects.
"""

from . import assets
from . import enemies as ice
from .game import BANDWIDTH_MAX
from .levels import EMITTER_CHARS, EXIT, SHARD, SPLITTER, WALL, LevelDef
from .lore import CODEX, ZONES, rank_for

ESC = "\x1b"
ESC_K = f"{ESC}[K"
HOME = f"{ESC}[H"
CLEAR = f"{ESC}[2J{ESC}[H"
HIDE_CURSOR = f"{ESC}[?25l"
SHOW_CURSOR = f"{ESC}[?25h"

MIN_W = 80
MIN_H = 24

# ANSI SGR codes - cyber blue theme -------------------------------------------
PLAYER_BLUE_ON_BLACK = "1;34;40"  # the probe: blue on black
BEAM_GREEN = "1;32"  # laser fire: green
BEAM_GREEN_HI = "1;92"  # laser fire, shimmer phase
EMITTER_RED = "1;31"  # emitters: red
RECEPTOR_YELLOW = "33"  # unpowered target
RECEPTOR_YELLOW_HI = "1;33"  # powered target
MIRROR_CYAN = "1;36"  # optical mirrors
WALL_BLUE = "34"  # mainframe structure
EXIT_ACTIVE = "1;37;5"  # flashing white
EXIT_LOCKED = "90"  # dim
FLOOR_GRAY = "90"  # dark gray on black
CYAN = "1;36"
YELLOW = "1;33"
SHARD_YELLOW = "93"  # datashards
RED = "1;31"
WHITE = "37"
GRAY = "90"
BLUE = "34"
ICE_MAGENTA = "1;35"  # ICE daemons
PAD_MAGENTA = "95"  # teleport pads
FLASH_WHITE = "1;97"  # VFX flash bursts

ZONE_SIZE = 8
ZONE_COUNT = 6

# Speaker colors for cutscene dialogue.
SPEAKER_COLORS = {
    "": GRAY,  # narration (SYSTEM)
    "NYX": WHITE,
    "MIRAGE": CYAN,
    "VEX": RED,
    "ORACLE-9": ICE_MAGENTA,
    "KAI": SHARD_YELLOW,
}

# Shake offsets cycled per frame while a shake is active (dx only).
SHAKE_OFFSETS = (0, -2, 2, -1, 1, -2, 0, 2)


def _c(code: str, ch: str) -> str:
    return f"{ESC}[{code}m{ch}{ESC}[0m"


def _truncate(text: str, width: int) -> str:
    return text if len(text) <= width else text[: width - 3] + "..."


def _strip_ansi(text: str) -> str:
    out = []
    i = 0
    while i < len(text):
        if text[i] == ESC:
            i += 2
            while i < len(text) and text[i] not in "ABCDEFGHJKSTfmnsulh":
                i += 1
            i += 1
        else:
            out.append(text[i])
            i += 1
    return "".join(out)


def _center(text: str, width: int) -> str:
    plain_len = len(_strip_ansi(text))
    pad = max(0, (width - plain_len) // 2)
    return " " * pad + text


def _wrap_center(text: str, width: int, color: str | None = None) -> list[str]:
    """Word-wrap a lore paragraph to the terminal width, centered per line."""
    import textwrap

    lines = textwrap.wrap(text, width=max(20, width - 8))
    out = []
    for line in lines:
        rendered = _c(color, line) if color else line
        out.append(_center(rendered, width))
    return out


# ------------------------------------------------------------------- gameplay

# Beam shimmer: alternate glyph sets every other frame.
BEAM_GLYPHS_H = ("─", "═")
BEAM_GLYPHS_V = ("│", "║")
BEAM_GLYPHS_X = ("┼", "╪")


def _beam_color(gi: int) -> str:
    return BEAM_GREEN if gi % 2 == 0 else BEAM_GREEN_HI


def _cell_str(game, x: int, y: int, gi: int = 0, flash_on: bool = True) -> str:
    """Single glyph for one grid cell (1x scale). gi = shimmer variant."""
    layout = game.layout
    pos = (x, y)
    if pos == game.player:
        return _c(PLAYER_BLUE_ON_BLACK, assets.PLAYER_GLYPH)
    for en in game.daemons:
        if en["pos"] == pos:
            return _c(ICE_MAGENTA, assets.ENEMY_GLYPHS[en["kind"]])
    if flash_on and game.flash.get(pos, 0) > 0:
        return _c(FLASH_WHITE, "\u2726")  # VFX flash burst
    if pos in game.mirrors:
        return _c(MIRROR_CYAN, game.mirrors[pos])
    raw = layout.rows[y][x]
    if raw == WALL:
        return _c(WALL_BLUE, assets.WALL_GLYPH)
    if raw in EMITTER_CHARS:
        return _c(EMITTER_RED, assets.EMITTER_GLYPHS.get(raw, raw))
    if raw == SPLITTER:
        return _c(MIRROR_CYAN, assets.SPLITTER_GLYPH)
    if raw in ("T", "U"):
        return _c(PAD_MAGENTA, assets.PAD_GLYPHS.get(raw, raw))
    if raw == SHARD and pos not in game.shards_taken:
        return _c(SHARD_YELLOW, assets.SHARD_GLYPH)
    if raw == "*":
        if pos in game.trace.powered:
            return _c(RECEPTOR_YELLOW_HI, assets.RECEPTOR_GLYPH)
        return _c(RECEPTOR_YELLOW, assets.RECEPTOR_GLYPH)
    if raw == EXIT:
        if game.exit_active():
            return _c(EXIT_ACTIVE, assets.EXIT_GLYPH)
        return _c(EXIT_LOCKED, assets.EXIT_GLYPH)
    h = pos in game.trace.h
    v = pos in game.trace.v
    color = _beam_color(gi)
    if h and v:
        return _c(color, BEAM_GLYPHS_X[gi])
    if h:
        return _c(color, BEAM_GLYPHS_H[gi])
    if v:
        return _c(color, BEAM_GLYPHS_V[gi])
    return _c(FLOOR_GRAY, assets.FLOOR_GLYPH)


def _cell_block(game, x: int, y: int, gi: int, flash_on: bool, sx: int, sy: int) -> list[str]:
    """One grid cell as `sy` rows of `sx` chars (per-axis pixel scaling).

    Square blocks (sx == sy) get true diagonal mirrors; everything else
    duplicates the glyph.
    """
    layout = game.layout
    pos = (x, y)
    n = sx
    if sx == sy:
        if pos == game.player:
            return [_c(PLAYER_BLUE_ON_BLACK, "@" * n)] * n
        for en in game.daemons:
            if en["pos"] == pos:
                g = assets.ENEMY_GLYPHS[en["kind"]]
                return [_c(ICE_MAGENTA, g * n)] * n
        if flash_on and game.flash.get(pos, 0) > 0:
            return [_c(FLASH_WHITE, "\u2726" * n)] * n
        if pos in game.mirrors:
            g = game.mirrors[pos]
            color = MIRROR_CYAN
            if g == "/":  # rising diagonal: bottom-left -> top-right
                return [
                    _c(color, " " * (n - 1 - i) + "/" + " " * i)
                    for i in range(n)
                ]
            # falling diagonal: top-left -> bottom-right
            return [
                _c(color, " " * i + "\\" + " " * (n - 1 - i))
                for i in range(n)
            ]
        raw = layout.rows[y][x]
        if raw == WALL:
            return [_c(WALL_BLUE, assets.WALL_GLYPH * n)] * n
        if raw in EMITTER_CHARS:
            g = assets.EMITTER_GLYPHS.get(raw, raw)
            return [_c(EMITTER_RED, g * n)] * n
        if raw == SPLITTER:
            return [_c(MIRROR_CYAN, assets.SPLITTER_GLYPH * n)] * n
        if raw in ("T", "U"):
            g = assets.PAD_GLYPHS.get(raw, raw)
            return [_c(PAD_MAGENTA, g * n)] * n
        if raw == SHARD and pos not in game.shards_taken:
            return [_c(SHARD_YELLOW, assets.SHARD_GLYPH * n)] * n
        if raw == "*":
            if pos in game.trace.powered:
                return [_c(RECEPTOR_YELLOW_HI, assets.RECEPTOR_GLYPH * n)] * n
            return [_c(RECEPTOR_YELLOW, assets.RECEPTOR_GLYPH * n)] * n
        if raw == EXIT:
            if game.exit_active():
                return [_c(EXIT_ACTIVE, assets.EXIT_GLYPH * n)] * n
            return [_c(EXIT_LOCKED, assets.EXIT_GLYPH * n)] * n
        h = pos in game.trace.h
        v = pos in game.trace.v
        color = _beam_color(gi)
        if h and v:
            return [
                _c(color, BEAM_GLYPHS_H[gi] * n),
                *[_c(color, BEAM_GLYPHS_V[gi] * n)] * (n - 1),
            ]
        if h:
            return [_c(color, BEAM_GLYPHS_H[gi] * n)] * n
        if v:
            return [_c(color, BEAM_GLYPHS_V[gi] * n)] * n
        return [_c(FLOOR_GRAY, assets.FLOOR_GLYPH * n)] * n
    # Non-square block: duplicate the 1x glyph horizontally/vertically.
    glyph = _cell_str(game, x, y, gi, flash_on)
    plain_glyph = _strip_ansi(glyph)
    code = None
    if glyph.startswith(ESC + "["):
        code = glyph[2 : glyph.index("m")]
    row = _c(code, plain_glyph * sx) if code else plain_glyph * sx
    return [row] * sy


def _bandwidth_bar(bandwidth: int) -> str:
    filled = max(0, min(20, bandwidth // 10))
    if bandwidth >= 100:
        color = WALL_BLUE
    elif bandwidth >= 50:
        color = YELLOW
    else:
        color = RED
    return _c(color, "\u2588" * filled) + _c(GRAY, "\u2591" * (20 - filled))


def _header_lines(game, total_score: int = 0) -> list[str]:
    zone = game.defn.zone
    title = _c(CYAN, f"  QUANTUM GRID 2099 // NODE {game.level_index + 1:02d}") + _c(
        GRAY, f" - {game.defn.name}"
    ) + _c(GRAY, f"  [SECTOR {zone:02d}]")
    powered = len(game.trace.powered)
    total = len(game.layout.receptors)
    if game.all_powered():
        state = _c(BEAM_GREEN, "[UNLOCKED]")
    else:
        state = _c(RED, "[LOCKED]")
    shards = len(game.shards_taken)
    shards_total = len(game.layout.shards)
    line = (
        f"  BW [{_bandwidth_bar(game.bandwidth)}] {_c(WHITE, str(game.bandwidth))}%"
        f" {_c(GRAY, '|')} REC {_c(WHITE, f'{powered}/{total}')} {state}"
    )
    if shards_total:
        line += (
            f" {_c(GRAY, '|')} {_c(SHARD_YELLOW, assets.SHARD_GLYPH)}"
            f" {_c(WHITE, f'{shards}/{shards_total}')}"
        )
    if total_score:
        line += f" {_c(GRAY, '|')} {_c(YELLOW, f'{total_score} PTS')}"
    return [title, line]


def _rule(width: int, color: str = WALL_BLUE) -> str:
    return _c(color, "=" * width)


_CONTROLS_LINE = (
    f"  {_c(WHITE, 'WASD')} {_c(GRAY, 'Move')}"
    f" {_c(GRAY, '|')} {_c(WHITE, 'R')} {_c(GRAY, 'Rotate')}"
    f" {_c(GRAY, '|')} {_c(WHITE, 'K')} {_c(GRAY, 'Restart')}"
    f" {_c(GRAY, '|')} {_c(WHITE, 'M')} {_c(GRAY, 'Sound')}"
    f" {_c(GRAY, '|')} {_c(WHITE, 'Q')} {_c(GRAY, 'Quit')}"
)

_EQ_BARS = "\u2581\u2582\u2583\u2584\u2585\u2586\u2587"


def _eq_strip(frame: int, music_on: bool, danger: bool = False) -> str:
    """Tiny animated equalizer strip - the visual half of the soundtrack."""
    icon = "\u266a" if music_on else "\u00d8"
    color = RED if danger else CYAN
    bars = ""
    for i in range(6):
        h = (frame * 7 + i * 13 + (frame // 2) * 5) % 7
        bars += _EQ_BARS[h]
    return _c(color, f"{icon} {bars}")


def _emit(lines: list[str], width: int, height: int, home: str) -> str:
    """Serialize frame lines to a terminal-sized escape sequence string."""
    out = [home]
    for i in range(height):
        content = lines[i] if i < len(lines) else ""
        out.append(content + ESC_K)
        out.append("\r\n" if i < height - 1 else "")
    return "".join(out)


def _grid_scale(game, width: int, height: int) -> tuple[int, int]:
    """Per-axis pixel scaling: (sx, sy), each 1..3 when the terminal fits.

    Cells go wider and taller independently - on an 80x24 terminal early
    nodes render 2x wider; huge grids stay 1x; big terminals get 3x3.
    """
    sx = 1
    for s in (3, 2):
        if (game.layout.width + 2) * s + 2 <= width:
            sx = s
            break
    sy = 1
    for s in (3, 2):
        if game.layout.height * s + 4 <= height:
            sy = s
            break
    return sx, sy


def render_frame(
    game,
    width: int = MIN_W,
    height: int = MIN_H,
    total_score: int = 0,
    frame: int = 0,
    music_on: bool = True,
    vfx: dict | None = None,
) -> str:
    """Build the gameplay frame filling the terminal, grid as large as fits.

    vfx toggles (from settings): shake / flashes / shimmer, defaulting on.
    """
    width = max(width, MIN_W)
    height = max(height, MIN_H)
    vfx = vfx or {}
    shake_on = vfx.get("shake", True)
    flash_on = vfx.get("flashes", True)
    shimmer_on = vfx.get("shimmer", True)
    gi = (frame % 2) if shimmer_on else 0
    sx, sy = _grid_scale(game, width, height)
    grid_w = (game.layout.width + 2) * sx
    indent = max(1, (width - grid_w) // 2)
    if game.shake > 0 and shake_on:
        indent = max(0, indent + SHAKE_OFFSETS[frame % len(SHAKE_OFFSETS)])
    rule_color = (RED if game.shake > 1 else WALL_BLUE) if (game.shake > 1 and shake_on) else WALL_BLUE
    danger = ice.threat_near(game)

    # chrome: rule + 2 HUD lines + grid + status + controls (footer pinned)
    chrome = 5
    rows = game.layout.height * sy
    flex = max(0, height - chrome - rows)
    pad_above = flex // 2
    pad_below = flex - pad_above

    lines: list[str] = [_rule(width, rule_color)]
    lines.extend(_header_lines(game, total_score))
    lines.extend([""] * pad_above)
    for y in range(game.layout.height):
        if sx == 1 and sy == 1:
            lines.append(
                " " * indent
                + "".join(
                    _cell_str(game, x, y, gi, flash_on)
                    for x in range(game.layout.width)
                )
            )
            continue
        blocks = [
            _cell_block(game, x, y, gi, flash_on, sx, sy)
            for x in range(game.layout.width)
        ]
        for r in range(sy):
            lines.append(" " * indent + "".join(b[r] for b in blocks))
    lines.extend([""] * pad_below)
    lines.append(
        f"  {_c(GRAY, 'STATUS:')} {_c(YELLOW, _truncate(game.msg, width - 14))}"
    )
    eq = _eq_strip(frame, music_on, danger)
    ctl = _CONTROLS_LINE
    pad = width - len(_strip_ansi(ctl)) - len(_strip_ansi(eq)) - 1
    lines.append(ctl + " " * max(1, pad) + eq)
    return _emit(lines, width, height, HOME)


# --------------------------------------------------------------------- screens


def _screen(body: list[str], width: int, height: int, clear: bool = True) -> str:
    lines = [_rule(width), ""]
    lines.extend(body)
    lines.append("")
    lines.append(_rule(width))
    return _emit(lines, width, height, CLEAR if clear else HOME)


def _indent(lines: list[str], spaces: int = 4) -> list[str]:
    pad = " " * spaces
    return [pad + line for line in lines]


def _colored_banner(text: str, color: str) -> list[str]:
    return [_c(color, row) for row in assets.banner(text)]


def _blink(text: str, frame: int, color: str, period: int = 4) -> str:
    """Visible on most frames, dimmed on the rest - retro attract blink."""
    if (frame // (period // 2)) % 2 == 0:
        return _c(color, text)
    return _c(GRAY, text)


def _laser_lane(width: int, frame: int) -> str:
    """Animated 8-bit lane: a beam comet sweeping back and forth."""
    lane_w = min(56, max(20, width - 24))
    period = (lane_w - 3) * 2
    t = frame % period
    pos = t if t < lane_w - 3 else period - t
    left = "\u00b7" * pos
    right = "\u00b7" * (lane_w - 3 - pos)
    lane = (
        _c(GRAY, left)
        + _c(EMITTER_RED, "\u25b6")
        + _c(_beam_color(frame), "\u2500" * 2)
        + _c(GRAY, right)
        + _c(RECEPTOR_YELLOW, "\u25c9")
    )
    return _center(lane, width)


def render_title(
    width: int = MIN_W, height: int = MIN_H, frame: int = 0, clear: bool = True
) -> str:
    body = [
        *_indent(_colored_banner("QUANTUM GRID", CYAN)),
        *_indent(_colored_banner("2099", EMITTER_RED)),
        "",
        *_wrap_center("B L A C K O U T   P R O T O C O L", width, color=GRAY),
        _laser_lane(width, frame),
        *_wrap_center(
            "48 nodes. 6 sectors. Live ICE. One erased brother.", width, color=WHITE
        ),
        "",
        _center(_c(GRAY, assets.LEGEND_ROW), width),
        _center(_c(GRAY, assets.LEGEND_LABELS), width),
        "",
        _center(
            "Rotate mirrors, split beams, fold space, dodge the daemons.", width
        ),
        _center(_c(GRAY, "\u266a no sound? run: python3 -m qgrid.audio_client"), width),
        _center(_blink(">>> PRESS ANY KEY TO JACK IN <<<", frame, BEAM_GREEN), width),
    ]
    return _screen(body, width, height, clear)


def render_save_menu(
    save: dict, username: str, width: int = MIN_W, height: int = MIN_H
) -> str:
    nodes = save.get("unlocked", 0)
    has_progress = nodes > 0 or save.get("total_score", 0) > 0
    body = [
        _center(_c(CYAN, f"NETRUNNER ID: {username}"), width),
        "",
    ]
    if has_progress:
        body.extend(
            [
                _center(
                    f"PROGRESS: {_c(WHITE, str(nodes) + '/48')} nodes"
                    f" {_c(GRAY, '|')} SCORE {_c(YELLOW, str(save.get('total_score', 0)))}"
                    f" {_c(GRAY, '|')} CODEX {_c(CYAN, str(len(save.get('codex', []))) + '/' + str(len(CODEX)))}",
                    width,
                ),
                "",
                _center(_c(BEAM_GREEN, "[ENTER] CONTINUE RUN"), width),
                _center(_c(WHITE, "[N] NEW RUN (resets progress)"), width),
                "",
                _center(_c(GRAY, "Shards banked survive a new run? No. The Grid"), width),
                _center(_c(GRAY, "keeps nothing it is not forced to keep."), width),
            ]
        )
    else:
        body.extend(
            [
                *_wrap_center(
                    "First descent detected. NYX, your channel is clean and your "
                    "debt is due. MIRAGE is waiting on the wire.",
                    width,
                    color=GRAY,
                ),
                "",
                _center(_c(BEAM_GREEN, "[ENTER] BEGIN RUN"), width),
            ]
        )
    return _screen(body, width, height)


def _zone_status(zone_num: int, save: dict, unlock_all: bool) -> str:
    start = (zone_num - 1) * ZONE_SIZE
    cleared_end = min(save.get("unlocked", 0), zone_num * ZONE_SIZE - 1)
    cleared = max(0, cleared_end - start + 1) if save.get("unlocked", 0) >= start else 0
    if unlock_all or save.get("unlocked", 0) >= start:
        if cleared >= ZONE_SIZE:
            return _c(BEAM_GREEN, f"CLEARED {cleared}/{ZONE_SIZE}")
        return _c(YELLOW, f"IN PROGRESS {cleared}/{ZONE_SIZE}")
    return _c(RED, "[LOCKED]")


def render_zone_select(
    save: dict, unlock_all: bool = False, width: int = MIN_W, height: int = MIN_H
) -> str:
    body = [
        _center(_c(CYAN, "SECTOR ACCESS // QUANTUM GRID 2099"), width),
        "",
    ]
    for zone in ZONES:
        num = zone.number
        label = _c(WHITE, f"[{num}] SECTOR {num:02d}") + _c(CYAN, f" - {zone.name}")
        status = _zone_status(num, save, unlock_all)
        pad = 34 - len(_strip_ansi(label))
        line = "  " + label + " " * max(1, pad) + status
        body.append(line)
        body.append(_center(_c(GRAY, zone.tagline), width))
    body.extend(
        [
            "",
            "  1-6: sector | ENTER: next node | C: codex | O: options | M: sound | Q: quit",
        ]
    )
    return _screen(body, width, height)


def _node_line(i: int, save: dict, unlock_all: bool) -> str:
    from .levels import LEVELS

    defn = LEVELS[i]
    in_zone = i // ZONE_SIZE + 1
    zone_unlocked = unlock_all or save.get("unlocked", 0) >= (in_zone - 1) * ZONE_SIZE
    unlocked = zone_unlocked and (unlock_all or i <= save.get("unlocked", 0))
    cleared = i < save.get("unlocked", 0)
    label = f"[{i % ZONE_SIZE + 1}] NODE {i + 1:02d} - {defn.name}"
    if not unlocked:
        return _c(GRAY, label) + _c(RED, " [LOCKED]")
    line = _c(WHITE, f"[{i % ZONE_SIZE + 1}]") + _c(CYAN, f" NODE {i + 1:02d} - {defn.name}")
    if cleared:
        line += _c(BEAM_GREEN, " \u2713")
    shard_note = ""
    layout_shards = _shard_count(i)
    if layout_shards:
        got = len(save.get("shards", {}).get(str(i), []))
        mark = assets.SHARD_GLYPH
        shard_note = f" {mark}{got}/{layout_shards}"
        line += _c(SHARD_YELLOW if got == layout_shards else GRAY, shard_note)
    return line


def _shard_count(i: int) -> int:
    from .levels import LEVELS, parse_level

    try:
        return len(parse_level(LEVELS[i].rows, LEVELS[i].name).shards)
    except ValueError:
        return 0


def render_node_select(
    zone_num: int,
    save: dict,
    unlock_all: bool = False,
    width: int = MIN_W,
    height: int = MIN_H,
) -> str:
    zone = ZONES[zone_num - 1]
    body = [
        _center(
            _c(CYAN, f"SECTOR {zone_num:02d}") + _c(GRAY, " // ") + _c(WHITE, zone.name),
            width,
        ),
        _center(_c(GRAY, zone.tagline), width),
        "",
    ]
    start = (zone_num - 1) * ZONE_SIZE
    for r in range(ZONE_SIZE // 2):
        left = _node_line(start + r, save, unlock_all)
        right = _node_line(start + r + ZONE_SIZE // 2, save, unlock_all)
        pad = 38 - len(_strip_ansi(left))
        body.append("  " + left + " " * max(1, pad) + right)
    body.extend(
        [
            "",
            "  1-8: node | ENTER: next uncleared | C: codex | O: options | Q: disconnect",
        ]
    )
    return _screen(body, width, height)


def render_codex(
    save: dict,
    selected: int = 0,
    detail: bool = False,
    width: int = MIN_W,
    height: int = MIN_H,
) -> str:
    unlocked = set(save.get("codex", []))
    body = [
        _center(
            _c(CYAN, "CODEX")
            + _c(GRAY, " // ")
            + _c(WHITE, f"{len(unlocked)}/{len(CODEX)} ENTRIES DECRYPTED"),
            width,
        ),
        "",
    ]
    half = (len(CODEX) + 1) // 2
    for r in range(half):
        cols = []
        for idx in (r, r + half):
            if idx >= len(CODEX):
                cols.append("")
                continue
            key, title, _ = CODEX[idx]
            marker = _c(BEAM_GREEN, ">") if idx == selected else _c(GRAY, " ")
            if key in unlocked:
                cols.append(f"{marker} {_c(WHITE, title)}")
            else:
                cols.append(f"{marker} {_c(GRAY, '?' * len(title))}")
        pad = 38 - len(_strip_ansi(cols[0]))
        body.append("  " + cols[0] + " " * max(1, pad) + cols[1])
    if detail and CODEX[selected][0] in unlocked:
        key, title, text = CODEX[selected]
        body.append("")
        body.append(_center(_c(YELLOW, f"// {title}"), width))
        body.extend(_wrap_center(text, width, color=GRAY))
    elif detail:
        body.append("")
        body.append(_center(_c(RED, "SIGNAL ENCRYPTED - entry not yet decrypted"), width))
    body.extend(
        [
            "",
            "  W/S: select | ENTER: read | C/Q: back",
        ]
    )
    return _screen(body, width, height)


def _threat_summary(defn: LevelDef) -> str:
    from .levels import parse_level

    layout = parse_level(defn.rows, defn.name)
    counts: dict[str, int] = {}
    for _, kind in layout.enemies:
        counts[kind] = counts.get(kind, 0) + 1
    names = {
        "sentinel": "SENTINEL",
        "hunter": "HUNTER",
        "corruptor": "CORRUPTOR",
        "wraith": "WRAITH",
        "lancer": "LANCER",
        "volt": "VOLT",
    }
    parts = [f"{count}x {names[kind]}" for kind, count in sorted(counts.items())]
    return ", ".join(parts) if parts else "none detected"


def render_level_intro(
    defn: LevelDef, node_index: int, bandwidth: int, width: int = MIN_W, height: int = MIN_H
) -> str:
    from .levels import parse_level

    layout = parse_level(defn.rows, defn.name)
    zone = ZONES[defn.zone - 1]
    body = [
        "",
        _center(_c(EMITTER_RED, "NEW NODE DETECTED"), width),
        "",
        _center(_c(CYAN, f"NODE {node_index + 1:02d} - {defn.name}"), width),
        _center(_c(GRAY, f"sector {defn.zone:02d} - {zone.name}"), width),
        _center(
            _c(
                GRAY,
                f"grid {layout.width}x{layout.height}"
                f" | {len(layout.mirrors)} mirrors"
                + (f" | {len(layout.splitters)} prisms" if layout.splitters else "")
                + (f" | {len(layout.pads) // 2} pad pair" if layout.pads else "")
                + f" | {len(layout.receptors)} receptors",
            ),
            width,
        ),
        "",
        *_wrap_center(defn.lore, width, color=GRAY),
        "",
        _center(_c(WHITE, f"OBJECTIVE: {_truncate(defn.intro, width - 16)}"), width),
        "",
        _center(
            _c(ICE_MAGENTA, f"ICE: {_threat_summary(defn)}")
            + _c(GRAY, " | ")
            + _c(SHARD_YELLOW, f"SHARDS: {len(layout.shards)}"),
            width,
        ),
        "",
        _center(
            f"BANDWIDTH: {_c(BEAM_GREEN, str(bandwidth))}%"
            f"  {_c(GRAY, '|')}  1% per action, 25% per ICE strike",
            width,
        ),
        "",
        _center(_c(BEAM_GREEN, ">>> PRESS ANY KEY TO ENGAGE OPTICAL PROBE <<<"), width),
    ]
    return _screen(body, width, height)


def render_level_complete(
    game, next_index: int, session_score: int, width: int = MIN_W, height: int = MIN_H, frame: int = 0
) -> str:
    from .levels import LEVELS

    par = game.defn.par or game.actions
    body = [
        "",
        _center(_blink("*** ACCESS GRANTED ***", frame, BEAM_GREEN), width),
        "",
        _center(
            _c(CYAN, f"NODE {game.level_index + 1:02d} - {game.defn.name}")
            + _c(BEAM_GREEN, " // EXTRACTION COMPLETE"),
            width,
        ),
        "",
        _center(
            f"ACTIONS {game.actions}"
            f" {_c(GRAY, '(par ' + str(par) + ')')}"
            f" {_c(GRAY, '|')} SHARDS {_c(SHARD_YELLOW, str(len(game.shards_taken)))}"
            f" {_c(GRAY, '|')} STRIKES {_c(RED, str(game.strikes))}",
            width,
        ),
        _center(
            _c(YELLOW, f"+{game.score()} SCORE")
            + _c(GRAY, " | ")
            + _c(WHITE, f"RUN TOTAL {session_score}"),
            width,
        ),
        "",
        _center(
            _c(BEAM_GREEN, f"BANDWIDTH REFRESHED TO {BANDWIDTH_MAX}%"), width,
        ),
        "",
        _center(
            f"Next: NODE {next_index + 1:02d} - {LEVELS[next_index].name}", width
        ),
        "",
        _center(_c(BEAM_GREEN, ">>> PRESS ANY KEY TO CONTINUE <<<"), width),
    ]
    return _screen(body, width, height, clear=False)


def render_sector_clear(
    zone, session_score: int, width: int = MIN_W, height: int = MIN_H, frame: int = 0
) -> str:
    """Intermission between sectors: the MIRAGE beat + run stats."""
    body = [
        "",
        _center(_blink("*** SECTOR CLEARED ***", frame, BEAM_GREEN), width),
        "",
        *_indent(_colored_banner("SECTOR", CYAN)),
        "",
        _center(_c(WHITE, f"SECTOR {zone.number:02d} - {zone.name}"), width),
        _center(_c(GRAY, zone.tagline), width),
        "",
        *_wrap_center(zone.clear_text, width, color=SHARD_YELLOW),
        "",
        _center(f"RUN TOTAL {_c(YELLOW, str(session_score))} PTS", width),
        _center(
            _c(BEAM_GREEN, f"BANDWIDTH REFRESHED TO {BANDWIDTH_MAX}%"), width,
        ),
        "",
        _center(_blink(">>> PRESS ANY KEY TO DESCEND <<<", frame, BEAM_GREEN), width),
    ]
    return _screen(body, width, height, clear=False)


def render_game_over(game, width: int = MIN_W, height: int = MIN_H, frame: int = 0) -> str:
    from .levels import GAMEOVER_LORE

    body = [
        "",
        _center(_blink("*** CONNECTION LOST ***", frame, EMITTER_RED), width),
        "",
        _center(_c(RED, "BANDWIDTH DEPLETED - SESSION TERMINATED"), width),
        "",
        *_wrap_center(GAMEOVER_LORE, width, color=GRAY),
        "",
        _center(
            f"You fell on NODE {game.level_index + 1:02d} - {game.defn.name}.", width
        ),
        _center(
            _c(GRAY, "Your progress is saved. The Grid keeps count even when you can't."),
            width,
        ),
        "",
        _center(_c(BEAM_GREEN, ">>> PRESS ANY KEY TO RE-JACK <<<"), width),
    ]
    return _screen(body, width, height, clear=False)


def render_victory(
    save: dict,
    total_shards_in_game: int,
    width: int = MIN_W,
    height: int = MIN_H,
    frame: int = 0,
) -> str:
    """Final campaign screen: rank + ending (true if enough shards banked)."""
    from .lore import (
        SHARDS_FOR_TRUE_ENDING,
        STANDARD_ENDING_LORE,
        TRUE_ENDING_LORE,
    )

    banked = sum(len(v) for v in save.get("shards", {}).values())
    score = save.get("total_score", 0)
    rank, color = rank_for(score)
    true_end = (
        total_shards_in_game > 0
        and banked >= SHARDS_FOR_TRUE_ENDING * total_shards_in_game
    )
    ending = TRUE_ENDING_LORE if true_end else STANDARD_ENDING_LORE
    body = [
        "",
        _center(_blink("*** MAINFRAME COMPROMISED ***", frame, BEAM_GREEN), width),
        "",
        *_indent(_colored_banner("GRID", BEAM_GREEN if frame % 2 == 0 else BEAM_GREEN_HI)),
        "",
        _center(
            _c(WHITE, "FINAL SCORE ")
            + _c(YELLOW, str(score))
            + _c(GRAY, " // ")
            + _c(color, f"RANK: {rank}"),
            width,
        ),
        _center(
            _c(SHARD_YELLOW, f"DATASHARDS RECOVERED: {banked}/{total_shards_in_game}"),
            width,
        ),
        "",
        *_wrap_center(ending, width, color=GRAY if not true_end else SHARD_YELLOW),
        "",
        _center(_laser_lane(width, frame), width),
        "",
        _center(_c(BEAM_GREEN, ">>> PRESS ANY KEY TO DISCONNECT <<<"), width),
    ]
    return _screen(body, width, height, clear=False)


def render_goodbye(width: int = MIN_W, height: int = MIN_H) -> str:
    body = [
        "",
        _center(_c(CYAN, "CONNECTION TERMINATED"), width),
        "",
        _center(
            "Quantum Grid 2099 // uplink closed. See you on the next floor.", width
        ),
    ]
    return _screen(body, width, height)


# ---------------------------------------------------------------- cutscenes


def _cutscene_page(cutscene: dict, page: int) -> tuple[str, list[str], int]:
    """Return (speaker, wrapped_lines, total_chars) for a cutscene page."""
    import textwrap

    speaker, text = cutscene["pages"][page]
    lines = textwrap.wrap(text, width=max(20, width_limit(cutscene)))
    total = sum(len(line) for line in lines)
    return speaker, lines, total


def width_limit(cutscene: dict) -> int:
    return 68  # text wrap width for cutscene pages


def _reveal(lines: list[str], shown: int) -> list[str]:
    """Take the first `shown` characters across wrapped lines."""
    out = []
    budget = shown
    for line in lines:
        if budget <= 0:
            break
        out.append(line if budget >= len(line) else line[:budget])
        budget -= len(line)
    return out


def render_cutscene(
    cutscene: dict,
    page: int,
    shown: int,
    width: int = MIN_W,
    height: int = MIN_H,
    frame: int = 0,
) -> str:
    """Typewriter-animated cutscene screen with a speaker tag per page."""
    speaker, lines, total = _cutscene_page(cutscene, page)
    color = SPEAKER_COLORS.get(speaker, WHITE)
    body: list[str] = [
        _center(_c(CYAN, _truncate(cutscene["title"], width - 4)), width),
        "",
    ]
    if speaker:
        body.append(_center(_c(color, f"\u00bb {speaker}"), width))
        body.append("")
    for line in _reveal(lines, shown):
        body.append(_center(_c(color, line), width))
    body.append("")
    if shown >= total:
        more = page < len(cutscene["pages"]) - 1
        prompt = "ENTER: MORE   X: SKIP" if more else "ENTER: CONTINUE   X: SKIP"
        body.append(_center(_blink("\u25bc " + prompt, frame, BEAM_GREEN), width))
    else:
        body.append(_center(_c(GRAY, "..."), width))
    return _screen(body, width, height, clear=False)


def cutscene_page_len(cutscene: dict, page: int) -> int:
    return _cutscene_page(cutscene, page)[2]


# ------------------------------------------------------------------ settings


def render_settings(
    settings: dict,
    selected: int,
    width: int = MIN_W,
    height: int = MIN_H,
) -> str:
    from .lore import SETTING_LABELS, SETTINGS_SCHEMA

    body = [
        _center(_c(CYAN, "SYSTEM SETTINGS"), width),
        _center(_c(GRAY, "changes save to your runner profile instantly"), width),
        "",
    ]
    keys = list(SETTINGS_SCHEMA)
    for i, key in enumerate(keys):
        marker = _c(BEAM_GREEN, ">") if i == selected else _c(GRAY, " ")
        label = SETTING_LABELS[key].ljust(15)
        value = settings[key].upper()
        line = f"  {marker} {_c(WHITE, label)} {_c(BEAM_GREEN, value)}"
        body.append(_center(line, width))
    body.extend(
        [
            "",
            "  W/S: select | ENTER: toggle | Q: back",
        ]
    )
    return _screen(body, width, height)
