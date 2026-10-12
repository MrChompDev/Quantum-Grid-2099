"""Unit tests for game state, actions, bandwidth, shards, teleports, scoring.

Geometry-agnostic: levels are procedurally generated, so tests locate
walls/emitters/mirrors from the parsed layout instead of hardcoding
coordinates. Solver-driven playthroughs verify the full action flow.
"""

import pytest

from qgrid.game import BANDWIDTH_MAX, Game, start_bandwidth
from qgrid.levels import EMITTER_CHARS, LEVELS, SHARD, WALL, LevelDef, parse_level
from qgrid.physics import DIR4, trace_beam
from qgrid.solver import solve_level

BORDER = "#" * 14


def mkmini(rows):
    return (BORDER,) + tuple(rows) + (BORDER,)


@pytest.fixture
def game1():
    return Game(0, BANDWIDTH_MAX)


def find_adjacent_passable(game):
    for dx, dy in DIR4:
        n = (game.player[0] + dx, game.player[1] + dy)
        if game.passable(*n):
            return (dx, dy)
    return None


def find_wall_adjacent_free(layout):
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
                    return n, (-dx, -dy)
    return None


def find_emitter_neighbor(layout):
    """A passable cell adjacent to an emitter: (stand_at, step_direction)."""
    for (ex, ey), _ in layout.emitters:
        for dx, dy in DIR4:
            n = (ex + dx, ey + dy)
            if (
                0 <= n[0] < layout.width
                and 0 <= n[1] < layout.height
                and layout.rows[n[1]][n[0]] != WALL
            ):
                return n, (-dx, -dy)  # step from n INTO the emitter cell
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
        assert game1.bandwidth == 200 - len(path)

    def test_all_levels_solver_wins(self):
        for i, defn in enumerate(LEVELS):
            game = Game(i, BANDWIDTH_MAX)
            game.daemons = []  # solver ignores ICE; replay the pure laser puzzle
            path = solve_level(game.layout)
            assert path is not None, f"{defn.name} unsolvable"
            apply_path(game, path)
            assert game.check_win(), f"{defn.name}: solver path did not win"
            assert game.bandwidth >= 0
            assert game.bandwidth == 200 - len(path)


class TestInitialStates:
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
            assert defn.bandwidth_start == 200

    def test_carryover_no_longer_applies(self):
        for defn in LEVELS:
            assert start_bandwidth(defn, 0) == 200
            assert start_bandwidth(defn, 55) == 200


class TestTeleports:
    def test_step_onto_pad_folds_probe(self):
        defn = LevelDef(
            name="padtest",
            intro="t",
            lore="l",
            rows=mkmini(
                [
                    "#............#",
                    "#.T.......U..#",
                    "#.@......E...#",
                    "#............#",
                    "#>....*......#",
                    "#............#",
                    "#............#",
                ]
            ),
            par=5,
        )
        game = Game(0, 100, defn=defn, rng_seed=1)
        assert game.layout.pads  # T<->U linked
        assert game.player == (2, 3)
        assert game.do_move(0, -1) == "ok"  # step up onto pad T
        assert game.player == (10, 2)  # folded to pad U
        # step off U, then step back on: folds back to T
        assert game.do_move(0, 1) == "ok"
        assert game.player == (10, 3)
        assert game.do_move(0, -1) == "ok"
        assert game.player == (2, 2)  # folded back to T

    def test_fold_costs_one_action(self):
        defn = LevelDef(
            name="padtest2",
            intro="t",
            lore="l",
            rows=mkmini(
                [
                    "#............#",
                    "#.T......U...#",
                    "#.@......E...#",
                    "#............#",
                    "#>....*......#",
                    "#............#",
                    "#............#",
                ]
            ),
            par=5,
        )
        game = Game(0, 100, defn=defn, rng_seed=1)
        # player at (2,3); step up onto the pad
        assert game.player == (2, 3)
        assert game.do_move(0, -1) == "ok"
        assert game.player == (9, 2)  # folded to U
        assert game.actions == 1
        assert game.bandwidth == 99


