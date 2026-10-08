"""Level solvability verification via BFS over (player, mirrors) states.

Ground truth for the 5 handcrafted nodes: every level must be solvable,
and the optimal solution must fit the node's bandwidth budget.
"""

from collections import deque

from qgrid.game import BANDWIDTH_MAX, start_bandwidth
from qgrid.levels import EMITTER_CHARS, LEVELS, WALL, parse_level
from qgrid.physics import DIR4, trace_beam


def passable(layout, pos):
    x, y = pos
    if not (0 <= x < layout.width and 0 <= y < layout.height):
        return False
    terrain = layout.rows[y][x]
    return terrain not in (WALL,) and terrain not in EMITTER_CHARS


def solve(defn):
    """BFS for the shortest action sequence that powers all receptors and
    steps onto the extraction node. Returns the action path or None."""
    layout = parse_level(defn.rows, defn.name)
    receptors = set(layout.receptors)
    start = (layout.player_start, frozenset(layout.mirrors.items()))
    queue = deque([(start, ())])
    visited = {start}
    while queue:
        (player, mirrors_fs), path = queue.popleft()
        mirrors = dict(mirrors_fs)
        trace = trace_beam(layout, player, mirrors)
        if player == layout.exit_pos and trace.powered == receptors:
            return path
        # moves
        for dx, dy in DIR4:
            nxt = (player[0] + dx, player[1] + dy)
            if not passable(layout, nxt):
                continue
            state = (nxt, mirrors_fs)
            if state not in visited:
                visited.add(state)
                queue.append((state, path + ("m",)))
        # rotate adjacent (or underfoot) mirror
        target = None
        if player in mirrors:
            target = player
        else:
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
                queue.append((state, path + ("r",)))
    return None


class TestAllLevelsSolvable:
    def test_every_level_solvable(self):
        optimals = {}
        for defn in LEVELS:
            path = solve(defn)
            assert path is not None, f"{defn.name} is unsolvable"
            optimals[defn.name] = len(path)
        print("\noptimal action counts:", optimals)
        assert optimals["FIRST LIGHT"] <= 20
        assert optimals["THE CORNERING"] <= 90
        assert optimals["SPLIT FOCUS"] <= 90
        assert optimals["BANDWIDTH CRUNCH"] <= 46
        assert optimals["CORE MAINFRAME"] <= 80
        assert optimals["SINGULARITY"] <= 72

    def test_optimal_solutions_fit_entry_bandwidth(self):
        """Entering bandwidth chain check with perfect play."""
        carry = 100
        for defn in LEVELS:
            entry = start_bandwidth(defn, carry)
            optimal = len(solve(defn))
            assert optimal <= entry, (
                f"{defn.name}: optimal {optimal} > entry bandwidth {entry}"
            )
            carry = min(BANDWIDTH_MAX, entry - optimal + 20)


class TestIntendedSolutions:
    """Verify the hand-designed mirror configurations power all receptors."""

    def solved(self, defn, mirror_states):
        layout = parse_level(defn.rows, defn.name)
        trace = trace_beam(layout, layout.player_start, mirror_states)
        return trace.powered == set(layout.receptors)

    def test_first_light(self):
        assert self.solved(LEVELS[0], {(16, 3): "\\"})

    def test_the_cornering(self):
        assert self.solved(LEVELS[1], {(8, 2): "\\", (8, 9): "\\", (20, 9): "/"})

    def test_split_focus(self):
        assert self.solved(
            LEVELS[2],
            {(8, 1): "\\", (8, 8): "\\", (14, 8): "/", (14, 1): "/", (22, 1): "\\"},
        )

    def test_bandwidth_crunch(self):
        assert self.solved(
            LEVELS[3], {(6, 2): "\\", (6, 11): "\\", (14, 11): "/", (14, 1): "\\"}
        )

    def test_core_mainframe(self):
        assert self.solved(
            LEVELS[4],
            {
                (10, 2): "\\",
                (10, 10): "\\",
                (18, 10): "/",
                (38, 2): "/",
                (38, 12): "/",
                (30, 12): "\\",
            },
        )

    def test_singularity(self):
        assert self.solved(
            LEVELS[5],
            {
                (10, 2): "\\",
                (10, 10): "\\",
                (20, 10): "/",
                (36, 12): "\\",
                (36, 4): "/",
            },
        )
