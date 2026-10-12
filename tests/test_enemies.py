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
        assert (
            abs(hunter["pos"][0] - before[0]) + abs(hunter["pos"][1] - before[1]) <= 1
        )


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


class TestCorruptorTargetShift:
    def test_corruptor_shifts_targets(self):
        """The corruptor must not pin a single mirror: over a window it
        seeks different targets (it may re-flip one en route, but the
        target shifts)."""
        game = make_game(
            [
                "#............#",
                "#.C/.........#",
                "#............#",
                "#............#",
                "#..../.......#",
                "#..........@.#",
                "#>....*..E...#",
            ],
            seed=1,
        )
        (corr,) = game.daemons
        first = (3, 2)
        # tick 1: flips the adjacent mirror
        step_daemons(game)
        assert corr["last_target"] == first
        seen = {corr["last_target"]}
        for _ in range(40):
            step_daemons(game)
            seen.add(corr["last_target"])
        assert seen >= {first, (5, 5)}, f"corruptor pinned one mirror: {seen}"


class TestCorruptorProbeGrip:
    def test_corruptor_respects_probe_grip(self):
        """A mirror the probe is holding (on or adjacent) is protected from
        corruption - standing with your hands on the optic shields it."""
        game = make_game(
            [
                "#............#",
                "#.C/.........#",
                "#............#",
                "#..@.........#",
                "#............#",
                "#>....*..E...#",
                "#............#",
            ],
            seed=1,
        )
        mirror_pos = (3, 2)
        before = game.mirrors[mirror_pos]
        for _ in range(20):
            step_daemons(game)
        assert game.mirrors[mirror_pos] == before, (
            "corruptor flipped a mirror the probe was holding"
        )

    def test_corruptor_flips_when_probe_far(self):
        game = make_game(
            [
                "#............#",
                "#.C/.........#",
                "#............#",
                "#............#",
                "#..........@.#",
                "#>....*..E...#",
                "#............#",
            ],
            seed=1,
        )
        mirror_pos = (3, 2)
        before = game.mirrors[mirror_pos]
        step_daemons(game)
        assert game.mirrors[mirror_pos] != before


class TestWraith:
    def test_wraith_phases_through_walls(self):
        game = make_game(
            [
                "#............#",
                "#.W..#.......#",
                "#....#.......#",
                "#....#..@....#",
                "#>...#.*..E..#",
                "#............#",
                "#............#",
            ],
            seed=1,
        )
        (wr,) = game.daemons
        assert wr["kind"] == "wraith"
        # Aim at the player across the wall column at x=5.
        wr["dir"] = (1, 0)
        crossed = False
        for _ in range(15):
            step_daemons(game)
            if wr["pos"][0] > 5:
                crossed = True
                break
        assert crossed, f"wraith could not phase through the wall: {wr['pos']}"

    def test_wraith_chases_when_close(self):
        game = make_game(
            [
                "#............#",
                "#.W..........#",
                "#............#",
                "#......@...E.#",
                "#>....*......#",
                "#............#",
                "#............#",
            ],
            seed=1,
        )
        (wr,) = game.daemons
        start = wr["pos"]
        for _ in range(6):
            step_daemons(game)
        d = abs(wr["pos"][0] - game.player[0]) + abs(wr["pos"][1] - game.player[1])
        assert d < abs(start[0] - game.player[0]) + abs(start[1] - game.player[1]), (
            "wraith did not close distance"
        )

    def test_wraith_is_slow_every_third_tick(self):
        game = make_game(
            [
                "#............#",
                "#.W..........#",
                "#............#",
                "#............#",
                "#..........@.#",
                "#>....*..E...#",
                "#............#",
            ],
            seed=1,
        )
        (wr,) = game.daemons
        cur = wr["pos"]
        moves = 0
        for _ in range(6):
            step_daemons(game)
            if wr["pos"] != cur:
                moves += 1
                cur = wr["pos"]
        assert moves == 2, f"wraith moved {moves} times in 6 ticks (want 2)"


