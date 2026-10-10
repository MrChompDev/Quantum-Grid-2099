"""ANSI rendering engine for Quantum Grid 2099: BLACKOUT PROTOCOL.

Cyber-blue theme: blue probe on black, green laser fire, red emitters,
magenta ICE. Renders adaptive terminal frames (minimum 80x24) using
ANSI escape sequences. Every frame is drawn with a cursor-home redraw
(\\033[H) plus clear-to-end-of-line (\\033[K) per row to avoid flicker;
full clears (\\033[2J) are used only on screen transitions.
"""

from . import assets
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

ZONE_SIZE = 8
ZONE_COUNT = 6


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
    if pos == game.player:
        return _c(PLAYER_BLUE_ON_BLACK, assets.PLAYER_GLYPH)
    for en in game.daemons:
        if en["pos"] == pos:
            return _c(ICE_MAGENTA, assets.ENEMY_GLYPHS[en["kind"]])
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


def render_frame(game, width: int = MIN_W, height: int = MIN_H, total_score: int = 0) -> str:
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
    lines.extend(_header_lines(game, total_score))
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
    body = [
        *_indent(_colored_banner("QUANTUM GRID", CYAN)),
        *_indent(_colored_banner("2099", EMITTER_RED)),
        "",
        *_wrap_center("B L A C K O U T   P R O T O C O L", width, color=GRAY),
        "",
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
        _center(_c(BEAM_GREEN, ">>> PRESS ANY KEY TO JACK IN <<<"), width),
    ]
    return _screen(body, width, height)


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
                    f" {_c(GRAY, '|')} CODEX {_c(CYAN, str(len(save.get('codex', []))) + '/16')}",
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
            "  Press 1-6 to enter a sector | ENTER: next node | C: codex | Q: disconnect",
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
            "  Press 1-8 to jack in | ENTER: next uncleared node | Q: disconnect",
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
            if key in unlocked:
                mark = _c(BEAM_GREEN, "[+]")
                cols.append(f"{mark} {_c(WHITE, title)}")
            else:
                cols.append(f"{_c(GRAY, '[?]')} {_c(GRAY, '?' * len(title))}")
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
    game, next_index: int, session_score: int, width: int = MIN_W, height: int = MIN_H
) -> str:
    from .levels import LEVELS

    par = game.defn.par or game.actions
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
        _center(_c(BEAM_GREEN, "BANDWIDTH REFRESHED TO 100%"), width),
        "",
        _center(
            f"Next: NODE {next_index + 1:02d} - {LEVELS[next_index].name}", width
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
        _center(
            _c(GRAY, "Your progress is saved. The Grid keeps count even when you can't."),
            width,
        ),
        "",
        _center(_c(BEAM_GREEN, ">>> PRESS ANY KEY TO RE-JACK <<<"), width),
    ]
    return _screen(body, width, height)


def render_victory(
    save: dict,
    total_shards_in_game: int,
    width: int = MIN_W,
    height: int = MIN_H,
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
    true_end = total_shards_in_game > 0 and banked >= SHARDS_FOR_TRUE_ENDING * total_shards_in_game
    ending = TRUE_ENDING_LORE if true_end else STANDARD_ENDING_LORE
    body = [
        "",
        _center(_c(BEAM_GREEN, "*** MAINFRAME COMPROMISED ***"), width),
        "",
        *_indent(_colored_banner("GRID", BEAM_GREEN)),
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
