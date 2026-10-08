"""Level solvability verification via BFS.

Levels are procedurally generated (constructive: the beam path is built
first, so a solution exists by construction) and re-verified here with
the BFS solver as the independent safety net.
"""

from qgrid.levels import LEVELS, parse_level
from qgrid.solver import optimal_actions


class TestAllLevelsSolvable:
    def test_every_level_solvable_and_feasible(self):
        optimals = {}
        for defn in LEVELS:
            opt = optimal_actions(defn)
            assert opt is not None, f"{defn.name} is unsolvable"
            optimals[defn.name] = opt
        print("\noptimal action counts:", optimals)
        for name, opt in optimals.items():
            assert opt <= 92, f"{name}: optimal {opt} exceeds a 100% budget"

    def test_sixteen_levels_with_lore(self):
        assert len(LEVELS) == 16
        names = [d.name for d in LEVELS]
        assert len(set(names)) == 16, "duplicate node names"
        for d in LEVELS:
            assert d.lore, f"{d.name} has no lore"
            assert d.intro, f"{d.name} has no objective"
            assert d.bandwidth_start == 100  # bandwidth refreshes every level

    def test_grid_sizes_grow_across_campaign(self):
        widths = [parse_level(d.rows, d.name).width for d in LEVELS]
        heights = [parse_level(d.rows, d.name).height for d in LEVELS]
        assert widths == sorted(widths), "grid width does not grow with level"
        assert widths[0] == 24 and widths[-1] == 69
        assert heights[0] == 11 and heights[-1] == 14
        # every grid fits an 80x24 terminal with chrome (7 lines)
        for w, h in zip(widths, heights):
            assert w + 4 <= 80 and h + 7 <= 24
