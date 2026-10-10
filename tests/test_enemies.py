"""Unit tests for ICE daemon AI: sentinel patrol, hunter pursuit, corruptor
sabotage, and ICE strikes."""

from qgrid.enemies import (
    DAEMON_STUN_TICKS,
    ICE_STRIKE_COST,
    cell_blocked_for_enemy,
    step_daemons,
)
from qgrid.game import Game
from qgrid.levels import LevelDef, parse_level

BORDER = "#" * 14


def mk(rows):
    return (BORDER,) + tuple(rows) + (BORDER,)


def make_game(rows, seed=7):
    defn = LevelDef(name="test", intro="t", lore="l", rows=mk(rows), par=10)
    return Game(0, 100, rng_seed=seed, defn=defn)


class TestParsingEnemies:
    def test_enemy_chars_parse_to_kinds(self):
        layout = parse_level(
            mk(
                [
                    "#............#",
                    "#.S...H...C..#",
                    "#....@....E..#",
                    "#............#",
                    "#>....*......#",
                    "#............#",
                    "#............#",
                ]
            ),
            "t",
        )
        kinds = sorted(k for _, k in layout.enemies)
        assert kinds == ["corruptor", "hunter", "sentinel"]


class TestSentinel:
    def test_patrol_walks_and_bounces(self):
        game = make_game(
            [
                "#............#",
                "#..S.........#",
                "#....@...E...#",
                "#............#",
                "#>....*......#",
                "#............#",
                "#............#",
            ],
            seed=1,
        )
        (sent,) = game.daemons
        assert sent["kind"] == "sentinel"
        # Force a horizontal patrol heading.
        sent["dir"] = (1, 0)
        start = sent["pos"]
        path = [start]
        for _ in range(6):
            step_daemons(game)
            path.append(sent["pos"])
        # It must have moved along row 1 and bounced off the wall (never left row).
        assert all(p[1] == start[1] for p in path)
        assert len(set(path)) >= 2  # it moved
        assert path[-1] != (11, start[1])  # never entered the border

    def test_sentinel_blocked_by_wall_bounces(self):
        game = make_game(
            [
                "#............#",
                "#.S#.........#",
                "#....@...E...#",
                "#............#",
                "#>....*......#",
                "#............#",
                "#............#",
            ],
            seed=1,
        )
        (sent,) = game.daemons
        sent["dir"] = (1, 0)  # straight into the wall at (3,2)
        step_daemons(game)
        assert sent["pos"] == (1, 2)  # bounced the other way


class TestHunter:
    def test_hunter_chases_player(self):
        game = make_game(
            [
                "#............#",
                "#.H..........#",
                "#............#",
                "#....@...E...#",
                "#>....*......#",
                "#............#",
                "#............#",
            ],
            seed=1,
        )
        (hunter,) = game.daemons
        hunter["dir"] = (0, 1)
        for _ in range(8):
            step_daemons(game)
        d = abs(hunter["pos"][0] - game.player[0]) + abs(
            hunter["pos"][1] - game.player[1]
        )
        assert d < 4, f"hunter did not close distance: {hunter['pos']}"

    def test_hunter_wanders_when_far(self):
        game = make_game(
            [
                "#............#",
                "#.H..........#",
                "#............#",
                "#............#",
                "#..........@.#",
                "#>....*..E...#",
                "#............#",
            ],
            seed=3,
        )
        (hunter,) = game.daemons
        before = hunter["pos"]
        step_daemons(game)
        # wander may keep it in place or move it; assert it never teleports
        assert abs(hunter["pos"][0] - before[0]) + abs(hunter["pos"][1] - before[1]) <= 1


class TestCorruptor:
    def test_corruptor_flips_adjacent_mirror(self):
        game = make_game(
            [
                "#............#",
                "#.C/.........#",
                "#....@...E...#",
                "#............#",
                "#>....*......#",
                "#............#",
                "#............#",
            ],
            seed=1,
        )
        (corr,) = game.daemons
        mirror_pos = (3, 2)
        before = game.mirrors[mirror_pos]
        step_daemons(game)
        assert game.mirrors[mirror_pos] != before  # flipped in place
        assert corr["pos"] == (2, 2)  # corruptor stood still

    def test_corruptor_walks_toward_nearest_mirror(self):
        game = make_game(
            [
                "#............#",
                "#.C..........#",
                "#............#",
                "#............#",
                "#..@.......E.#",
                "#./..........#",
                "#>.....*.....#",
            ],
            seed=1,
        )
        (corr,) = game.daemons
        start = corr["pos"]
        step_daemons(game)
        moved = abs(corr["pos"][0] - start[0]) + abs(corr["pos"][1] - start[1])
        assert moved == 1
        assert corr["pos"][1] == start[1] + 1  # stepped toward the mirror below


class TestIceStrike:
    def test_hunter_closing_triggers_strike_via_action(self):
        game = make_game(
            [
                "#............#",
                "#..@.H....E..#",
                "#............#",
                "#............#",
                "#>....*......#",
                "#............#",
                "#............#",
            ],
            seed=1,
        )
        # player (3,2), hunter (5,2): dist 2, within sense range 6
        (h,) = game.daemons
        h["dir"] = (-1, 0)
        bw = game.bandwidth
        game.do_move(1, 0)  # player steps to (4,2); hunter steps onto it
        assert game.strikes == 1
        assert game.player == (4, 2)  # probe keeps its position
        assert game.bandwidth == bw - 1 - ICE_STRIKE_COST
        assert h["stun"] == DAEMON_STUN_TICKS  # attacker stunned
        assert h["pos"] == (5, 2)  # knocked back one cell

    def test_strike_can_kill_at_low_bandwidth(self):
        game = make_game(
            [
                "#............#",
                "#..@.H....E..#",
                "#............#",
                "#............#",
                "#>....*......#",
                "#............#",
                "#............#",
            ],
            seed=1,
        )
        game.bandwidth = 20
        (h,) = game.daemons
        h["dir"] = (-1, 0)
        game.do_move(1, 0)
        assert game.bandwidth == 0
        assert game.game_over


class TestEnemyBlocking:
    def test_enemies_cannot_enter_walls_pads_exit(self):
        layout = parse_level(
            mk(
                [
                    "#....T...U...#",
                    "#............#",
                    "#..@...S...E.#",
                    "#............#",
                    "#>....*......#",
                    "#............#",
                    "#............#",
                ]
            ),
            "t",
        )
        assert cell_blocked_for_enemy(layout, set(), (5, 1))  # pad T
        assert cell_blocked_for_enemy(layout, set(), (9, 1))  # pad U
        assert cell_blocked_for_enemy(layout, set(), (11, 3))  # exit
        assert cell_blocked_for_enemy(layout, set(), (0, 0))  # border
        assert not cell_blocked_for_enemy(layout, set(), (3, 1))  # floor
