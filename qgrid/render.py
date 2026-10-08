"""ANSI rendering engine for Quantum Grid 2099.

Cyber-blue theme: blue probe on black, green laser fire, red emitters.
Renders adaptive terminal frames (minimum 80x24) using ANSI escape
sequences. Every frame is drawn with a cursor-home redraw (\\033[H) plus
clear-to-end-of-line (\\033[K) per row to avoid flicker; full clears
(\\033[2J) are used only on screen transitions.
"""

from . import assets
from .levels import EMITTER_CHARS, EXIT, WALL, LevelDef

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
EMITTER_RED = "1;31"  # enemies: red
RECEPTOR_YELLOW = "33"  # unpowered target
RECEPTOR_YELLOW_HI = "1;33"  # powered target
MIRROR_CYAN = "1;36"  # optical mirrors
WALL_BLUE = "34"  # mainframe structure
EXIT_ACTIVE = "1;37;5"  # flashing white
EXIT_LOCKED = "90"  # dim
FLOOR_GRAY = "90"  # dark gray on black
CYAN = "1;36"
YELLOW = "1;33"
RED = "1;31"
WHITE = "37"
GRAY = "90"
BLUE = "34"


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


def _cell_str(game, x: int, y: int) -> str:
    layout = game.layout
    pos = (x, y)
    raw = layout.rows[y][x]
    if pos == game.player:
        return _c(PLAYER_BLUE_ON_BLACK, assets.PLAYER_GLYPH)
    if pos in game.mirrors:
        return _c(MIRROR_CYAN, game.mirrors[pos])
    if raw == WALL:
        return _c(WALL_BLUE, assets.WALL_GLYPH)
    if raw in EMITTER_CHARS:
        return _c(EMITTER_RED, assets.EMITTER_GLYPHS.get(raw, raw))
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
    if h and v:
        return _c(BEAM_GREEN, assets.BEAM_X)
    if h:
        return _c(BEAM_GREEN, assets.BEAM_H)
    if v:
        return _c(BEAM_GREEN, assets.BEAM_V)
    return _c(FLOOR_GRAY, assets.FLOOR_GLYPH)


