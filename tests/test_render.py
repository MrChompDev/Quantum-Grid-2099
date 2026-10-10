"""Rendering tests: 2x2 pixel-doubling, shimmer, flashes, shake, chrome."""

from qgrid import render as R
from qgrid.game import Game


def plain(text: str) -> str:
    return R._strip_ansi(text)


def test_scale1_frame_fits_80x24():
    game = Game(0, 100)
    out = R.render_frame(game, 80, 24)
    lines = out.count("\r\n") + 1
    assert lines == 24
    assert "WASD" in plain(out)
    assert "\u266a" in plain(out)  # equalizer strip


def test_scale2_doubles_small_grids_on_big_terminals():
    game = Game(0, 100)  # 26x11 grid
    assert R._grid_scale(game, 120, 40) == (3, 3)  # full tripling fits
    out = R.render_frame(game, 120, 40)
    assert "@@@" in plain(out)  # tripled player
    lines = out.count("\r\n") + 1
    assert lines == 40


def test_scale1_keeps_big_grids_on_small_terminals():
    game = Game(47, 100)  # 72x16 grid: doubled = 144 wide, too big for 80
    assert R._grid_scale(game, 80, 24) == (1, 1)
    assert R._grid_scale(game, 200, 50) == (2, 2)  # but scales on a huge terminal


def test_beam_shimmer_alternates():
    game = Game(0, 100)
    out0 = R.render_frame(game, 80, 24, frame=0)
    out1 = R.render_frame(game, 80, 24, frame=1)
    assert R.BEAM_GLYPHS_H[0] in plain(out0) or R.BEAM_GLYPHS_H[0] not in plain(out1)
    assert plain(out0) != plain(out1)  # the shimmer re-renders differently


def test_flash_burst_overrides_cells():
    game = Game(0, 100)
    out = R.render_frame(game, 80, 24)
    assert "\u2726" not in plain(out)
    # flash a receptor cell (player glyph keeps priority over flashes)
    target = game.layout.receptors[0]
    game.flash[target] = 3
    out = R.render_frame(game, 80, 24)
    assert "\u2726" in plain(out)


def test_shake_changes_indent_and_tints_rule():
    game = Game(0, 100)
    game.shake = 3
    out = R.render_frame(game, 80, 24, frame=1)
    # red rule tint on the first render after a strike
    assert f"{R.ESC}[{R.RED}m=" in out
    game.shake = 0
    out = R.render_frame(game, 80, 24, frame=1)
    assert f"{R.ESC}[{R.RED}m=" not in out


def test_decay_fx_ages_flashes_and_shake():
    game = Game(0, 100)
    game.flash[(5, 5)] = 1
    game.shake = 1
    game.decay_fx()
    assert (5, 5) not in game.flash
    assert game.shake == 0
    game.flash[(5, 5)] = 3
    game.decay_fx()
    assert game.flash[(5, 5)] == 2


def test_eq_strip_reflects_music_state():
    on = R._eq_strip(0, True)
    off = R._eq_strip(0, False)
    assert "\u266a" in plain(on)
    assert "\u266a" not in plain(off)


def test_title_animates():
    out0 = R.render_title(80, 24, 0)
    out1 = R.render_title(80, 24, 1, clear=False)
    assert plain(out0) != plain(out1)
    assert "JACK IN" in plain(out0)
    # the animated laser lane sweeps
    assert "\u25b6" in plain(out0)


def test_victory_screen_ranks_and_animates():
    from qgrid.save import default_save

    save = default_save()
    save["total_score"] = 260000
    save["shards"] = {"0": [0, 1]}
    out0 = R.render_victory(save, 96, 80, 24, frame=0)
    out2 = R.render_victory(save, 96, 80, 24, frame=2)
    assert "LEGEND OF THE GRID" in plain(out0)
    assert plain(out0) != plain(out2)


def test_sector_clear_intermission():
    from qgrid.lore import ZONES

    zone = ZONES[0]
    out0 = R.render_sector_clear(zone, 12345, 80, 24, frame=0)
    out2 = R.render_sector_clear(zone, 12345, 80, 24, frame=2)
    text = plain(out0)
    assert "SECTOR CLEARED" in text
    assert "SECTOR 01 - THE SPINE" in text
    assert "MIRAGE" in text  # the lore beat quotes her
    assert "12345" in text
    assert out0 != out2  # animated blink (bright vs dimmed color)


def test_cutscene_renders_speaker_and_reveal():
    from qgrid.lore import OPENING_CUTSCENE

    out = R.render_cutscene(OPENING_CUTSCENE, 0, 10, 80, 24, 0)
    text = plain(out)
    assert "PROLOGUE" in text
    assert "2099. SECT" in text  # partial typewriter reveal
    assert "Tonight the meter stops" not in text
    assert "MIRAGE" not in text  # speaker 0 is narration
    assert "..." in text  # still typing

    full = R.cutscene_page_len(OPENING_CUTSCENE, 0)
    out = R.render_cutscene(OPENING_CUTSCENE, 0, full, 80, 24, 0)
    text = plain(out)
    assert "Tonight the meter stops." in text
    assert "ENTER: MORE" in text  # page 0 of 5 -> more pages

    # dialogue page carries the speaker tag in its color
    out = R.render_cutscene(OPENING_CUTSCENE, 2, 999, 80, 24, 0)
    assert "\u00bb MIRAGE" in plain(out)


def test_cutscene_last_page_prompt():
    from qgrid.lore import OPENING_CUTSCENE

    last = len(OPENING_CUTSCENE["pages"]) - 1
    total = R.cutscene_page_len(OPENING_CUTSCENE, last)
    out = R.render_cutscene(OPENING_CUTSCENE, last, total, 80, 24, 0)
    assert "ENTER: CONTINUE" in plain(out)


def test_settings_screen_renders_and_marks_selection():
    from qgrid.lore import DEFAULT_SETTINGS

    s = dict(DEFAULT_SETTINGS)
    out = R.render_settings(s, 0, 80, 24)
    text = plain(out)
    for label in ("SOUND", "SCREEN SHAKE", "FLASH EFFECTS", "BEAM SHIMMER", "TEXT SPEED"):
        assert label in text
    assert ">" in text and "FULL" in text and "NORMAL" in text


def test_vfx_toggles_off():
    game = Game(0, 100)
    game.flash[game.layout.receptors[0]] = 3
    game.shake = 3
    out = R.render_frame(game, 80, 24, vfx={"shake": False, "flashes": False, "shimmer": False})
    text = plain(out)
    assert "\u2726" not in text  # flashes off
    assert f"{R.ESC}[{R.RED}m=" not in out  # no red alert rule
    # shimmer off: beam glyphs stay at variant 0 on any frame
    out1 = R.render_frame(game, 80, 24, frame=1, vfx={"shimmer": False})
    assert R.BEAM_GLYPHS_H[0] in plain(out1)


def test_per_axis_scale_tiers():
    game = Game(0, 100)  # 26x11
    assert R._grid_scale(game, 80, 24) == (2, 1)  # wide doubling on 80x24
    assert R._grid_scale(game, 120, 40) == (3, 3)  # full 3x3 on big terminals
    big = Game(47, 100)  # 72x16
    assert R._grid_scale(big, 80, 24) == (1, 1)
    assert R._grid_scale(big, 200, 50) == (2, 2)
