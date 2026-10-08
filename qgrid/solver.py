"""BFS solver for Quantum Grid 2099.

Explores (player, mirror-state) space to verify level solvability and
compute optimal action counts. The beam trace is only evaluated for
states where the player stands on the extraction node (the win
condition), keeping the search fast even on the biggest grids.
"""

from collections import deque

from .levels import EMITTER_CHARS, WALL, LevelDef, parse_level
from .physics import DIR4, trace_beam

# Actions: ("m", dx, dy) move, ("r", 0, 0) rotate.
Action = tuple[str, int, int]


def solve_level(layout) -> Action | None:
    """BFS for the shortest action sequence that powers all receptors and
    steps onto the extraction node. Returns the action path or None."""
    receptors = set(layout.receptors)
    start = (layout.player_start, frozenset(layout.mirrors.items()))
    queue: deque[tuple[tuple[tuple[int, int], frozenset], tuple]] = deque([(start, ())])
    visited = {start}
    while queue:
        (player, mirrors_fs), path = queue.popleft()
        if player == layout.exit_pos:
            trace = trace_beam(layout, player, dict(mirrors_fs))
            if trace.powered == receptors:
                return path
        for dx, dy in DIR4:
            nxt = (player[0] + dx, player[1] + dy)
            if not (0 <= nxt[0] < layout.width and 0 <= nxt[1] < layout.height):
                continue
            terrain = layout.rows[nxt[1]][nxt[0]]
            if terrain == WALL or terrain in EMITTER_CHARS:
                continue
            state = (nxt, mirrors_fs)
            if state not in visited:
                visited.add(state)
                queue.append((state, path + (("m", dx, dy),)))
        mirrors = dict(mirrors_fs)
        target = player if player in mirrors else None
        if target is None:
            for dx, dy in DIR4:
                cand = (player[0] + dx, player[1] + dy)
                if cand in mirrors:
                    target = cand
                    break
        if target is not None:
            new_mirrors = dict(mirrors_fs)
            new_mirrors[target] = "/" if new_mirrors[target] == "\\" else "\\"
            state = (player, frozenset(new_mirrors.items()))
            if state not in visited:
                visited.add(state)
                queue.append((state, path + (("r", 0, 0),)))
    return None


def optimal_actions(defn: LevelDef) -> int | None:
    """Parse a level definition and return its optimal action count."""
    path = solve_level(parse_level(defn.rows, defn.name))
    return None if path is None else len(path)
