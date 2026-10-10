"""Level definitions and parsing for Quantum Grid 2099: BLACKOUT PROTOCOL.

Each level is an ASCII grid of characters (including the border walls).
Grid size varies per level (bigger nodes deeper in the campaign):

    #  mainframe wall (impassable, blocks beams)
    .  empty floor
    @  player probe start position
    >  laser emitter firing right      <  left      ^  up      v  down
    *  target receptor
    /  optical mirror (rotates to backslash and back)
    +  splitter prism (forks the beam into two perpendicular beams)
    T  teleport pad A (links to U)     U  teleport pad B (links to T)
    $  datashard (optional collectible: memory fragment of KAI)
    S  SENTINEL ICE spawn (patrol daemon)
    H  HUNTER ICE spawn (pursuit daemon)
    C  CORRUPTOR ICE spawn (sabotage daemon)
    E  extraction node

The 48 campaign nodes across 6 sectors are procedurally generated and
BFS-verified; see scripts/generate_levels.py and qgrid/level_data.py.
"""

from dataclasses import dataclass, field

from .level_data import GAMEOVER_LORE, LEVEL_DATA, TITLE_LORE, VICTORY_LORE

WALL = "#"
FLOOR = "."
PLAYER = "@"
RECEPTOR = "*"
MIRROR_A = "/"
MIRROR_B = "\\"
SPLITTER = "+"
PAD_A = "T"
PAD_B = "U"
SHARD = "$"
ENEMY_SPAWNS = ("S", "H", "C")  # sentinel, hunter, corruptor
EXIT = "E"
EMITTER_CHARS = (">", "<", "^", "v")

ENEMY_KIND_BY_CHAR = {"S": "sentinel", "H": "hunter", "C": "corruptor"}

__all__ = [
    "EMITTER_CHARS",
    "ENEMY_KIND_BY_CHAR",
    "ENEMY_SPAWNS",
    "EXIT",
    "FLOOR",
    "GAMEOVER_LORE",
    "LEVELS",
    "MIRROR_A",
    "MIRROR_B",
    "PAD_A",
    "PAD_B",
    "PLAYER",
    "RECEPTOR",
    "SHARD",
    "SPLITTER",
    "TITLE_LORE",
    "VICTORY_LORE",
    "WALL",
    "LevelDef",
    "LevelLayout",
    "parse_level",
]


@dataclass(frozen=True)
class LevelDef:
    name: str
    intro: str
    rows: tuple[str, ...]
    lore: str = ""
    zone: int = 1
    par: int | None = None
    # Hard-set bandwidth on entry (None = carry over from previous node).
    bandwidth_start: int | None = None
    # Minimum bandwidth on entry (applied after carry-over, capped at 100).
    bandwidth_floor: int = 0


@dataclass
class LevelLayout:
    width: int
    height: int
    rows: tuple[str, ...]
    walls: frozenset[tuple[int, int]] = field(default_factory=frozenset)
    mirrors: dict[tuple[int, int], str] = field(default_factory=dict)
    splitters: frozenset[tuple[int, int]] = field(default_factory=frozenset)
    pads: dict[tuple[int, int], tuple[int, int]] = field(default_factory=dict)
    shards: tuple[tuple[int, int], ...] = ()
    enemies: tuple[tuple[tuple[int, int], str], ...] = ()
    emitters: tuple[tuple[tuple[int, int], str], ...] = ()
    receptors: tuple[tuple[int, int], ...] = ()
    exit_pos: tuple[int, int] = (0, 0)
    player_start: tuple[int, int] = (0, 0)


def parse_level(rows: tuple[str, ...], name: str = "?") -> LevelLayout:
    """Parse a level's ASCII rows into a validated LevelLayout.

    The grid size is derived from the rows; the border must be intact.
    Teleport pads must come in exactly one T/U pair.
    """
    height = len(rows)
    if height < 3:
        raise ValueError(f"level '{name}' must have at least 3 rows, got {height}")
    width = len(rows[0])
    if width < 3:
        raise ValueError(f"level '{name}' must have at least 3 columns, got {width}")

    walls: set[tuple[int, int]] = set()
    mirrors: dict[tuple[int, int], str] = {}
    splitters: set[tuple[int, int]] = set()
    pads_a: list[tuple[int, int]] = []
    pads_b: list[tuple[int, int]] = []
    shards: list[tuple[int, int]] = []
    enemies: list[tuple[tuple[int, int], str]] = []
    emitters: list[tuple[tuple[int, int], str]] = []
    receptors: list[tuple[int, int]] = []
    exit_pos = None
    player_start = None

    for y, row in enumerate(rows):
        if len(row) != width:
            raise ValueError(
                f"level '{name}' row {y} has {len(row)} columns, expected {width}"
            )
        for x, ch in enumerate(row):
            pos = (x, y)
            if ch == WALL:
                walls.add(pos)
            elif ch == FLOOR:
                continue
            elif ch in (MIRROR_A, MIRROR_B):
                mirrors[pos] = ch
            elif ch == SPLITTER:
                splitters.add(pos)
            elif ch == PAD_A:
                pads_a.append(pos)
            elif ch == PAD_B:
                pads_b.append(pos)
            elif ch == SHARD:
                shards.append(pos)
            elif ch in ENEMY_SPAWNS:
                enemies.append((pos, ENEMY_KIND_BY_CHAR[ch]))
            elif ch in EMITTER_CHARS:
                emitters.append((pos, ch))
            elif ch == RECEPTOR:
                receptors.append(pos)
            elif ch == EXIT:
                if exit_pos is not None:
                    raise ValueError(f"level '{name}' has multiple extraction nodes")
                exit_pos = pos
            elif ch == PLAYER:
                if player_start is not None:
                    raise ValueError(f"level '{name}' has multiple player starts")
                player_start = pos
            else:
                raise ValueError(f"level '{name}' has unknown symbol {ch!r} at {pos}")

    # Border integrity: full wall rows top/bottom, wall columns at the sides.
    for x in range(width):
        if (x, 0) not in walls or (x, height - 1) not in walls:
            raise ValueError(f"level '{name}' has a broken top/bottom border")
    for y in range(height):
        if (0, y) not in walls or (width - 1, y) not in walls:
            raise ValueError(f"level '{name}' has a broken side border")

    if exit_pos is None:
        raise ValueError(f"level '{name}' has no extraction node")
    if player_start is None:
        raise ValueError(f"level '{name}' has no player start")
    if not emitters:
        raise ValueError(f"level '{name}' has no laser emitters")
    if not receptors:
        raise ValueError(f"level '{name}' has no receptors")
    if len(pads_a) != len(pads_b):
        raise ValueError(f"level '{name}' has unlinked teleport pads")
    if len(pads_a) > 1:
        raise ValueError(f"level '{name}' has more than one teleport pad pair")

    pads: dict[tuple[int, int], tuple[int, int]] = {}
    if pads_a:
        pads[pads_a[0]] = pads_b[0]
        pads[pads_b[0]] = pads_a[0]

    return LevelLayout(
        width=width,
        height=height,
        rows=tuple(rows),
        walls=frozenset(walls),
        mirrors=mirrors,
        splitters=frozenset(splitters),
        pads=pads,
        shards=tuple(shards),
        enemies=tuple(enemies),
        emitters=tuple(emitters),
        receptors=tuple(receptors),
        exit_pos=exit_pos,
        player_start=player_start,
    )


LEVELS: tuple[LevelDef, ...] = tuple(LevelDef(**d) for d in LEVEL_DATA)
