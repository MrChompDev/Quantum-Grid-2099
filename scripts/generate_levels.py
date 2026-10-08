#!/usr/bin/env python3
"""Procedural level generator for Quantum Grid 2099.

CONSTRUCTIVE generation: a random beam path is built first (emitters,
turn-point mirrors, receptors on the path), which guarantees the level is
solvable by construction. Walls, the player probe and the extraction node
are placed off-path; a difficulty-scaled subset of mirrors starts flipped.
Every candidate is verified with the BFS solver (solvable, optimal within
the tier's difficulty band) before being accepted.

Writes qgrid/level_data.py with a fixed seed for reproducible builds.

Run:  python3 scripts/generate_levels.py
"""

import os
import sys
from random import Random

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from qgrid.levels import EMITTER_CHARS, parse_level  # noqa: E402
from qgrid.physics import DIR_VEC, REFLECT, trace_beam  # noqa: E402
from qgrid.solver import solve_level  # noqa: E402

SEED = 2099
N_LEVELS = 16

NAMES = [
    "FIRST LIGHT",
    "COLD BOOT",
    "THE CORNERING",
    "DEAD SECTOR",
    "SPLIT FOCUS",
    "GHOST PROTOCOL",
    "NEON MAZE",
    "BLACKOUT",
    "FIREWALL",
    "OVERCLOCK",
    "DARK FIBER",
    "ZERO DAY",
    "TERMINAL VELOCITY",
    "DEEP GRID",
    "CORE MAINFRAME",
    "SINGULARITY",
]

LORE = [
    "The maintenance hatch seals shut behind you. OMNICORP's optical security hums in the dark. One mirror stands between you and the first node.",
    "The Grid felt you jack in. Alarm levels climbing. Bend the beam around their wall before the trace finds your signal.",
    "Deeper in, the corridors twist. OMNICORP built these walls to break runners like you. Prove them wrong.",
    "This node went dark years ago. Nobody has rerouted its lasers since. Power it back up - your way.",
    "Three receptors, one beam. The Grid never expected anyone to split the light this clean.",
    "You move like a ghost through the optical layer. The walls are thicker here. So is the security.",
    "Neon corridors, dead ends, and a maze that was designed never to be solved. Solve it anyway.",
    "Half the Grid is down and OMNICORP is scrambling. This node still burns bright. Kill the light.",
    "The firewall layer. Two emitters, no mercy. One wrong bounce and the trace burns you out.",
    "You are overclocking the probe. The Grid's defenses are overclocking right back at you.",
    "Old fiber, new tricks. The deep lines still carry light - if you can find the path through the dark.",
    "You found a zero day in their optics. Exploit it before they patch the light and lock you out.",
    "The Grid knows your name now. Every mirror is a trap. Every wall, a warning. Keep moving.",
    "Below the city, below the datacenters - the deep Grid. It dreams in laser light. Wake it up.",
    "The core mainframe. Two circuits, six mirrors, one chance. This is OMNICORP's last defense.",
    "The final node. The Grid's heart beats in green light. Liberate the city, runner.",
]

TITLE_LORE = (
    "2099. OMNICORP's Quantum Grid owns the city - power, traffic, data, everything. "
    "You are a netrunner with a light-beam probe and a debt to settle. "
    "Jack in. Reroute their security. Liberate the grid."
)

GAMEOVER_LORE = (
    "Your signal flatlines in the optical layer. Somewhere above, the city keeps "
    "burning under OMNICORP's grid. Maybe another runner will finish what you started."
)

VICTORY_LORE = (
    "The Quantum Grid falls silent. OMNICORP's hold on the city shatters. You pull "
    "the probe out of the last node as the lights come back on - block by block, "
    "street by street. The city is free, runner."
)

# Difficulty tiers: 4 tiers of 4 levels.
TIER_OPT_MIN = [10, 25, 35, 45]
TIER_OPT_MAX = [30, 50, 70, 92]


def _turn_glyph(incoming: tuple[int, int], outgoing: tuple[int, int]) -> str | None:
    """Mirror glyph that reflects `incoming` into `outgoing`, or None."""
    for glyph in ("/", "\\"):
        if REFLECT[glyph].get(incoming) == outgoing:
            return glyph
    return None


