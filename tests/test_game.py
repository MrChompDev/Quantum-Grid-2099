"""Unit tests for game state, actions and bandwidth management.

Geometry-agnostic: levels are procedurally generated, so tests locate
walls/emitters/mirrors from the parsed layout instead of hardcoding
coordinates. Solver-driven playthroughs verify the full action flow.
"""

import pytest

from qgrid.game import BANDWIDTH_MAX, Game, start_bandwidth
from qgrid.levels import EMITTER_CHARS, LEVELS, WALL, parse_level
from qgrid.physics import DIR4, trace_beam
from qgrid.solver import solve_level


@pytest.fixture
def game1():
    return Game(0, 100)


def find_adjacent_passable(game):
    for dx, dy in DIR4:
        n = (game.player[0] + dx, game.player[1] + dy)
        if game.passable(*n):
            return (dx, dy)
    return None


def find_wall_adjacent_free(layout):
    """A wall cell with a passable neighbor: (stand_at, move_direction)."""
    for y in range(1, layout.height - 1):
        for x in range(1, layout.width - 1):
            if layout.rows[y][x] != WALL:
                continue
            for dx, dy in DIR4:
                n = (x + dx, y + dy)
                if not (0 <= n[0] < layout.width and 0 <= n[1] < layout.height):
                    continue
                t = layout.rows[n[1]][n[0]]
                if t != WALL and t not in EMITTER_CHARS:
                    return n, (-dx, -dy)  # stand at n, step back into the wall
    return None


def find_emitter_neighbor(layout):
    for (ex, ey), _ in layout.emitters:
        for dx, dy in DIR4:
            n = (ex + dx, ey + dy)
            if (
                0 <= n[0] < layout.width
                and 0 <= n[1] < layout.height
                and layout.rows[n[1]][n[0]] != WALL
            ):
                return n, (dx, dy)
    return None


def apply_path(game, path):
    for act, dx, dy in path:
        if act == "m":
            assert game.do_move(dx, dy) == "ok"
        else:
            assert game.do_rotate() is True


class TestSolverPlaythrough:
    def test_level1_solver_path_wins(self, game1):
        path = solve_level(game1.layout)
        assert path is not None
        assert not game1.all_powered()  # level 1 starts unsolved
        apply_path(game1, path)
        assert game1.check_win()
        assert game1.bandwidth == 100 - len(path)

    def test_all_levels_solver_wins(self):
        for i, defn in enumerate(LEVELS):
            game = Game(i, 100)
            path = solve_level(game.layout)
            assert path is not None, f"{defn.name} unsolvable"
            apply_path(game, path)
            assert game.check_win(), f"{defn.name}: solver path did not win"
            assert game.bandwidth >= 0
            assert game.bandwidth == 100 - len(path)


class TestInitialStates:
    def test_level1_single_flipped_mirror(self, game1):
        assert len(game1.mirrors) == 1
        assert not game1.all_powered()

    def test_no_level_starts_solved(self):
        for defn in LEVELS:
            layout = parse_level(defn.rows, defn.name)
            trace = trace_beam(layout, layout.player_start, layout.mirrors)
            assert trace.powered != set(layout.receptors), (
                f"{defn.name} starts already solved"
            )


class TestBlockedMoves:
    def test_wall_blocks_and_costs_nothing(self, game1):
        found = find_wall_adjacent_free(game1.layout)
        assert found is not None
        stand, (dx, dy) = found
        game1.player = stand
        bw = game1.bandwidth
        assert game1.do_move(dx, dy) == "blocked"
        assert game1.bandwidth == bw  # no cost for blocked move
        assert game1.player == stand

    def test_emitter_blocks(self, game1):
        found = find_emitter_neighbor(game1.layout)
        assert found is not None
        stand, (dx, dy) = found
        game1.player = stand
        assert game1.do_move(dx, dy) == "blocked"
        assert game1.player == stand

    def test_out_of_bounds_blocks(self, game1):
        game1.player = (1, 1)
        assert game1.do_move(-1, 0) == "blocked"
        assert game1.do_move(0, -1) == "blocked"


