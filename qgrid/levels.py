"""Level definitions and parsing for Quantum Grid 2099.

Each level is an ASCII grid of characters (including the border walls).
Grid size varies per level (bigger nodes later in the campaign):
    #  mainframe wall (impassable, blocks beams)
    .  empty floor
    @  player probe start position
    >  laser emitter firing right
    <  laser emitter firing left
    ^  laser emitter firing up
    v  laser emitter firing down
    *  target receptor
    /  optical mirror (rotates to backslash and back)
    E  extraction node
"""

from dataclasses import dataclass, field

WALL = "#"
FLOOR = "."
PLAYER = "@"
RECEPTOR = "*"
MIRROR_A = "/"
MIRROR_B = "\\"
EXIT = "E"
EMITTER_CHARS = (">", "<", "^", "v")


@dataclass(frozen=True)
class LevelDef:
    name: str
    intro: str
    rows: tuple[str, ...]
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
    emitters: tuple[tuple[tuple[int, int], str], ...] = ()
    receptors: tuple[tuple[int, int], ...] = ()
    exit_pos: tuple[int, int] = (0, 0)
    player_start: tuple[int, int] = (0, 0)


def parse_level(rows: tuple[str, ...], name: str = "?") -> LevelLayout:
    """Parse a level's ASCII rows into a validated LevelLayout.

    The grid size is derived from the rows; the border must be intact.
    """
    height = len(rows)
    if height < 3:
        raise ValueError(f"level '{name}' must have at least 3 rows, got {height}")
    width = len(rows[0])
    if width < 3:
        raise ValueError(f"level '{name}' must have at least 3 columns, got {width}")

    walls: set[tuple[int, int]] = set()
    mirrors: dict[tuple[int, int], str] = {}
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

    return LevelLayout(
        width=width,
        height=height,
        rows=tuple(rows),
        walls=frozenset(walls),
        mirrors=mirrors,
        emitters=tuple(emitters),
        receptors=tuple(receptors),
        exit_pos=exit_pos,
        player_start=player_start,
    )


LEVELS: tuple[LevelDef, ...] = (
    LevelDef(
        name="FIRST LIGHT",
        intro="Rotate the single mirror once using R to complete the direct line.",
        rows=(
            "########################",
            "#......................#",
            "#......................#",
            "#.>............./@.....#",
            "#......................#",
            "#......................#",
            "#......................#",
            "#......................#",
            "#...........E...*......#",
            "#......................#",
            "########################",
        ),
        bandwidth_start=100,
    ),
    LevelDef(
        name="THE CORNERING",
        intro="A central wall spans the node. Position three mirrors to route the beam around it.",
        rows=(
            "##############################",
            "#.............#..............#",
            "#.>...../.....#..............#",
            "#.............#..............#",
            "#.............#.....*........#",
            "#...@.........#..............#",
            "#.............#..............#",
            "#.............#..............#",
            "#.............#..............#",
            "#......./...........\\.....E..#",
            "#............................#",
            "##############################",
        ),
    ),
    LevelDef(
        name="SPLIT FOCUS",
        intro="Chain the beam through three receptors across the node. Five mirrors required.",
        rows=(
            "####################################",
            "#.>...../.....\\......./............#",
            "#.............*....................#",
            "#..................................#",
            "#...@...*..........................#",
            "#..................................#",
            "#.....................*............#",
            "#..................................#",
            "#......./.....\\........E...........#",
            "#..................................#",
            "#..................................#",
            "####################################",
        ),
    ),
    LevelDef(
        name="BANDWIDTH CRUNCH",
        intro="Tight maze, tight move budget. Precise pathing only - you cannot afford to backtrack.",
        rows=(
            "########################################",
            "#.......#..*../..E......#..............#",
            "#.>.../.#.......#.......#.......#......#",
            "#.......#.......#.......#.......#......#",
            "#.......#.......#.......#.......#......#",
            "#.......#.....*.#.......#.......#......#",
            "#.......#.......#.......#.......#......#",
            "#.......#.......#.......#.......#......#",
            "#.......#.......#.......#.......#......#",
            "#.......#.......#.......#.......#......#",
            "#.@.....#.......#.......#.......#......#",
            "#...../.......\\.#...............#......#",
            "########################################",
        ),
        bandwidth_start=46,
    ),
    LevelDef(
        name="CORE MAINFRAME",
        intro="Two emitters, three receptors, six mirrors. Align both optical circuits without crossing beams.",
        rows=(
            "################################################",
            "#..............................................#",
            "#.>......./...........................\\.......<#",
            "#..............................................#",
            "#.................*............................#",
            "#....@.........................................#",
            "#..............................................#",
            "#.........*....................................#",
            "#.............................*................#",
            "#..............................................#",
            "#........./.......\\............................#",
            "#..............................E...............#",
            "#............................./.......\\........#",
            "################################################",
        ),
        bandwidth_floor=80,
    ),
    LevelDef(
        name="SINGULARITY",
        intro="FINAL NODE: the grid's core. Two circuits, three receptors, five mirrors. Liberate the mainframe.",
        rows=(
            "########################################################",
            "#......................................................#",
            "#.>......./.................#..........................#",
            "#...........................#..........................#",
            "#...................*.......#.......\\.......*..........#",
            "#...........................#...........E..............#",
            "#.........*.................#..........................#",
            "#...@.......................#..........................#",
            "#...........................#..........................#",
            "#...........................#..........................#",
            "#........./.........\\.......#..........................#",
            "#...........................#..........................#",
            "#.................................../.................<#",
            "########################################################",
        ),
        bandwidth_floor=72,
    ),
)
