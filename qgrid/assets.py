"""Visual assets for Quantum Grid 2099: unicode glyph theme + ASCII art."""

# ------------------------------------------------------------------ glyphs
# In-game entity glyphs (unicode upgrade over plain ASCII).

PLAYER_GLYPH = "@"

EMITTER_GLYPHS = {
    ">": "\u25b6",  # right
    "<": "\u25c0",  # left
    "^": "\u25b2",  # up
    "v": "\u25bc",  # down
}

RECEPTOR_GLYPH = "\u25c9"  # target receptor
EXIT_GLYPH = "\u03a9"  # extraction node (omega)
WALL_GLYPH = "\u2593"  # mainframe structure (medium shade)
FLOOR_GLYPH = "\u00b7"  # empty floor (middle dot)

MIRROR_GLYPHS = ("/", "\\")

SPLITTER_GLYPH = "\u25c7"  # splitter prism (diamond)
PAD_GLYPHS = {"T": "\u00bb", "U": "\u00ab"}  # teleport pads (linked pair)
SHARD_GLYPH = "\u25c6"  # datashard (memory fragment of KAI)

SENTINEL_GLYPH = "\u2716"  # patrol daemon
HUNTER_GLYPH = "\u2620"  # pursuit daemon
CORRUPTOR_GLYPH = "\u03a8"  # sabotage daemon
ENEMY_GLYPHS = {
    "sentinel": SENTINEL_GLYPH,
    "hunter": HUNTER_GLYPH,
    "corruptor": CORRUPTOR_GLYPH,
}

BEAM_H = "\u2500"  # horizontal beam
BEAM_V = "\u2502"  # vertical beam
BEAM_X = "\u253c"  # crossing

BORDER_H = "\u2500"
BORDER_V = "\u2502"
CORNERS = ("\u250c", "\u2510", "\u2514", "\u2518")  # TL, TR, BL, BR

# ------------------------------------------------------------------- banner

_BANNER_FONT: dict[str, tuple[str, str, str, str, str]] = {
    "Q": ("█████", "█...█", "█...█", "█..██", ".████"),
    "U": ("█...█", "█...█", "█...█", "█...█", ".███."),
    "A": (".███.", "█...█", "█████", "█...█", "█...█"),
    "N": ("█...█", "██..█", "█.█.█", "█..██", "█...█"),
    "T": ("█████", "..█..", "..█..", "..█..", "..█.."),
    "M": ("█...█", "██.██", "█.█.█", "█...█", "█...█"),
    "G": (".████", "█....", "█.███", "█...█", ".████"),
    "R": ("████.", "█...█", "████.", "█.█..", "█..██"),
    "D": ("████.", "█...█", "█...█", "█...█", "████."),
    "I": ("█████", "..█..", "..█..", "..█..", "█████"),
    "L": ("█....", "█....", "█....", "█....", "█████"),
    "B": ("████.", "█...█", "████.", "█...█", "████."),
    "E": ("█████", "█....", "████.", "█....", "█████"),
    "S": (".████", "█....", ".███.", "....█", "████."),
    "C": (".████", "█....", "█....", "█....", ".████"),
    "F": ("█████", "█....", "████.", "█....", "█...."),
    "H": ("█...█", "█...█", "█████", "█...█", "█...█"),
    "K": ("█...█", "█..█.", "███..", "█..█.", "█...█"),
    "O": (".███.", "█...█", "█...█", "█...█", ".███."),
    "P": ("████.", "█...█", "████.", "█....", "█...."),
    "V": ("█...█", "█...█", "█...█", ".█.█.", "..█.."),
    "W": ("█...█", "█...█", "█.█.█", "██.██", "█...█"),
    "X": ("█...█", ".█.█.", "..█..", ".█.█.", "█...█"),
    "Y": ("█...█", ".█.█.", "..█..", "..█..", "..█.."),
    "Z": ("█████", "...█.", "..█..", ".█...", "█████"),
    "1": ("..█..", ".██..", "..█..", "..█..", "█████"),
    "2": (".███.", "█...█", "..██.", ".█...", "█████"),
    "0": (".███.", "█...█", "█.███", "█...█", ".███."),
    "9": ("████.", "█...█", "████.", "...█.", ".███."),
    " ": (".....", ".....", ".....", ".....", "....."),
}