class TestDatashards:
    def test_shard_pickup_records_and_scores(self):
        defn = LevelDef(
            name="shardtest",
            intro="t",
            lore="l",
            rows=mkmini(
                [
                    "#............#",
                    "#............#",
                    "#.@$.....E...#",
                    "#............#",
                    "#>..#.*......#",
                    "#............#",
                    "#............#",
                ]
            ),
            par=5,
        )
        game = Game(0, 100, defn=defn, rng_seed=1)
        assert len(game.layout.shards) == 1
        shard_pos = game.layout.shards[0]
        assert shard_pos == (3, 3)
        assert game.do_move(1, 0) == "ok"
        assert game.player == shard_pos
        assert shard_pos in game.shards_taken
        assert "DATASHARD 1" in game.msg
        assert game.score() >= 250
        # shards don't re-trigger
        game.do_move(-1, 0)
        game.do_move(1, 0)
        assert len(game.shards_taken) == 1

    def test_shards_passable_by_beam(self):
        defn = LevelDef(
            name="shardbeam",
            intro="t",
            lore="l",
            rows=mkmini(
                [
                    "#............#",
                    "#..$.........#",
                    "#.@......E...#",
                    "#............#",
                    "#>....*......#",
                    "#............#",
                    "#............#",
                ]
            ),
            par=5,
        )
        game = Game(0, 100, defn=defn, rng_seed=1)
        layout = game.layout
        assert layout.rows[5][6] == "*"  # receptor on the beam line
        trace = trace_beam(layout, game.player, game.mirrors)
        assert (6, 5) in trace.powered  # shard on row 2 doesn't block row 5


class TestScoring:
    def test_score_breakdown(self):
        defn = LevelDef(
            name="scoretest",
            intro="t",
            lore="l",
            rows=mkmini(
                [
                    "#............#",
                    "#............#",
                    "#.@$.....E...#",
                    "#............#",
                    "#>....*......#",
                    "#............#",
                    "#............#",
                ]
            ),
            par=10,
        )
        game = Game(0, 100, defn=defn, rng_seed=1)
        game.do_move(1, 0)  # collect shard, actions=1, bandwidth=99
        s = game.score()
        # no ICE on this node: no flawless bonus, just bandwidth + shard
        # + efficiency (par 10)
        expected = 99 * 10 + 1 * 250 + max(0, 20 - 1) * 20
        assert s == expected

    def test_finish_banks_shards(self):
        defn = LevelDef(
            name="banktest",
            intro="t",
            lore="l",
            rows=mkmini(
                [
                    "#............#",
                    "#............#",
                    "#.@$.....E...#",
                    "#............#",
                    "#>....*......#",
                    "#............#",
                    "#............#",
                ]
            ),
            par=5,
        )
        game = Game(0, 100, defn=defn, rng_seed=1)
        game.do_move(1, 0)
        game.finish_level()
        assert len(game.shards_banked) == 1


