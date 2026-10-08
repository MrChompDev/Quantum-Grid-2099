"""Unit tests for game state, actions and bandwidth management."""

import pytest

from qgrid.game import BANDWIDTH_MAX, Game, start_bandwidth
from qgrid.levels import LEVELS


@pytest.fixture
def game1():
    return Game(0, 100)


class TestFirstLight:
    def test_initial_state(self, game1):
        assert game1.player == (17, 3)
        assert game1.mirrors == {(16, 3): "/"}
        assert game1.bandwidth == 100
        assert not game1.all_powered()
        assert not game1.exit_active()

    def test_rotate_once_solves_level(self, game1):
        assert game1.do_rotate() is True
        assert game1.mirrors[(16, 3)] == "\\"
        assert game1.all_powered()
        assert game1.exit_active()
        assert game1.bandwidth == 99

    def test_move_onto_active_exit_wins(self, game1):
        game1.do_rotate()
        # walk from (17,3) to exit (12,8): 5 left, 5 down
        for _ in range(5):
            game1.do_move(-1, 0)
        for _ in range(5):
            game1.do_move(0, 1)
        assert game1.player == (12, 8)
        assert game1.check_win()

    def test_rotate_costs_bandwidth(self, game1):
        game1.do_rotate()
        game1.do_rotate()  # rotate back
        assert game1.bandwidth == 98


class TestBlockedMoves:
    def test_wall_blocks_and_costs_nothing(self, game1):
        result = game1.do_move(0, 1)  # down into (17,4) which is floor
        assert result == "ok"
        # move left into the mirror tile -> walkable
        result = game1.do_move(-1, 0)
        assert result == "ok"
        assert game1.player == (16, 4)
        # now a real blocked move against a wall:
        game2 = Game(3, 25)  # bandwidth crunch
        game2.player = (7, 2)
        bw2 = game2.bandwidth
        assert game2.do_move(1, 0) == "blocked"  # (8,2) is wall
        assert game2.bandwidth == bw2  # no cost for blocked move
        assert game2.player == (7, 2)

    def test_emitter_blocks(self):
        game = Game(0, 100)
        game.player = (3, 3)
        result = game.do_move(-1, 0)  # (2,3) is the emitter
        assert result == "blocked"
        assert game.player == (3, 3)

    def test_out_of_bounds_blocks(self, game1):
        game1.player = (1, 1)
        assert game1.do_move(-1, 0) == "blocked"
        assert game1.do_move(0, -1) == "blocked"


class TestRotation:
    def test_rotate_requires_adjacent_mirror(self, game1):
        assert game1.do_rotate() is True  # starts adjacent
        game1.player = (16, 7)  # far from mirror
        bw2 = game1.bandwidth
        assert game1.do_rotate() is False
        assert game1.bandwidth == bw2  # failed rotate costs nothing

    def test_rotate_underfoot_mirror(self):
        game = Game(0, 100)
        game.player = (16, 3)  # standing on the mirror
        assert game.do_rotate() is True
        assert game.mirrors[(16, 3)] == "\\"


class TestBandwidth:
    def test_depletion_triggers_game_over(self):
        game = Game(0, 3)
        game.do_rotate()
        assert not game.game_over
        game.do_move(1, 0)
        assert not game.game_over
        game.do_move(1, 0)
        assert game.game_over  # 3 actions -> 0%

    def test_restart_restores_snapshot(self):
        game = Game(0, 40)
        game.do_rotate()
        game.do_move(1, 0)
        game.do_move(-1, 0)
        assert game.bandwidth == 37
        game.restart()
        assert game.bandwidth == 40
        assert game.mirrors == {(16, 3): "/"}
        assert game.player == (17, 3)
        assert not game.game_over

    def test_bonus_and_unlock(self, game1):
        game1.do_rotate()
        bw = game1.finish_level()
        assert bw == min(BANDWIDTH_MAX, 99 + 20)
        assert game1.unlocked == 1


class TestStartBandwidth:
    def test_hard_start_override(self):
        assert start_bandwidth(LEVELS[3], 100) == 46  # bandwidth crunch
        assert start_bandwidth(LEVELS[3], 0) == 46

    def test_floor(self):
        defn = LEVELS[4]  # core mainframe, floor 50
        assert start_bandwidth(defn, 10) == 80
        assert start_bandwidth(defn, 80) == 80

    def test_carry_capped_at_max(self):
        assert start_bandwidth(LEVELS[1], 120) == 100


class TestPlayerAbsorbsBeam:
    def test_standing_in_beam_blocks_receptor(self):
        game = Game(3, 100)  # bandwidth crunch
        game.mirrors[(6, 2)] = "\\"
        game.mirrors[(6, 11)] = "\\"
        game.mirrors[(14, 11)] = "/"
        game.mirrors[(14, 1)] = "\\"
        game.refresh()
        assert game.all_powered()
        # walk into the beam on row 8, between mirror and receptor
        game.player = (10, 11)
        game.refresh()
        assert not game.all_powered()  # probe blocks the beam