def _bandwidth_bar(bandwidth: int) -> str:
    filled = max(0, min(20, bandwidth // 5))
    if bandwidth >= 50:
        color = WALL_BLUE
    elif bandwidth >= 25:
        color = YELLOW
    else:
        color = RED
    return _c(color, "\u2588" * filled) + _c(GRAY, "\u2591" * (20 - filled))


def _header_lines(game) -> list[str]:
    node = f"{game.level_index + 1:02d}"
    title = _c(CYAN, f"  QUANTUM GRID 2099 // MAINFRAME NODE {node}") + _c(
        GRAY, f" - {game.defn.name}"
    )
    powered = len(game.trace.powered)
    total = len(game.layout.receptors)
    if game.all_powered():
        state = _c(BEAM_GREEN, "[UNLOCKED]")
    else:
        state = _c(RED, "[LOCKED]")
    line = (
        f"  BANDWIDTH: [{_bandwidth_bar(game.bandwidth)}] {_c(WHITE, str(game.bandwidth))}%"
        f" {_c(GRAY, '|')} RECEPTORS: {_c(WHITE, f'{powered}/{total}')} {state}"
    )
    return [title, line]


def _rule(width: int) -> str:
    return _c(WALL_BLUE, "=" * width)


_CONTROLS_LINE = (
    f"  {_c(GRAY, 'CONTROLS:')} {_c(WHITE, 'WASD')} {_c(GRAY, '(Move)')}"
    f" {_c(GRAY, '|')} {_c(WHITE, 'R')} {_c(GRAY, '(Rotate Mirror)')}"
    f" {_c(GRAY, '|')} {_c(WHITE, 'K')} {_c(GRAY, '(Restart)')}"
    f" {_c(GRAY, '|')} {_c(WHITE, 'Q')} {_c(GRAY, '(Disconnect)')}"
)


def _emit(lines: list[str], width: int, height: int, home: str) -> str:
    """Serialize frame lines to a terminal-sized escape sequence string."""
    out = [home]
    for i in range(height):
        content = lines[i] if i < len(lines) else ""
        out.append(content + ESC_K)
        out.append("\r\n" if i < height - 1 else "")
    return "".join(out)


def render_frame(game, width: int = MIN_W, height: int = MIN_H) -> str:
    """Build the gameplay frame filling the terminal, grid centered."""
    width = max(width, MIN_W)
    height = max(height, MIN_H)
    grid_w = game.layout.width + 2
    indent = max(2, (width - grid_w) // 2)

    # chrome: 4 header lines + 3 footer lines; grid centered in between
    middle = height - 7
    grid_h = game.layout.height
    pad_above = max(0, (middle - grid_h) // 2)
    pad_below = max(0, middle - grid_h - pad_above)

    lines: list[str] = [_rule(width)]
    lines.extend(_header_lines(game))
    lines.append(_rule(width))
    lines.extend([""] * pad_above)
    for y in range(game.layout.height):
        row = "".join(_cell_str(game, x, y) for x in range(game.layout.width))
        lines.append(" " * indent + row)
    lines.extend([""] * pad_below)
    lines.append(
        f"  {_c(GRAY, 'STATUS:')} {_c(YELLOW, _truncate(game.msg, width - 14))}"
    )
    lines.append(_CONTROLS_LINE)
    lines.append(_rule(width))
    return _emit(lines, width, height, HOME)


# --------------------------------------------------------------------- screens


def _screen(body: list[str], width: int, height: int) -> str:
    lines = [_rule(width), ""]
    lines.extend(body)
    lines.append("")
    lines.append(_rule(width))
    return _emit(lines, width, height, CLEAR)


def _indent(lines: list[str], spaces: int = 4) -> list[str]:
    pad = " " * spaces
    return [pad + line for line in lines]


def _colored_banner(text: str, color: str) -> list[str]:
    return [_c(color, row) for row in assets.banner(text)]


def render_title(width: int = MIN_W, height: int = MIN_H) -> str:
    from .levels import TITLE_LORE

    # fits exactly 24 rows on a standard terminal
    body = [
        *_indent(_colored_banner("QUANTUM GRID", CYAN)),
        *_indent(_colored_banner("2099", EMITTER_RED)),
        "",
        *_wrap_center(TITLE_LORE, width),
        "",
        _center(_c(GRAY, assets.LEGEND_ROW), width),
        _center(_c(GRAY, assets.LEGEND_LABELS), width),
        "",
        _center(
            "Rotate optical mirrors, redirect laser fire, power the receptors.", width
        ),
        _center(_c(BEAM_GREEN, ">>> PRESS ANY KEY TO JACK IN <<<"), width),
    ]
    return _screen(body, width, height)


def _node_label(i: int, unlocked: int, unlock_all: bool) -> str:
    from .levels import LEVELS

    if unlock_all or i <= unlocked:
        return _c(WHITE, f"[{i + 1}] NODE {i + 1:02d}") + _c(
            CYAN, f" - {LEVELS[i].name}"
        )
    return _c(GRAY, f"[{i + 1}] NODE {i + 1:02d} - {LEVELS[i].name}") + _c(
        RED, " [LOCKED]"
    )


def render_level_select(
    unlocked: int, unlock_all: bool = False, width: int = MIN_W, height: int = MIN_H
) -> str:
    from .levels import LEVELS

    body = [
        _center(_c(CYAN, "MAINFRAME NODE ACCESS"), width),
        "",
    ]
    half = (len(LEVELS) + 1) // 2
    for i in range(half):
        left = _node_label(i, unlocked, unlock_all)
        right = ""
        if i + half < len(LEVELS):
            right = _node_label(i + half, unlocked, unlock_all)
        pad = 36 - len(_strip_ansi(left))
        body.append("  " + left + " " * max(1, pad) + right)
    body.extend(
        [
            "",
            f"  Press 1-{len(LEVELS)} to jack in | ENTER for next node | Q to disconnect",
        ]
    )
    return _screen(body, width, height)


def render_level_intro(
    defn: LevelDef, bandwidth: int, width: int = MIN_W, height: int = MIN_H
) -> str:
    from .levels import LEVELS, parse_level

    layout = parse_level(defn.rows, defn.name)
    node = LEVELS.index(defn) + 1
    body = [
        "",
        _center(_c(EMITTER_RED, "NEW NODE DETECTED"), width),
        "",
        _center(_c(CYAN, f"NODE {node:02d} - {defn.name}"), width),
        _center(
            _c(
                GRAY,
                f"grid {layout.width}x{layout.height}"
                f" | {len(layout.mirrors)} mirrors | {len(layout.receptors)} receptors",
            ),
            width,
        ),
        "",
        *_wrap_center(defn.lore, width, color=GRAY),
        "",
        _center(_c(WHITE, f"OBJECTIVE: {_truncate(defn.intro, width - 16)}"), width),
        "",
        _center(
            f"BANDWIDTH: {_c(BEAM_GREEN, str(bandwidth))}%"
            f"  {_c(GRAY, '|')}  1% consumed per action",
            width,
        ),
        "",
        _center(_c(BEAM_GREEN, ">>> PRESS ANY KEY TO ENGAGE OPTICAL PROBE <<<"), width),
    ]
    return _screen(body, width, height)


def render_level_complete(
    game, next_index: int, width: int = MIN_W, height: int = MIN_H
) -> str:
    from .levels import LEVELS

    body = [
        "",
        _center(_c(BEAM_GREEN, "*** ACCESS GRANTED ***"), width),
        "",
        _center(
            _c(CYAN, f"NODE {game.level_index + 1:02d} - {game.defn.name}")
            + _c(BEAM_GREEN, " // EXTRACTION COMPLETE"),
            width,
        ),
        "",
        _center(_c(BEAM_GREEN, "BANDWIDTH REFRESHED TO 100%"), width),
        "",
        _center(
            f"Descend to NODE {next_index + 1:02d} - {LEVELS[next_index].name}", width
        ),
        "",
        _center(_c(BEAM_GREEN, ">>> PRESS ANY KEY TO CONTINUE <<<"), width),
    ]
    return _screen(body, width, height)


def render_game_over(game, width: int = MIN_W, height: int = MIN_H) -> str:
    from .levels import GAMEOVER_LORE

    body = [
        "",
        _center(_c(EMITTER_RED, "*** CONNECTION LOST ***"), width),
        "",
        _center(_c(RED, "BANDWIDTH DEPLETED - SESSION TERMINATED"), width),
        "",
        *_wrap_center(GAMEOVER_LORE, width, color=GRAY),
        "",
        _center(
            f"You fell on NODE {game.level_index + 1:02d} - {game.defn.name}.", width
        ),
        "",
        _center(_c(BEAM_GREEN, ">>> PRESS ANY KEY TO DISCONNECT <<<"), width),
    ]
    return _screen(body, width, height)


def render_victory(session, width: int = MIN_W, height: int = MIN_H) -> str:
    from .levels import VICTORY_LORE

    body = [
        "",
        _center(_c(BEAM_GREEN, "*** MAINFRAME COMPROMISED ***"), width),
        "",
        *_indent(_colored_banner("GRID", BEAM_GREEN)),
        "",
        *_wrap_center(VICTORY_LORE, width),
        "",
        _center(f"Total actions burned: {session.total_actions}", width),
        "",
        *_indent([_c(GRAY, row) for row in assets.VICTORY_MOTIF]),
        "",
        _center(_c(BEAM_GREEN, ">>> PRESS ANY KEY TO DISCONNECT <<<"), width),
    ]
    return _screen(body, width, height)


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