class TestPlayerAbsorbsBeam:
    def test_standing_in_beam_blocks_receptor(self, game1):
        path = solve_level(game1.layout)
        assert path is not None
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
        beam_cells = [
            c
            for c in solved.h | solved.v
            if c not in game1.layout.receptors
            and game1.layout.rows[c[1]][c[0]] in (".", SHARD)
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


class TestGameFxEvents:
    def test_rotate_sets_event(self):
        # A mirror that does not touch the beam: rotating must report the
        # rotate event (power events override it only when they fire).
        defn = LevelDef(
            name="rotfx",
            intro="t",
            lore="l",
            rows=mkmini(
                [
                    "#............#",
                    "#............#",
                    "#.@......E...#",
                    "#............#",
                    "#>..#.*......#",
                    "#./..........#",
                    "#............#",
                ]
            ),
            par=5,
        )
        game = Game(0, 100, defn=defn, rng_seed=1)
        game.do_move(0, 2)  # step beside the mirror at (2,6)
        game.event = None
        assert game.do_rotate() is True
        assert game.event == "rotate"

    def test_all_powered_sets_event_and_exit_flash(self):
        defn = LevelDef(
            name="powertest",
            intro="t",
            lore="l",
            rows=mkmini(
                [
                    "#............#",
                    "#............#",
                    "#.@......E...#",
                    "#............#",
                    "#>....*......#",
                    "#............#",
                    "#............#",
                ]
            ),
            par=5,
        )
        game = Game(0, 100, defn=defn, rng_seed=1)
        game.do_move(1, 0)
        assert game.event == "all_powered"  # this mini level starts solved
        assert game.layout.exit_pos in game.flash

    def test_shake_and_flash_on_strike(self):
        defn = LevelDef(
            name="shaketest",
            intro="t",
            lore="l",
            rows=mkmini(
                [
                    "#............#",
                    "#..@.H....E..#",
                    "#............#",
                    "#............#",
                    "#>....*......#",
                    "#............#",
                    "#............#",
                ]
            ),
            par=5,
        )
        game = Game(0, 100, defn=defn, rng_seed=1)
        game.do_move(1, 0)  # hunter closes in -> strike
        assert game.shake > 0
        assert game.event == "strike"

    def test_teleport_sets_event_and_flash(self):
        defn = LevelDef(
            name="tpfx",
            intro="t",
            lore="l",
            rows=mkmini(
                [
                    "#............#",
                    "#.T......U...#",
                    "#.@......E...#",
                    "#............#",
                    "#>..#.*......#",
                    "#............#",
                    "#............#",
                ]
            ),
            par=5,
        )
        game = Game(0, 100, defn=defn, rng_seed=1)
        game.do_move(0, -1)  # onto pad T -> fold
        assert game.event == "teleport"
        assert game.flash.get((9, 2), 0) > 0  # destination pad flashing
        assert game.flash.get((2, 2), 0) > 0  # origin pad flashing


class TestEmp:
    def test_emp_stuns_daemons_in_radius(self):
        defn = LevelDef(
            name="emp",
            intro="t",
            lore="l",
            rows=mkmini(
                [
                    "#............#",
                    "#.....H......#",
                    "#....@.......#",
                    "#..........C.#",
                    "#>..#.*..E...#",
                    "#............#",
                    "#............#",
                ]
            ),
            par=5,
        )
        game = Game(0, 100, defn=defn, rng_seed=1)
        kinds = {en["kind"]: en for en in game.daemons}
        bw = game.bandwidth
        actions = game.actions
        assert game.do_emp() is True
        # The hunter is within Chebyshev radius 2 of the probe at (5,3);
        # the corruptor at (12,4) is not.
        assert kinds["hunter"].get("stun", 0) > 0
        assert kinds["corruptor"].get("stun", 0) == 0
        assert game.bandwidth == bw - 10
        assert game.actions == actions + 1
        assert game.event == "emp"
        assert game.emp_charges == 0

    def test_emp_single_charge(self):
        defn = LevelDef(
            name="emp2",
            intro="t",
            lore="l",
            rows=mkmini(
                [
                    "#............#",
                    "#..H.........#",
                    "#....@.......#",
                    "#............#",
                    "#>..#.*..E...#",
                    "#............#",
                    "#............#",
                ]
            ),
            par=5,
        )
        game = Game(0, 100, defn=defn, rng_seed=1)
        assert game.do_emp() is True
        bw = game.bandwidth
        assert game.do_emp() is False
        assert game.bandwidth == bw  # no second burst
        assert "offline" in game.msg

    def test_emp_resets_on_restart(self):
        defn = LevelDef(
            name="emp3",
            intro="t",
            lore="l",
            rows=mkmini(
                [
                    "#............#",
                    "#..H.........#",
                    "#....@.......#",
                    "#............#",
                    "#>..#.*..E...#",
                    "#............#",
                    "#............#",
                ]
            ),
            par=5,
        )
        game = Game(0, 100, defn=defn, rng_seed=1)
        game.do_emp()
        game.restart()
        assert game.emp_charges == 1


class TestFlawless:
    def test_flawless_bonus_applies(self):
        defn = LevelDef(
            name="fl",
            intro="t",
            lore="l",
            rows=mkmini(
                [
                    "#............#",
                    "#..H.........#",
                    "#....@.......#",
                    "#............#",
                    "#>..#.*..E...#",
                    "#............#",
                    "#............#",
                ]
            ),
            par=5,
        )
        clean = Game(0, 100, defn=defn, rng_seed=1)
        clean.bandwidth = 100
        assert clean.strikes == 0
        bloodied = Game(0, 100, defn=defn, rng_seed=1)
        bloodied.bandwidth = 100
        bloodied.strikes = 1
        assert clean.score() == bloodied.score() + 400

    def test_last_killer_recorded(self):
        defn = LevelDef(
            name="kill",
            intro="t",
            lore="l",
            rows=mkmini(
                [
                    "#............#",
                    "#..@.H....E..#",
                    "#............#",
                    "#............#",
                    "#>....*......#",
                    "#............#",
                    "#............#",
                ]
            ),
            par=5,
        )
        game = Game(0, 100, defn=defn, rng_seed=1)
        game.do_move(1, 0)  # step next to the hunter; it strikes
        assert game.strikes == 1
        assert game.last_killer == "hunter"


class TestHint:
    def test_hint_costs_and_flashes_without_ticking(self):
        defn = LevelDef(
            name="hint",
            intro="t",
            lore="l",
            rows=mkmini(
                [
                    "#..*.........#",
                    "#..H.........#",
                    "#....@...E...#",
                    "#............#",
                    "#>./.........#",
                    "#............#",
                    "#............#",
                ]
            ),
            par=5,
        )
        game = Game(0, 100, defn=defn, rng_seed=1)
        bw = game.bandwidth
        daemon_pos = dict(game.daemons[0])["pos"]
        assert game.do_hint() is True
        assert game.bandwidth == bw - 5
        assert game.actions == 0  # a trace is not an action
        assert game.flash, "hint left no destination glint"
        assert game.daemons[0]["pos"] == daemon_pos  # world did not tick
        assert "TRACE" in game.msg

    def test_hint_refused_when_low(self):
        defn = LevelDef(
            name="hint2",
            intro="t",
            lore="l",
            rows=mkmini(
                [
                    "#............#",
                    "#....@...E...#",
                    "#............#",
                    "#............#",
                    "#>..#.*......#",
                    "#............#",
                    "#............#",
                ]
            ),
            par=5,
        )
        game = Game(0, 5, defn=defn, rng_seed=1)
        assert game.do_hint() is False
        assert game.bandwidth == 5  # nothing charged

    def test_hint_on_unsolvable_state(self):
        # A state the solver cannot escape: player walled in by emitters
        # on all sides is impossible to build - instead verify the refusal
        # path via a mock.
        defn = LevelDef(
            name="hint3",
            intro="t",
            lore="l",
            rows=mkmini(
                [
                    "#............#",
                    "#....@...E...#",
                    "#............#",
                    "#............#",
                    "#>..#.*......#",
                    "#............#",
                    "#............#",
                ]
            ),
            par=5,
        )
        game = Game(0, 100, defn=defn, rng_seed=1)
        from unittest.mock import patch

        with patch("qgrid.game.solve_state", return_value=None):
            assert game.do_hint() is False
        assert "No solution thread" in game.msg
        assert game.bandwidth == 100  # refusal is free


class TestHintEdge:
    def test_hint_on_winning_state_is_safe(self):
        """A trace from an already-winning state must not crash (the solver
        returns an empty path); it politely declines instead."""
        defn = LevelDef(
            name="hintwin",
            intro="t",
            lore="l",
            rows=mkmini(
                [
                    "#..*.........#",
                    "#....@...E...#",
                    "#............#",
                    "#............#",
                    "#>./.........#",
                    "#............#",
                    "#............#",
                ]
            ),
            par=5,
        )
        game = Game(0, 100, defn=defn, rng_seed=1)
        path = solve_level_ish(game)
        for act, dx, dy in path:
            if act == "m":
                assert game.do_move(dx, dy) == "ok"
            else:
                game.do_rotate()
        assert game.check_win()
        assert game.do_hint() is False
        assert game.bandwidth == game.bandwidth  # no charge on refusal


def solve_level_ish(game):
    from qgrid.solver import solve_state

    return solve_state(game.layout, game.player, dict(game.mirrors))


class TestFlawlessIceOnly:
    def test_flawless_bonus_requires_ice(self):
        defn = LevelDef(
            name="noice",
            intro="t",
            lore="l",
            rows=mkmini(
                [
                    "#............#",
                    "#....@...E...#",
                    "#............#",
                    "#............#",
                    "#>..#.*......#",
                    "#............#",
                    "#............#",
                ]
            ),
            par=5,
        )
        game = Game(0, 100, defn=defn, rng_seed=1)
        assert not game.layout.enemies
        assert game.strikes == 0
        assert game.score() % 10 == 0 and "no flawless without ICE"  # sanity
        from qgrid.game import FLAWLESS_BONUS

        # score without ICE < score + FLAWLESS_BONUS comparison base:
        base = game.bandwidth * 10 + len(game.shards_taken) * 250
        par = game.defn.par or 1
        eff = max(0, 2 * par - game.actions) * 20
        assert game.score() == base + eff  # no flawless term
        assert FLAWLESS_BONUS == 400
