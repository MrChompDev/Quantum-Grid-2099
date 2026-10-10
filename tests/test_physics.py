"""Unit tests for the ray-tracing physics engine."""

from qgrid.levels import LEVELS, parse_level
from qgrid.physics import DIR_VEC, REFLECT, trace_beam

BORDER = "#" * 20


def mk(interior_rows):
    """Wrap 8 interior rows (20 cols each) with border walls."""
    assert len(interior_rows) == 8
    for row in interior_rows:
        assert len(row) == 20, f"bad row length {len(row)}: {row!r}"
    rows = list(interior_rows)
    if not any("E" in row for row in rows):
        rows[-1] = rows[-1][:18] + "E" + rows[-1][19]
    if not any("*" in row for row in rows):
        rows[0] = rows[0][:18] + "*" + rows[0][19]
    return (BORDER,) + tuple(rows) + (BORDER,)


def trace(interior_rows, mirrors=None, player=(1, 1)):
    layout = parse_level(mk(interior_rows), "test")
    return trace_beam(layout, player, mirrors or {})


class TestReflectionTable:
    """Spec section 3.2: exact mirror reflection rules."""

    def test_slash_right_goes_up(self):
        assert REFLECT["/"][(1, 0)] == (0, -1)

    def test_slash_left_goes_down(self):
        assert REFLECT["/"][(-1, 0)] == (0, 1)

    def test_slash_up_goes_right(self):
        assert REFLECT["/"][(0, -1)] == (1, 0)

    def test_slash_down_goes_left(self):
        assert REFLECT["/"][(0, 1)] == (-1, 0)

    def test_backslash_right_goes_down(self):
        assert REFLECT["\\"][(1, 0)] == (0, 1)

    def test_backslash_left_goes_up(self):
        assert REFLECT["\\"][(-1, 0)] == (0, -1)

    def test_backslash_up_goes_left(self):
        assert REFLECT["\\"][(0, -1)] == (-1, 0)

    def test_backslash_down_goes_right(self):
        assert REFLECT["\\"][(0, 1)] == (1, 0)

    def test_all_directions_covered(self):
        for glyph in ("/", "\\"):
            assert set(REFLECT[glyph]) == set(DIR_VEC.values())


class TestBeamPropagation:
    def test_straight_beam_marks_horizontal_cells(self):
        t = trace(
            [
                "#@.................#",
                "#..................#",
                "#>.................#",
                "#..................#",
                "#..................#",
                "#..................#",
                "#..................#",
                "#..................#",
            ]
        )
        for x in range(2, 19):
            assert (x, 3) in t.h, f"missing beam at ({x},3)"
        assert (1, 3) not in t.h  # emitter cell itself is not beam
        assert t.v == set()

    def test_beam_stops_at_wall(self):
        t = trace(
            [
                "#@.................#",
                "#..................#",
                "#>.....#...........#",
                "#..................#",
                "#..................#",
                "#..................#",
                "#..................#",
                "#..................#",
            ]
        )
        assert (6, 3) in t.h  # last floor cell before wall
        assert (7, 3) not in t.h  # wall cell
        assert (8, 3) not in t.h  # nothing behind wall

    def test_beam_stops_at_grid_edge(self):
        t = trace(
            [
                "#@.................#",
                "#..................#",
                "#>.................#",
                "#..................#",
                "#..................#",
                "#..................#",
                "#..................#",
                "#..................#",
            ]
        )
        assert (18, 3) in t.h  # runs to the border

    def test_backslash_reflects_right_to_down(self):
        t = trace(
            [
                "#@.................#",
                "#..................#",
                "#>....\\............#",
                "#..................#",
                "#..................#",
                "#..................#",
                "#..................#",
                "#..................#",
            ],
            mirrors={(6, 3): "\\"},
        )
        assert (5, 3) in t.h
        assert (6, 4) in t.v  # right -> down
        assert (7, 3) not in t.h  # no pass-through

    def test_slash_reflects_right_to_up(self):
        t = trace(
            [
                "#@.................#",
                "#..................#",
                "#..................#",
                "#>...../...........#",
                "#..................#",
                "#..................#",
                "#..................#",
                "#..................#",
            ],
            mirrors={(7, 4): "/"},
        )
        assert (6, 4) in t.h
        assert (7, 3) in t.v  # right -> up
        assert (8, 4) not in t.h

    def test_receptor_is_powered_and_beam_passes_through(self):
        t = trace(
            [
                "#@.................#",
                "#..................#",
                "#>....*............#",
                "#..................#",
                "#..................#",
                "#..................#",
                "#..................#",
                "#..................#",
            ]
        )
        assert (6, 3) in t.powered
        assert (7, 3) in t.h  # beam continues past receptor

    def test_player_absorbs_beam(self):
        t = trace(
            [
                "#@.................#",
                "#..................#",
                "#>.................#",
                "#..................#",
                "#..................#",
                "#..................#",
                "#..................#",
                "#..................#",
            ],
            player=(10, 3),
        )
        assert (10, 3) in t.h  # beam reaches probe
        assert (11, 3) not in t.h  # absorbed

    def test_emitter_down_marks_vertical_cells(self):
        t = trace(
            [
                "#@........v........#",
                "#..................#",
                "#..................#",
                "#..................#",
                "#..................#",
                "#..................#",
                "#..................#",
                "#..................#",
            ]
        )
        for y in range(2, 9):
            assert (10, y) in t.v
        assert (10, 1) not in t.v

    def test_crossing_beams_mark_both_axes(self):
        t = trace(
            [
                "#@........v........#",
                "#..................#",
                "#>.................#",
                "#..................#",
                "#..................#",
                "#..................#",
                "#..................#",
                "#..................#",
            ]
        )
        # horizontal beam on row 3 crosses vertical beam on column 10
        assert (10, 3) in t.h
        assert (10, 3) in t.v

    def test_mirror_chain_terminates(self):
        """Cycle-prone geometry must not hang the tracer (loop protection)."""
        t = trace(
            [
                "#@.................#",
                "#..................#",
                "#>....\\............#",
                "#..................#",
                "#...../\\...........#",
                "#...../............#",
                "#..................#",
                "#..................#",
            ],
            mirrors={(6, 3): "\\", (6, 5): "/", (7, 5): "\\", (6, 4): "/", (7, 4): "/"},
        )
        assert isinstance(t.h, set) and isinstance(t.v, set)