class TestLancer:
    def test_lancer_charges_down_its_lane(self):
        game = make_game(
            [
                "#............#",
                "#.R.....@....#",
                "#............#",
                "#............#",
                "#>....*..E...#",
                "#............#",
                "#............#",
            ],
            seed=1,
        )
        (ln,) = game.daemons
        assert ln["kind"] == "lancer"
        start = ln["pos"]  # (2, 2); player (8, 2) - same row, clear sight
        step_daemons(game)
        # Dash is 2 cells per tick toward the player.
        assert ln["pos"] == (start[0] + 2, start[1])

    def test_lancer_dash_stops_on_contact_and_strikes(self):
        game = make_game(
            [
                "#............#",
                "#.R.@........#",
                "#............#",
                "#............#",
                "#>....*..E...#",
                "#............#",
                "#............#",
            ],
            seed=1,
        )
        (ln,) = game.daemons
        bw = game.bandwidth
        # Player at (4,2) steps left to (3,2); the lancer's dash lands on it.
        game.do_move(-1, 0)
        assert game.strikes == 1
        assert game.bandwidth == bw - 1 - ICE_STRIKE_COST
        assert ln["stun"] == DAEMON_STUN_TICKS
        assert game.player == (3, 2)  # the probe keeps its position

    def test_lancer_slow_off_lane(self):
        game = make_game(
            [
                "#............#",
                "#.R..........#",
                "#....#.......#",
                "#....#...@...#",  # wall column blocks the row sight? no: rows differ
                "#>...#.*..E..#",
                "#............#",
                "#............#",
            ],
            seed=1,
        )
        (ln,) = game.daemons
        start = ln["pos"]
        # Break line of sight: player is 2 rows down; lancer's row has no
        # player, column x=2 has no player. It should patrol slowly.
        moved = 0
        for _ in range(6):
            step_daemons(game)
        moved = abs(ln["pos"][0] - start[0]) + abs(ln["pos"][1] - start[1])
        assert moved <= 3, f"lancer moved {moved} cells in 6 ticks off-lane"


class TestVolt:
    def test_volt_never_moves_and_pulses_field(self):
        game = make_game(
            [
                "#............#",
                "#............#",
                "#....V.......#",
                "#............#",
                "#.....@......#",
                "#>....*..E...#",
                "#............#",
            ],
            seed=1,
        )
        (v,) = game.daemons
        assert v["kind"] == "volt"
        start = v["pos"]
        for _ in range(6):
            step_daemons(game)
        assert v["pos"] == start, "static ward moved"
        # Player at (6,5) is not adjacent: no strikes.
        assert game.strikes == 0
        # The field telegraph flashed during pulses.
        assert game.flash, "volt pulse left no field glint"

    def test_volt_zaps_probe_in_field(self):
        game = make_game(
            [
                "#............#",
                "#............#",
                "#....V.......#",
                "#............#",
                "#....@.......#",
                "#>....*..E...#",
                "#............#",
            ],
            seed=1,
        )
        (v,) = game.daemons
        bw = game.bandwidth
        # Player at (5,5) steps up to (5,4) - inside the field. The first
        # tick pulses: caught.
        game.do_move(0, -1)
        assert game.strikes == 1
        assert game.bandwidth == bw - 1 - ICE_STRIKE_COST
        assert v["stun"] == DAEMON_STUN_TICKS
        assert v["pos"] == (5, 3)  # static wards are never knocked back

    def test_volt_field_grounded_by_walls(self):
        game = make_game(
            [
                "#............#",
                "#............#",
                "#...#V.......#",
                "#............#",
                "#..#.@.......#",
                "#>....*..E...#",
                "#............#",
            ],
            seed=1,
        )
        (v,) = game.daemons
        from qgrid.enemies import _volt_field

        field = _volt_field(game.layout, v, set())
        assert (3, 4) not in field  # wall at (3,3) grounds the pulse
        assert (5, 2) in field and (6, 3) in field


class TestThreatNear:
    def test_threat_near_detects_daemons(self):
        game = make_game(
            [
                "#............#",
                "#.....H......#",
                "#............#",
                "#....@.......#",
                "#>....*..E...#",
                "#............#",
                "#............#",
            ],
            seed=1,
        )
        from qgrid.enemies import threat_near

        assert threat_near(game)  # hunter within 6
        game.daemons[0]["pos"] = (11, 1)
        assert not threat_near(game)  # hunter far away

    def test_threat_near_volt_adjacent(self):
        game = make_game(
            [
                "#............#",
                "#............#",
                "#....V.......#",
                "#....@.......#",
                "#............#",
                "#>....*..E...#",
                "#............#",
            ],
            seed=1,
        )
        from qgrid.enemies import threat_near

        assert threat_near(game)  # volt adjacent to the probe
        game.player = (9, 6)
        assert not threat_near(game)
