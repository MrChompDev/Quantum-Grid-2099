#!/usr/bin/env python3
"""Procedural level generator for Quantum Grid 2099: BLACKOUT PROTOCOL.

CONSTRUCTIVE generation: a random beam path is built first (emitters,
turn-point mirrors AND splitter prisms, receptors on the path), which
guarantees the level is solvable by construction. Walls, teleport pads,
datashards, ICE daemon spawns, the player probe and the extraction node
are placed off-path; a difficulty-scaled subset of mirrors starts
flipped. Every candidate is verified with the BFS solver (solvable,
optimal within the sector's difficulty band, not already solved) plus a
shard-reachability check before being accepted.

Writes qgrid/level_data.py with a fixed seed for reproducible builds.
Campaign: 6 sectors x 8 nodes = 48 levels.

Run:  python3 scripts/generate_levels.py
"""

import os
import sys
from collections import deque
from random import Random

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from qgrid.levels import parse_level
from qgrid.lore import GAMEOVER_LORE, NODE_LORE, TITLE_LORE, VICTORY_LORE
from qgrid.physics import DIR_VEC, REFLECT, trace_beam
from qgrid.solver import solve_level

SEED = 2099
ZONE_SIZE = 8
N_LEVELS = 48

NAMES = [
    # Sector 1 - THE SPINE
    "FIRST LIGHT", "COLD BOOT", "WARM SIGNAL", "DEAD DROP",
    "LINE OF SIGHT", "SHORT CIRCUIT", "LIVE WIRE", "GATE CRASHER",
    # Sector 2 - NEON DISTRICT
    "PULSE STREET", "NEON RAIN", "SIGNAL NOISE", "BLACK MARKET",
    "SPLIT FOCUS", "PRISM ALLEY", "GHOST LANE", "DISTRICT LOCKDOWN",
    # Sector 3 - ICE FOUNDRY
    "FROSTBITE", "ICE BREAKER", "COLD STEEL", "THE HUNTER",
    "SENTINEL WALK", "FROZEN ASSETS", "GLASSHOUSE", "FOUNDRY CORE",
    # Sector 4 - THE MAZE
    "MAZE RUNNER", "WORMHOLE", "SIDE STEP", "TWISTED PAIR",
    "THE LONG WAY", "BLINK DRIVE", "LABYRINTH", "MAZE HEART",
    # Sector 5 - BLACK VAULT
    "VAULT DOOR", "SPLIT DECISION", "DAEMON DANCE", "CORRUPTED",
    "HEAVY ICE", "DOUBLE CROSS", "VAULT RUN", "THE CRUCIBLE",
    # Sector 6 - SINGULARITY CORE
    "THRESHOLD", "EVENT HORIZON", "CORE LIGHT", "LAST MILE",
    "SYSTEM SHOCK", "FINAL FIREWALL", "GRID HEART", "SINGULARITY",
]

# Difficulty bands per sector (BFS-optimal action count range).
ZONE_OPT_MIN = [12, 22, 24, 26, 30, 34]
ZONE_OPT_MAX = [45, 60, 65, 72, 80, 95]

# Splitter prisms per level (by sector, by node-in-sector index 0..7).
ZONE_SPLITTERS = [
    [0, 0, 0, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 1, 1, 1, 2],
    [0, 0, 1, 1, 1, 1, 2, 2],
    [0, 0, 0, 1, 1, 1, 1, 1],
    [1, 1, 2, 2, 2, 2, 3, 3],
    [1, 1, 2, 2, 2, 2, 2, 3],
]

# Teleport pad pairs per level (sector 4 + finale touches in sector 6).
ZONE_PADS = [
    [0, 0, 0, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 0, 0, 0],
    [0, 1, 1, 1, 1, 1, 1, 1],
    [0, 0, 0, 0, 0, 0, 0, 0],
    [0, 1, 0, 0, 1, 0, 0, 1],
]

# ICE daemons per level: (sentinels, hunters, corruptors).
def zone_enemies(zone: int, node: int) -> tuple[int, int, int]:
    if zone == 3:
        sent = 1 if node >= 2 else 0
        hunt = 1 if node in (3, 5, 7) else 0
        return sent, hunt, 0
    if zone == 4:
        sent = 1 if node >= 2 else 0
        hunt = 1 if node >= 3 else 0
        return sent, hunt, 0
    if zone == 5:
        corr = 1 if node >= 2 else 0
        hunt = 1 if node >= 4 else 0
        sent = 1 if node >= 6 else 0
        return sent, hunt, corr
    if zone == 6:
        corr = 1 if node >= 2 else 0
        hunt = 1 if node >= 1 else 0
        sent = 1 if node >= 3 else 0
        return sent, hunt, corr
    return 0, 0, 0