def banner(text: str) -> list[str]:
    """Render text in 5-row block letters. Returns the 5 raw rows."""
    rows = ["", "", "", "", ""]
    for ch in text.upper():
        glyph = _BANNER_FONT.get(ch, _BANNER_FONT[" "])
        for i in range(5):
            rows[i] += glyph[i] + " "
    return [row.rstrip() for row in rows]


# --------------------------------------------------------------- title motif

# Laser-diagram legend strip: entities with their glyphs.
LEGEND_ROW = (
    f"{EMITTER_GLYPHS['>']} {BEAM_H * 3} {RECEPTOR_GLYPH}"
    f"   {MIRROR_GLYPHS[0]} {MIRROR_GLYPHS[1]} {SPLITTER_GLYPH}"
    f"   {PAD_GLYPHS['T']}{PAD_GLYPHS['U']} {SHARD_GLYPH}"
    f"   {WALL_GLYPH * 3}"
    f"   {PLAYER_GLYPH} {EXIT_GLYPH}"
)

LEGEND_LABELS = (
    "EMITTER     MIRRORS PRISM  PADS SHARD   WALL     PROBE EXIT"
)

# Decorative circuit motif for the title screen.
TITLE_MOTIF = [
    (
        f"      {EMITTER_GLYPHS['>']}{BEAM_H * 12}{MIRROR_GLYPHS[1]}"
        f"{BEAM_V * 4}"
        f"{MIRROR_GLYPHS[0]}{BEAM_H * 8}{RECEPTOR_GLYPH}"
    ),
    f"      {FLOOR_GLYPH * 13}{BEAM_V}{FLOOR_GLYPH * 12}{BEAM_V}{FLOOR_GLYPH * 8}{BEAM_V}",
    f"      {WALL_GLYPH * 3}{FLOOR_GLYPH * 10}{BEAM_V}{FLOOR_GLYPH * 12}{BEAM_V}{FLOOR_GLYPH * 8}{BEAM_V}",
    f"      {FLOOR_GLYPH * 13}{BEAM_V}{FLOOR_GLYPH * 12}{BEAM_V}{FLOOR_GLYPH * 8}{RECEPTOR_GLYPH}",
]

# -------------------------------------------------------------- victory art

VICTORY_MOTIF = [
    (
        f"  {RECEPTOR_GLYPH} {BEAM_H * 6} {MIRROR_GLYPHS[0]}"
        f"   {WALL_GLYPH * 4}   {EMITTER_GLYPHS['^']}"
        f"   {MIRROR_GLYPHS[1]} {BEAM_V}"
    ),
    (
        f"  {BEAM_V} {FLOOR_GLYPH * 6} {BEAM_V}"
        f"   {WALL_GLYPH}{FLOOR_GLYPH * 2}{WALL_GLYPH}   {BEAM_V}"
        f"   {FLOOR_GLYPH} {FLOOR_GLYPH}  {BEAM_V}"
    ),
    (
        f"  {BEAM_V} {FLOOR_GLYPH * 6} {MIRROR_GLYPHS[1]}"
        f"   {WALL_GLYPH}{FLOOR_GLYPH * 2}{WALL_GLYPH}   {BEAM_H * 3}"
        f"   {MIRROR_GLYPHS[0]} {BEAM_V}"
    ),
    (
        f"  {BEAM_V} {FLOOR_GLYPH * 6} {FLOOR_GLYPH}"
        f"   {WALL_GLYPH * 4}   {FLOOR_GLYPH * 3}   {FLOOR_GLYPH} {BEAM_V}"
    ),
]