def _construct(rng: Random, w: int, h: int, n_emitters: int, n_mirrors: int,
               n_receptors: int, n_walls: int):
    """Build one candidate level. Returns (rows, ...) or None on conflict."""
    mirrors: dict[tuple[int, int], str] = {}   # solution state
    emitter_cells: set[tuple[int, int]] = set()
    emitters: list[tuple[tuple[int, int], str]] = []
    paths: list[set[tuple[int, int]]] = []
    interior = [(x, y) for x in range(1, w - 1) for y in range(1, h - 1)]

    for ei in range(n_emitters):
        free = [c for c in interior if c not in emitter_cells and c not in mirrors]
        if not free:
            return None
        start = rng.choice(free)
        direction = rng.choice(list(DIR_VEC.values()))
        emitters.append((start, next(k for k, v in DIR_VEC.items() if v == direction)))
        emitter_cells.add(start)
        path: set[tuple[int, int]] = set()
        pre_first: set[tuple[int, int]] = set()  # cells before the first mirror:
        # a receptor here would be powered unconditionally, so keep them out
        first_mirror_placed = False
        x, y = start
        dx, dy = direction
        turns = rng.randint(1, max(1, n_mirrors - len(mirrors)))
        for _ in range(turns):
            seg_len = rng.randint(2, 8)
            moved = 0
            for _ in range(seg_len):
                nx, ny = x + dx, y + dy
                if not (0 < nx < w - 1 and 0 < ny < h - 1):
                    break  # beam would exit before the turn
                if (nx, ny) in emitter_cells or (nx, ny) in mirrors:
                    break  # would interact with another emitter's hardware
                (path if first_mirror_placed else pre_first).add((nx, ny))
                x, y = nx, ny
                moved += 1
            if moved == 0:
                break  # stuck: end this walk without the turn
            if any((x, y) in p for j, p in enumerate(paths) if j != ei):
                break  # turn point would corrupt another emitter's path
            new_dir = rng.choice([(dy, dx), (-dy, -dx)])
            glyph = _turn_glyph((dx, dy), new_dir)
            if glyph is None:
                break
            mirrors[(x, y)] = glyph
            first_mirror_placed = True
            dx, dy = new_dir
        # final run to the border/obstacle
        while True:
            nx, ny = x + dx, y + dy
            if not (0 < nx < w - 1 and 0 < ny < h - 1):
                break
            if (nx, ny) in emitter_cells or (nx, ny) in mirrors:
                break
            if (nx, ny) in path:
                break  # would loop
            path.add((nx, ny))
            x, y = nx, ny
        paths.append(path)

    all_path = set().union(*paths) if paths else set()
    hardware = set(mirrors) | emitter_cells

    # receptors: on the beam path, never on mirrors/hardware
    receptor_candidates = sorted(all_path - hardware)
    if len(receptor_candidates) < n_receptors:
        return None
    receptors = rng.sample(receptor_candidates, n_receptors)

    # walls: random runs off-path
    walls: set[tuple[int, int]] = set()
    for _ in range(n_walls):
        cx, cy = rng.choice(interior)
        dx, dy = rng.choice([(1, 0), (0, 1)])
        run_len = rng.randint(2, 5)
        for _ in range(run_len):
            if not (0 < cx < w - 1 and 0 < cy < h - 1):
                break
            if (cx, cy) in all_path or (cx, cy) in hardware or (cx, cy) in receptors:
                break
            walls.add((cx, cy))
            cx, cy = cx + dx, cy + dy

    blocked = all_path | hardware | walls | set(receptors)

    # player + exit: off every beam path and entity
    free_cells = [c for c in interior if c not in blocked]
    if len(free_cells) < 2:
        return None
    player, exit_pos = rng.sample(free_cells, 2)

    # flip a difficulty-scaled subset of mirrors for the initial state
    flip_count = min(len(mirrors), max(1, len(mirrors) // 2 + (1 if len(mirrors) > 3 else 0)))
    initial = dict(mirrors)
    for pos in rng.sample(sorted(mirrors), flip_count):
        initial[pos] = "/" if initial[pos] == "\\" else "\\"

    # assemble rows
    grid = [["." for _ in range(w)] for _ in range(h)]
    for x in range(w):
        grid[0][x] = grid[h - 1][x] = "#"
    for y in range(h):
        grid[y][0] = grid[y][w - 1] = "#"
    for pos in walls:
        grid[pos[1]][pos[0]] = "#"
    for pos, glyph in initial.items():
        grid[pos[1]][pos[0]] = glyph
    for pos, d in emitters:
        grid[pos[1]][pos[0]] = d
    for pos in receptors:
        grid[pos[1]][pos[0]] = "*"
    grid[player[1]][player[0]] = "@"
    grid[exit_pos[1]][exit_pos[0]] = "E"
    return tuple("".join(row) for row in grid)


def generate_level(index: int, rng: Random) -> dict:
    tier = (index - 1) // 4
    w = min(24 + (index - 1) * 3, 70)
    h = min(11 + (index - 1) // 5, 14)
    n_mirrors = min(1 + (index - 1) // 2, 8)
    n_receptors = min(1 + (index - 1) // 4, 4)
    n_emitters = 1 if index < 10 else 2
    n_walls = min(2 + index // 2, 8)
    opt_min, opt_max = TIER_OPT_MIN[tier], TIER_OPT_MAX[tier]

    for attempt in range(400):
        rows = _construct(rng, w, h, n_emitters, n_mirrors, n_receptors, n_walls)
        if rows is None:
            continue
        try:
            layout = parse_level(rows, f"gen{index}")
        except ValueError:
            continue
        path = solve_level(layout)
        if path is None:
            continue
        if len(layout.mirrors) < n_mirrors:
            continue  # want the full mirror quota placed
        opt = len(path)
        if not (opt_min <= opt <= opt_max):
            continue
        # the initial state must not already be solved
        trace = trace_beam(layout, layout.player_start, layout.mirrors)
        if trace.powered == set(layout.receptors):
            continue
        return {
            "name": NAMES[index - 1],
            "lore": LORE[index - 1],
            "intro": (
                f"Node {index:02d} of the OMNICORP Quantum Grid. "
                f"{len(layout.mirrors)} mirrors, {len(layout.receptors)} receptors"
                + (f", {len(layout.emitters)} emitters" if len(layout.emitters) > 1 else "")
                + ". Power all receptors, reach the extraction node."
            ),
            "rows": rows,
            "bandwidth_start": 100,  # bandwidth refreshes after every level
            "bandwidth_floor": 0,
        }
    raise RuntimeError(f"could not generate level {index} after 400 attempts")


def main() -> int:
    rng = Random(SEED)
    levels = []
    print(f"generating {N_LEVELS} levels (seed {SEED})...")
    for i in range(1, N_LEVELS + 1):
        data = generate_level(i, rng)
        rows = data["rows"]
        layout = parse_level(rows, data["name"])
        opt = len(solve_level(layout))
        levels.append(data)
        print(
            f"  {i:2d}. {data['name']:18} {layout.width}x{layout.height}"
            f"  mirrors={len(layout.mirrors)} receptors={len(layout.receptors)}"
            f" emitters={len(layout.emitters)} optimal={opt}",
            flush=True,
        )

    out_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                            "qgrid", "level_data.py")
    with open(out_path, "w") as f:
        f.write('"""Generated level data for Quantum Grid 2099.\n\n')
        f.write(f"Procedurally generated (seed {SEED}) and BFS-verified by\n")
        f.write("scripts/generate_levels.py. Regenerate with:\n\n")
        f.write("    python3 scripts/generate_levels.py\n\n")
        f.write('Bandwidth refreshes to 100% after every level.\n"""\n\n')
        f.write(f"TITLE_LORE = {TITLE_LORE!r}\n\n")
        f.write(f"GAMEOVER_LORE = {GAMEOVER_LORE!r}\n\n")
        f.write(f"VICTORY_LORE = {VICTORY_LORE!r}\n\n")
        f.write("LEVEL_DATA = (\n")
        for data in levels:
            f.write("    {\n")
            f.write(f'        "name": {data["name"]!r},\n')
            f.write(f'        "lore": {data["lore"]!r},\n')
            f.write(f'        "intro": {data["intro"]!r},\n')
            f.write('        "rows": (\n')
            for row in data["rows"]:
                f.write(f'            {row!r},\n')
            f.write("        ),\n")
            f.write(f'        "bandwidth_start": {data["bandwidth_start"]},\n')
            f.write(f'        "bandwidth_floor": {data["bandwidth_floor"]},\n')
            f.write("    },\n")
        f.write(")\n")
    print(f"wrote {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
