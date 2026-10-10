#!/usr/bin/env python3
"""Full campaign audit: verifies every one of the 48 nodes is complete.

Per node checks:
  - parses + has all required entities
  - BFS-solvable without ICE, optimal within the sector's difficulty band
  - does not start pre-solved
  - every datashard reachable from the start (teleport pads count)
  - ICE spawns are legal (off pads/exit, far enough from the probe start)
  - LIVE-ICE bot playthrough: a re-planning agent wins within the 100%
    bandwidth budget (the real winnability guarantee)

Run:  python3 scripts/audit_levels.py
"""

import os
import sys
import time
from collections import deque

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from qgrid.bot import bot_play
from qgrid.levels import EMITTER_CHARS, LEVELS, WALL, parse_level
from qgrid.solver import solve_level

ZONE_SIZE = 8
ZONE_OPT_MAX = {1: 45, 2: 60, 3: 65, 4: 72, 5: 80, 6: 95}

BOT_BUDGET_ATTEMPTS = 8
BOT_TIME_LIMIT_S = 45.0


def shards_reachable(layout) -> bool:
    if not layout.shards:
        return True
    seen = {layout.player_start}
    queue = deque([layout.player_start])
    while queue:
        x, y = queue.popleft()
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            n = (x + dx, y + dy)
            if not (0 <= n[0] < layout.width and 0 <= n[1] < layout.height):
                continue
            t = layout.rows[n[1]][n[0]]
            if t == WALL or t in EMITTER_CHARS:
                continue
            if n not in seen:
                seen.add(n)
                queue.append(n)
            if n in layout.pads and layout.pads[n] not in seen:
                seen.add(layout.pads[n])
                queue.append(layout.pads[n])
    return all(s in seen for s in layout.shards)


def enemies_legal(layout) -> bool:
    for pos, _ in layout.enemies:
        # S/H/C terrain IS the daemon's spawn cell (legal); pads and the
        # exit are not.
        if layout.rows[pos[1]][pos[0]] in ("T", "U", "E"):
            return False
        d = abs(pos[0] - layout.player_start[0]) + abs(pos[1] - layout.player_start[1])
        if d < 5:
            return False
    return True


def main() -> int:
    failures = []
    print(f"auditing {len(LEVELS)} nodes (BFS + live-ICE bot)...")
    total_opt = 0
    t0 = time.monotonic()
    for i, defn in enumerate(LEVELS):
        layout = parse_level(defn.rows, defn.name)
        problems = []

        path = solve_level(layout)
        if path is None:
            problems.append("UNSOLVABLE")
        else:
            opt = len(path)
            total_opt += opt
            zone_max = ZONE_OPT_MAX[defn.zone]
            if opt > zone_max:
                problems.append(f"opt {opt} > sector max {zone_max}")
            if defn.par is not None and abs(defn.par - opt) > 0:
                problems.append(f"stale par {defn.par} != optimal {opt}")

        trace_path = solve_level(layout)
        if trace_path is not None:
            # pre-solved check
            from qgrid.physics import trace_beam

            trace = trace_beam(layout, layout.player_start, layout.mirrors)
            if trace.powered == set(layout.receptors):
                problems.append("starts pre-solved")

        if not shards_reachable(layout):
            problems.append("unreachable shard")
        if not enemies_legal(layout):
            problems.append("illegal ICE spawn")

        won, strikes, resets = bot_play(i)
        if not won:
            problems.append(f"ICE bot FAILED (strikes={strikes}, resets={resets})")

        mark = "OK " if not problems else "BAD"
        ice_note = ",".join(sorted({k.upper() for _, k in layout.enemies})) or "-"
        print(
            f"  {mark} {i + 1:02d} {defn.name:18} z{defn.zone} {ice_note:14}"
            f" par={defn.par:3} shards={len(layout.shards)} "
            f"bot={'W' if won else 'X'} strikes={strikes}"
            + (f"  <-- {'; '.join(problems)}" if problems else ""),
            flush=True,
        )
        if problems:
            failures.append((i + 1, defn.name, problems))

    dt = time.monotonic() - t0
    print(f"\naudit done in {dt:.1f}s - total optimal actions: {total_opt}")
    if failures:
        print(f"FAILURES: {len(failures)}")
        for num, name, problems in failures:
            print(f"  node {num:02d} {name}: {'; '.join(problems)}")
        return 1
    print("ALL 48 NODES COMPLETE - every level solvable, beatable with live ICE")
    return 0


if __name__ == "__main__":
    sys.exit(main())
