"""BFS solver for Quantum Grid 2099.

Explores (player, mirror-state) space to verify level solvability and
compute optimal action counts. Teleport pads add both the stepped cell
and its linked destination as zero-extra-cost successors of the same
move. The beam trace (including splitter prisms) is only evaluated for
states where the player stands on the extraction node (the win
condition), keeping the search fast even on the biggest grids.

ICE daemons are intentionally NOT modeled: they are action-economy
hazards, not puzzle state. A level is "solvable" if the laser puzzle
admits a solution.
"""

from collections import deque

from .levels import EMITTER_CHARS, WALL, LevelDef, parse_level
from .physics import DIR4, trace_beam

# Actions: ("m", dx, dy) move, ("r", 0, 0) rotate.
Action = tuple[str, int, int]


def solve_level(layout) -> Action | None:
    """BFS for the shortest action sequence that powers all receptors and
    steps onto the extraction node. Returns the action path or None."""
    return solve_state(layout, layout.player_start, dict(layout.mirrors))


def solve_state(
    layout, player: tuple[int, int], mirrors: dict[tuple[int, int], str]
) -> Action | None:
    """BFS from an arbitrary (player, mirror) state - used by adaptive
    playthrough bots that must re-plan around live ICE."""
    receptors = set(layout.receptors)
    pads = layout.pads
    start = (player, frozenset(mirrors.items()))
    queue: deque[tuple[tuple[tuple[int, int], frozenset], tuple]] = deque([(start, ())])
    visited = {start}
    while queue:
        (pos, mirrors_fs), path = queue.popleft()
        if pos == layout.exit_pos:
            trace = trace_beam(layout, pos, dict(mirrors_fs))
            if trace.powered == receptors:
                return path
        for dx, dy in DIR4:
            nxt = (pos[0] + dx, pos[1] + dy)
            if not (0 <= nxt[0] < layout.width and 0 <= nxt[1] < layout.height):
                continue
            terrain = layout.rows[nxt[1]][nxt[0]]
            if terrain == WALL or terrain in EMITTER_CHARS:
                continue
            # Teleport pads are wormholes: stepping onto one always leaves
            # the probe at its twin, matching Game.do_move. The pad cell
            # itself is never a place the probe can stand.
            eff = pads.get(nxt, nxt)
            state = (eff, mirrors_fs)
            if state not in visited:
                visited.add(state)
                queue.append((state, path + (("m", dx, dy),)))
        mirror_map = dict(mirrors_fs)
        target = pos if pos in mirror_map else None
        if target is None:
            for dx, dy in DIR4:
                cand = (pos[0] + dx, pos[1] + dy)
                if cand in mirror_map:
                    target = cand
                    break
        if target is not None:
            new_mirrors = dict(mirrors_fs)
            new_mirrors[target] = "/" if new_mirrors[target] == "\\" else "\\"
            state = (pos, frozenset(new_mirrors.items()))
            if state not in visited:
                visited.add(state)
                queue.append((state, path + (("r", 0, 0),)))
    return None


def optimal_actions(defn: LevelDef) -> int | None:
    """Parse a level definition and return its optimal action count."""
    path = solve_level(parse_level(defn.rows, defn.name))
    return None if path is None else len(path)
