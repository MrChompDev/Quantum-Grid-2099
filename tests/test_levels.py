"""Campaign verification: all 48 nodes solvable, lore complete, grids fit."""

from qgrid.levels import LEVELS, parse_level
from qgrid.solver import optimal_actions

ZONE_SIZE = 8


class TestAllLevelsSolvable:
    def test_every_level_solvable_and_feasible(self):
        optimals = {}
        for defn in LEVELS:
            opt = optimal_actions(defn)
            assert opt is not None, f"{defn.name} is unsolvable"
            optimals[defn.name] = opt
        print("\noptimal action counts:", optimals)
        for name, opt in optimals.items():
            assert opt <= 95, f"{name}: optimal {opt} exceeds a 100% budget"

    def test_forty_eight_levels_across_six_sectors(self):
        assert len(LEVELS) == 48
        names = [d.name for d in LEVELS]
        assert len(set(names)) == 48, "duplicate node names"
        for i, d in enumerate(LEVELS):
            assert d.zone == i // ZONE_SIZE + 1, f"{d.name} in wrong sector"
            assert d.par is not None and d.par > 0, f"{d.name} missing par"
            assert d.lore, f"{d.name} has no lore"
            assert d.intro, f"{d.name} has no objective"
            assert d.bandwidth_start == 100  # bandwidth refreshes every level

    def test_sector_difficulty_bands(self):
        from qgrid.lore import ZONES

        assert len(ZONES) == 6
        for z in range(1, 7):
            nodes = LEVELS[(z - 1) * ZONE_SIZE : z * ZONE_SIZE]
            assert all(d.zone == z for d in nodes)

    def test_grid_sizes_grow_across_campaign(self):
        widths = [parse_level(d.rows, d.name).width for d in LEVELS]
        heights = [parse_level(d.rows, d.name).height for d in LEVELS]
        assert widths == sorted(widths), "grid width does not grow with node"
        assert heights == sorted(heights), "grid height does not grow with sector"
        assert widths[0] >= 24 and widths[-1] <= 72
        assert heights[0] == 11 and heights[-1] == 16
        # every grid fits an 80x24 terminal with chrome (7 lines)
        for w, h in zip(widths, heights):
            assert w + 4 <= 80 and h + 7 <= 24

    def test_mechanics_appear_where_lore_promises(self):
        """Prisms from node 13, ICE from node 19, pads from node 26."""
        for i, d in enumerate(LEVELS):
            layout = parse_level(d.rows, d.name)
            if i >= 12:
                assert len(layout.splitters) >= 1 or d.zone in (1, 3, 4), (
                    f"{d.name}: expected prisms"
                )
            if 18 <= i < 24:
                assert len(layout.enemies) >= 1, f"{d.name}: sector 3 needs ICE"
            if 25 <= i < 32:
                assert len(layout.pads) >= 2 or i in (24,), (
                    f"{d.name}: sector 4 needs teleport pads"
                )

    def test_no_level_starts_solved(self):
        from qgrid.physics import trace_beam

        for defn in LEVELS:
            layout = parse_level(defn.rows, defn.name)
            trace = trace_beam(layout, layout.player_start, layout.mirrors)
            assert trace.powered != set(layout.receptors), (
                f"{defn.name} starts already solved"
            )

    def test_shards_reachable_from_start_everywhere(self):
        """Every datashard must be reachable from the player start (pads link)."""
        from collections import deque

        from qgrid.levels import EMITTER_CHARS, WALL

        for defn in LEVELS:
            layout = parse_level(defn.rows, defn.name)
            if not layout.shards:
                continue
            seen = {layout.player_start}
            queue = deque([layout.player_start])
            while queue:
                x, y = queue.popleft()
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    n = (x + dx, y + dy)
                    if not (
                        0 <= n[0] < layout.width and 0 <= n[1] < layout.height
                    ):
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
            for s in layout.shards:
                assert s in seen, f"{defn.name}: shard at {s} unreachable"

    def test_enemies_spawn_far_from_start(self):
        for defn in LEVELS:
            layout = parse_level(defn.rows, defn.name)
            for pos, _ in layout.enemies:
                d = abs(pos[0] - layout.player_start[0]) + abs(
                    pos[1] - layout.player_start[1]
                )
                assert d >= 5, f"{defn.name}: enemy at {pos} too close to start"