def level_sizes(i: int) -> tuple[int, int]:
    w = min(26 + (i - 1), 72)
    h = min(11 + (i - 1) // ZONE_SIZE, 16)
    return w, h


def _turn_glyph(incoming, outgoing):
    for glyph in ("/", "\\"):
        if REFLECT[glyph].get(incoming) == outgoing:
            return glyph
    return None


def _construct_full(rng, cfg):
    """Full construction including shards/enemies/pads. Returns dict or None."""
    w, h = cfg["w"], cfg["h"]
    mirrors: dict[tuple[int, int], str] = {}
    splitters: set[tuple[int, int]] = set()
    emitter_cells: set[tuple[int, int]] = set()
    emitters: list[tuple[tuple[int, int], str]] = []
    paths: list[set[tuple[int, int]]] = []
    interior = [(x, y) for x in range(1, w - 1) for y in range(1, h - 1)]
    hw_quota = cfg["n_mirrors"] + cfg["n_splitters"]

    def walk(ei, x, y, dx, dy):
        path: set[tuple[int, int]] = set()
        turns = rng.randint(1, max(1, hw_quota - len(mirrors) - len(splitters)))
        for _ in range(turns):
            seg_len = rng.randint(2, 8)
            moved = 0
            for _ in range(seg_len):
                nx, ny = x + dx, y + dy
                if not (0 < nx < w - 1 and 0 < ny < h - 1):
                    break
                if (nx, ny) in emitter_cells or (nx, ny) in mirrors or (nx, ny) in splitters:
                    break
                if (nx, ny) in path or any((nx, ny) in p for p in paths):
                    break
                path.add((nx, ny))
                x, y = nx, ny
                moved += 1
            if moved == 0:
                break
            if any((x, y) in p for j, p in enumerate(paths) if j != ei):
                break
            if len(splitters) < cfg["n_splitters"] and rng.random() < 0.5:
                splitters.add((x, y))
                for d in ((dy, -dx), (-dy, dx)):
                    path |= walk(ei, x, y, d[0], d[1])
                return path
            new_dir = rng.choice([(dy, dx), (-dy, -dx)])
            glyph = _turn_glyph((dx, dy), new_dir)
            if glyph is None:
                break
            mirrors[(x, y)] = glyph
            dx, dy = new_dir
        while True:
            nx, ny = x + dx, y + dy
            if not (0 < nx < w - 1 and 0 < ny < h - 1):
                break
            if (nx, ny) in emitter_cells or (nx, ny) in mirrors or (nx, ny) in splitters:
                break
            if (nx, ny) in path or any((nx, ny) in p for p in paths):
                break
            path.add((nx, ny))
            x, y = nx, ny
        return path

    for ei in range(cfg["n_emitters"]):
        free = [
            c for c in interior
            if c not in emitter_cells and c not in mirrors and c not in splitters
        ]
        if not free:
            return None
        start = rng.choice(free)
        direction = rng.choice(list(DIR_VEC.values()))
        emitters.append((start, next(k for k, v in DIR_VEC.items() if v == direction)))
        emitter_cells.add(start)
        paths.append(walk(ei, start[0], start[1], direction[0], direction[1]))

    all_path = set().union(*paths) if paths else set()
    hardware = set(mirrors) | splitters | emitter_cells

    if len(mirrors) < 1:
        return None
    receptor_candidates = sorted(all_path - hardware)
    if len(receptor_candidates) < cfg["n_receptors"]:
        return None
    receptors = rng.sample(receptor_candidates, cfg["n_receptors"])

    walls: set[tuple[int, int]] = set()
    for _ in range(cfg["n_walls"]):
        cx, cy = rng.choice(interior)
        dx, dy = rng.choice([(1, 0), (0, 1)])
        for _ in range(rng.randint(2, 5)):
            if not (0 < cx < w - 1 and 0 < cy < h - 1):
                break
            if (cx, cy) in all_path or (cx, cy) in hardware or (cx, cy) in receptors:
                break
            walls.add((cx, cy))
            cx, cy = cx + dx, cy + dy

    blocked = all_path | hardware | walls | set(receptors)
    free_cells = [c for c in interior if c not in blocked]
    if len(free_cells) < 10:
        return None

    # teleport pads
    pad_pair: list[tuple[int, int]] = []
    if cfg["n_pads"]:
        for _ in range(30):
            a, b = rng.sample(free_cells, 2)
            if abs(a[0] - b[0]) + abs(a[1] - b[1]) >= max(5, (w + h) // 3):
                pad_pair = [a, b]
                break
        if not pad_pair:
            return None
    pad_set = set(pad_pair)

    candidates = [c for c in free_cells if c not in pad_set]
    if len(candidates) < 6:
        return None
    player, exit_pos = rng.sample(candidates, 2)
    for _ in range(16):
        if abs(player[0] - exit_pos[0]) + abs(player[1] - exit_pos[1]) >= max(4, (w + h) // 4):
            break
        player, exit_pos = rng.sample(candidates, 2)

    # shards
    shard_pool = [c for c in candidates if c not in (player, exit_pos)]
    if len(shard_pool) < 2:
        return None
    shards = rng.sample(shard_pool, 2)

    # ICE daemons
    taken = {player, exit_pos} | pad_set | set(shards)
    enemy_cells: list[tuple[tuple[int, int], str]] = []
    kind_chars = ["S"] * cfg["n_sentinels"] + ["H"] * cfg["n_hunters"] + ["C"] * cfg["n_corruptors"]
    for kch in kind_chars:
        options = [
            c for c in candidates
            if c not in taken
            and abs(c[0] - player[0]) + abs(c[1] - player[1]) >= 5
            and sum(
                1 for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))
                if (c[0] + dx, c[1] + dy) in free_cells
                and (c[0] + dx, c[1] + dy) not in taken
            ) >= 2
        ]
        if not options:
            return None
        spot = rng.choice(options)
        enemy_cells.append((spot, kch))
        taken.add(spot)

    # flip a difficulty-scaled subset of mirrors for the initial state
    flip_count = min(
        len(mirrors), max(1, len(mirrors) // 2 + (1 if len(mirrors) > 3 else 0))
    )
    initial = dict(mirrors)
    for pos in rng.sample(sorted(mirrors), flip_count):
        initial[pos] = "/" if initial[pos] == "\\" else "\\"

    grid = [["." for _ in range(w)] for _ in range(h)]
    for x in range(w):
        grid[0][x] = grid[h - 1][x] = "#"
    for y in range(h):
        grid[y][0] = grid[y][w - 1] = "#"
    for pos in walls:
        grid[pos[1]][pos[0]] = "#"
    for pos in splitters:
        grid[pos[1]][pos[0]] = "+"
    for pos, glyph in initial.items():
        grid[pos[1]][pos[0]] = glyph
    for pos, d in emitters:
        grid[pos[1]][pos[0]] = d
    for pos in receptors:
        grid[pos[1]][pos[0]] = "*"
    for pos, kch in enemy_cells:
        grid[pos[1]][pos[0]] = kch
    for pos in shards:
        grid[pos[1]][pos[0]] = "$"
    if pad_pair:
        grid[pad_pair[0][1]][pad_pair[0][0]] = "T"
        grid[pad_pair[1][1]][pad_pair[1][0]] = "U"
    grid[player[1]][player[0]] = "@"
    grid[exit_pos[1]][exit_pos[0]] = "E"
    return tuple("".join(row) for row in grid)


def _reachable(layout, extra_links: dict) -> set:
    """Cells reachable from the player start (pads link both ways)."""
    start = layout.player_start
    seen = {start}
    queue = deque([start])
    while queue:
        x, y = queue.popleft()
        nxts = []
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            n = (x + dx, y + dy)
            if 0 <= n[0] < layout.width and 0 <= n[1] < layout.height:
                t = layout.rows[n[1]][n[0]]
                if t != "#" and t not in EMITTERS:
                    nxts.append(n)
        link = extra_links.get((x, y))
        if link is not None:
            nxts.append(link)
        for n in nxts:
            if n not in seen:
                seen.add(n)
                queue.append(n)
    return seen


EMITTERS = (">", "<", "^", "v")


def generate_level(index: int, rng: Random) -> dict:
    zone = (index - 1) // ZONE_SIZE + 1
    node = (index - 1) % ZONE_SIZE
    w, h = level_sizes(index)
    n_mirrors = min(1 + (index - 1) // 2, 9)
    n_receptors = min(1 + (index - 1) // 5, 4)
    n_emitters = 1 if index < 14 else (2 if index < 41 else 3)
    n_walls = min(2 + index // 2, 9)
    n_splitters = ZONE_SPLITTERS[zone - 1][node]
    n_pads = ZONE_PADS[zone - 1][node]
    n_sent, n_hunt, n_corr = zone_enemies(zone, node)
    opt_min, opt_max = ZONE_OPT_MIN[zone - 1], ZONE_OPT_MAX[zone - 1]
    if n_hunt:
        # Hunter levels must stay short enough that a couple of ICE strikes
        # (25% each) still fit inside the 100% bandwidth budget.
        opt_max = min(opt_max, 48)
    cfg = {
        "w": w, "h": h,
        "n_mirrors": n_mirrors, "n_receptors": n_receptors,
        "n_emitters": n_emitters, "n_walls": n_walls,
        "n_splitters": n_splitters, "n_pads": n_pads,
        "n_sentinels": n_sent, "n_hunters": n_hunt, "n_corruptors": n_corr,
    }

    attempts = 0
    while attempts < 500:
        attempts += 1
        rows = _construct_full(rng, cfg)
        if rows is None:
            continue
        try:
            layout = parse_level(rows, f"gen{index}")
        except ValueError:
            continue
        if len(layout.mirrors) < n_mirrors:
            continue
        path = solve_level(layout)
        if path is None:
            continue
        opt = len(path)
        if not (opt_min <= opt <= opt_max):
            continue
        trace = trace_beam(layout, layout.player_start, layout.mirrors)
        if trace.powered == set(layout.receptors):
            continue  # must not start solved
        # shards must be reachable from the start (pads count as links)
        reach = _reachable(layout, layout.pads)
        if any(s not in reach for s in layout.shards):
            continue
        if len(layout.splitters) < n_splitters:
            continue
        if len(layout.pads) // 2 < n_pads:
            continue
        if len(layout.enemies) < n_sent + n_hunt + n_corr:
            continue
        intro_bits = [
            f"Sector {zone:02d}, node {node + 1}.",
            f"{len(layout.mirrors)} mirrors",
        ]
        if layout.splitters:
            intro_bits.append(f"{len(layout.splitters)} splitter prisms")
        if layout.pads:
            intro_bits.append("a teleport pad pair")
        if layout.enemies:
            kinds = sorted(k for _, k in layout.enemies)
            intro_bits.append(
                f"ICE on the floor: {', '.join(k.upper() for k in kinds)}"
            )
        intro_bits.append(f"{len(layout.receptors)} receptors.")
        intro_bits.append("Power all receptors, reach the extraction node.")
        return {
            "name": NAMES[index - 1],
            "lore": NODE_LORE[zone - 1][node],
            "intro": " ".join(intro_bits),
            "rows": rows,
            "zone": zone,
            "par": opt,
            "bandwidth_start": 100,
            "bandwidth_floor": 0,
        }
    raise RuntimeError(f"could not generate level {index} after {attempts} attempts")


def main() -> int:
    rng = Random(SEED)
    levels = []
    print(f"generating {N_LEVELS} levels across 6 sectors (seed {SEED})...")
    for i in range(1, N_LEVELS + 1):
        data = generate_level(i, rng)
        rows = data["rows"]
        layout = parse_level(rows, data["name"])
        opt = len(solve_level(layout))
        levels.append(data)
        enemies = len(layout.enemies)
        print(
            f"  {i:2d}. {data['name']:18} z{data['zone']} {layout.width:2d}x{layout.height:2d}"
            f"  mirrors={len(layout.mirrors)} prisms={len(layout.splitters)}"
            f" pads={len(layout.pads) // 2} ice={enemies}"
            f" shards={len(layout.shards)} optimal={opt}",
            flush=True,
        )

    out_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "qgrid",
        "level_data.py",
    )
    with open(out_path, "w") as f:
        f.write('"""Generated level data for Quantum Grid 2099: BLACKOUT PROTOCOL.\n\n')
        f.write(f"Procedurally generated (seed {SEED}) and BFS-verified by\n")
        f.write("scripts/generate_levels.py. Regenerate with:\n\n")
        f.write("    python3 scripts/generate_levels.py\n\n")
        f.write("48 nodes across 6 sectors. Bandwidth refreshes to 100%\n")
        f.write('after every level. par = BFS-optimal action count.\n"""\n\n')
        f.write(f"TITLE_LORE = {TITLE_LORE!r}\n\n")
        f.write(f"GAMEOVER_LORE = {GAMEOVER_LORE!r}\n\n")
        f.write(f"VICTORY_LORE = {VICTORY_LORE!r}\n\n")
        f.write("LEVEL_DATA = (\n")
        for data in levels:
            f.write("    {\n")
            f.write(f'        "name": {data["name"]!r},\n')
            f.write(f'        "lore": {data["lore"]!r},\n')
            f.write(f'        "intro": {data["intro"]!r},\n')
            f.write(f'        "zone": {data["zone"]},\n')
            f.write(f'        "par": {data["par"]},\n')
            f.write('        "rows": (\n')
            f.writelines(f"            {row!r},\n" for row in data["rows"])
            f.write("        ),\n")
            f.write(f'        "bandwidth_start": {data["bandwidth_start"]},\n')
            f.write(f'        "bandwidth_floor": {data["bandwidth_floor"]},\n')
            f.write("    },\n")
        f.write(")\n")
    print(f"wrote {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