class TestRotation:
    def test_rotate_adjacent_mirror(self, game1):
        pos = next(iter(game1.mirrors))
        stood = False
        for dx, dy in DIR4:
            n = (pos[0] + dx, pos[1] + dy)
            if game1.passable(*n):
                game1.player = n
                stood = True
                break
        assert stood
        bw = game1.bandwidth
        assert game1.do_rotate() is True
        assert game1.bandwidth == bw - 1

    def test_rotate_underfoot_mirror(self, game1):
        pos = next(iter(game1.mirrors))
        game1.player = pos  # mirrors are walkable
        assert game1.do_rotate() is True

    def test_rotate_requires_adjacent_mirror(self, game1):
        layout = game1.layout
        for y in range(1, layout.height - 1):
            for x in range(1, layout.width - 1):
                terrain = layout.rows[y][x]
                if terrain == WALL or terrain in EMITTER_CHARS:
                    continue
                if (x, y) in game1.mirrors:
                    continue
                if any((x + dx, y + dy) in game1.mirrors for dx, dy in DIR4):
                    continue
                game1.player = (x, y)
                bw = game1.bandwidth
                assert game1.do_rotate() is False
                assert game1.bandwidth == bw  # failed rotate costs nothing
                return
        pytest.fail("no free cell without an adjacent mirror found")


class TestBandwidth:
    def test_depletion_triggers_game_over(self, game1):
        game = Game(0, 3)
        moved = 0
        while moved < 3:
            step = find_adjacent_passable(game)
            assert step is not None
            dx, dy = step
            assert game.do_move(dx, dy) == "ok"
            moved += 1
            if moved < 3:
                assert game.do_move(-dx, -dy) == "ok"
                moved += 1
        assert game.game_over

    def test_restart_restores_snapshot(self, game1):
        game = Game(0, 40)
        dx, dy = find_adjacent_passable(game)
        game.do_move(dx, dy)
        game.do_move(-dx, -dy)
        assert game.bandwidth == 38
        game.restart()
        assert game.bandwidth == 40
        assert game.mirrors == game.layout.mirrors
        assert game.player == game.layout.player_start
        assert not game.game_over

    def test_finish_refreshes_bandwidth(self, game1):
        dx, dy = find_adjacent_passable(game1)
        game1.do_move(dx, dy)
        bw = game1.finish_level()
        assert bw == BANDWIDTH_MAX
        assert game1.unlocked == 1


class TestStartBandwidth:
    def test_refresh_after_each_level(self):
        for defn in LEVELS:
            assert defn.bandwidth_start == 100  # refreshes every level

    def test_carryover_no_longer_applies(self):
        for defn in LEVELS:
            assert start_bandwidth(defn, 0) == 100
            assert start_bandwidth(defn, 55) == 100


class TestPlayerAbsorbsBeam:
    def test_standing_in_beam_blocks_receptor(self, game1):
        path = solve_level(game1.layout)
        assert path is not None
        # replay the solution to reach the solved mirror state
        mirrors = dict(game1.mirrors)
        player = game1.player
        for act, dx, dy in path:
            if act == "m":
                player = (player[0] + dx, player[1] + dy)
            else:
                target = player if player in mirrors else None
                if target is None:
                    for ddx, ddy in DIR4:
                        cand = (player[0] + ddx, player[1] + ddy)
                        if cand in mirrors:
                            target = cand
                            break
                mirrors[target] = "/" if mirrors[target] == "\\" else "\\"
        solved = trace_beam(game1.layout, player, mirrors)
        assert solved.powered == set(game1.layout.receptors)
        # find a plain-floor beam cell whose block un-powers a receptor
        beam_cells = [
            c
            for c in solved.h | solved.v
            if c not in game1.layout.receptors and game1.layout.rows[c[1]][c[0]] == "."
        ]
        assert beam_cells
        for cell in beam_cells:
            blocked = trace_beam(game1.layout, cell, mirrors)
            if blocked.powered != set(game1.layout.receptors):
                game1.player = cell
                game1.mirrors = mirrors
                game1.refresh()
                assert not game1.all_powered()
                return
        pytest.fail("no beam cell blocks a receptor when occupied")
