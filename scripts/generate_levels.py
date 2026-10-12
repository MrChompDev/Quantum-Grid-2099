#!/usr/bin/env python3
"""Procedural level generator CLI for Quantum Grid 2099: BLACKOUT PROTOCOL.

Writes qgrid/level_data.py with a fixed seed for reproducible builds.
Campaign: 6 sectors x 8 nodes = 48 levels.

Run:  python3 scripts/generate_levels.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from random import Random

from qgrid.generator import N_LEVELS, SEED, generate_level
from qgrid.levels import parse_level
from qgrid.lore import GAMEOVER_LORE, TITLE_LORE, VICTORY_LORE
from qgrid.solver import solve_level


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
        f.write("48 nodes across 6 sectors. Bandwidth refreshes to 200%\n")
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