class TestLevelParsing:
    def test_all_levels_parse_and_have_entities(self):
        for i, defn in enumerate(LEVELS):
            layout = parse_level(defn.rows, defn.name)
            assert len(layout.emitters) >= 1
            assert len(layout.receptors) >= 1
            assert layout.player_start != layout.exit_pos
            w, h = layout.width, layout.height
            assert all(0 < x < w - 1 and 0 < y < h - 1 for x, y in layout.receptors)


class TestSplitterPrism:
    def test_splitter_forks_perpendicular(self):
        """Beam moving right into a prism forks up AND down, no pass-through."""
        t = trace(
            [
                "#@.................#",
                "#..................#",
                "#>....+............#",
                "#..................#",
                "#..................#",
                "#..................#",
                "#..................#",
                "#..................#",
            ]
        )
        assert (5, 3) in t.h  # approach
        assert (6, 2) in t.v  # fork up
        assert (6, 4) in t.v  # fork down
        assert (7, 3) not in t.h  # no pass-through

    def test_splitter_forks_vertical(self):
        """Beam moving down into a prism forks left AND right."""
        t = trace(
            [
                "#@........v........#",
                "#..................#",
                "#..................#",
                "#..................#",
                "#.........+........#",
                "#..................#",
                "#..................#",
                "#..................#",
            ]
        )
        assert (11, 5) in t.h  # fork right
        assert (9, 5) in t.h  # fork left
        assert (10, 6) not in t.v  # no pass-through

    def test_splitter_loop_terminates(self):
        """Two facing prisms create a beam loop: must terminate via loop guard."""
        t = trace(
            [
                "#@.................#",
                "#..................#",
                "#>....+............#",
                "#.....+............#",
                "#..................#",
                "#..................#",
                "#..................#",
                "#..................#",
            ]
        )
        assert isinstance(t.h, set) and isinstance(t.v, set)

    def test_splitter_powers_both_receptor_branches(self):
        t = trace(
            [
                "#@.................#",
                "#..................#",
                "#>....+............#",
                "#.....*............#",
                "#..................#",
                "#..................#",
                "#..................#",
                "#..................#",
            ]
        )
        assert (6, 4) in t.powered  # fork down hits the receptor
        assert (6, 1) in t.v  # fork up continues


class TestNewTileTransparency:
    def test_beam_passes_through_shard(self):
        t = trace(
            [
                "#@.................#",
                "#..................#",
                "#>....$............#",
                "#..................#",
                "#..................#",
                "#..................#",
                "#..................#",
                "#..................#",
            ]
        )
        assert (6, 3) in t.h
        assert (7, 3) in t.h

    def test_beam_passes_through_teleport_pads(self):
        t = trace(
            [
                "#@.................#",
                "#..................#",
                "#>...TU............#",
                "#..................#",
                "#..................#",
                "#..................#",
                "#..................#",
                "#..................#",
            ]
        )
        assert (4, 3) in t.h and (5, 3) in t.h and (6, 3) in t.h

    def test_beam_ignores_ice_spawn_markers(self):
        t = trace(
            [
                "#@.................#",
                "#..................#",
                "#>....S.H.C........#",
                "#..................#",
                "#..................#",
                "#..................#",
                "#..................#",
                "#..................#",
            ]
        )
        for x in (6, 8, 10):
            assert (x, 3) in t.h
