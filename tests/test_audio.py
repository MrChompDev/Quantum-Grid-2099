"""Unit tests for the 8-bit chiptune engine."""

import math

from qgrid import audio


def test_a4_is_440():
    assert audio.note_freq("A4") == 440.0


def test_c5_is_a_perfect_octave_plus_major_third_above_a4():
    f = audio.note_freq("C5")
    assert math.isclose(f, 440.0 * 2 ** (3 / 12), rel_tol=1e-9)


def test_octave_doubling():
    assert math.isclose(audio.note_freq("A5"), 880.0, rel_tol=1e-9)
    assert math.isclose(audio.note_freq("A3"), 220.0, rel_tol=1e-9)


def test_sharps_and_flats():
    assert math.isclose(audio.note_freq("A#4"), audio.note_freq("BB4"), rel_tol=1e-9)
    assert audio.note_freq("C4") < audio.note_freq("C#4") < audio.note_freq("D4")


def test_bad_notes_raise():
    import pytest

    with pytest.raises(ValueError):
        audio.note_freq("H4")
    with pytest.raises(ValueError):
        audio.note_freq("4")


def test_parse_track_rests_and_holds():
    track = audio.parse_track(["A4", ".", "C5*3"])
    assert track == [(440.0, 1), (None, 1), (audio.note_freq("C5"), 3)]


def test_all_songs_are_valid_and_nonempty():
    for name, track in audio.SONGS.items():
        assert track, f"song {name} is empty"
        total_steps = sum(s for _, s in track)
        assert total_steps >= 16, f"song {name} too short"
        notes = [f for f, _ in track if f is not None]
        assert notes, f"song {name} has no notes"
        for f in notes:
            assert audio.MIN_FREQ <= f <= audio.MAX_FREQ


def test_all_sfx_are_valid():
    for name, track in audio.SFX.items():
        assert track, f"sfx {name} is empty"
        for freq, steps in track:
            assert steps >= 1
            if freq is not None:
                assert audio.MIN_FREQ <= freq <= audio.MAX_FREQ


def test_tone_emits_pitch_escape_on_change_only():
    out = []

    def write(s):
        out.append(s)

    tone = audio.Tone(write)
    f = audio.note_freq("A4")
    tone.tone(f, 90)
    tone.tone(f, 90)  # same pitch: no new escape, just the bell
    g = audio.note_freq("C5")
    tone.tone(g, 90)
    text = "".join(out)
    assert text.count("\a") == 3
    assert text.count(f"\x1b[10;{int(f)}]") == 1
    assert text.count(f"\x1b[10;{int(g)}]") == 1


def test_tone_clamps_frequency():
    out = []
    tone = audio.Tone(out.append)
    tone.tone(99999, 10)
    tone.tone(1, 10)
    text = "".join(out)
    assert f"\x1b[10;{int(audio.MAX_FREQ)}]" in text
    assert f"\x1b[10;{int(audio.MIN_FREQ)}]" in text


def test_mode_cycle_order():
    player = audio.MusicPlayer(audio.Tone(lambda s: None))
    seq = [player.mode]
    for _ in range(4):
        seq.append(player.cycle_mode())
    assert seq == ["full", "music", "sfx", "off", "full"]


def test_mode_gating():
    player = audio.MusicPlayer(audio.Tone(lambda s: None))
    assert player.music_on and player.sfx_on  # full
    player.cycle_mode()  # music
    assert player.music_on and not player.sfx_on
    player.cycle_mode()  # sfx
    assert not player.music_on and player.sfx_on
    player.cycle_mode()  # off
    assert not player.music_on and not player.sfx_on


def test_set_song_restarts_index():
    player = audio.MusicPlayer(audio.Tone(lambda s: None))
    player._index = 7
    player.set_song("danger")
    assert player._index == 0
    player.set_song("danger")  # same song: no restart
    assert player.song == "danger"


def test_default_mode_env(monkeypatch):
    monkeypatch.setenv("QG_AUDIO", "sfx")
    assert audio.default_mode() == "sfx"
    monkeypatch.setenv("QG_AUDIO", "nonsense")
    assert audio.default_mode() == "full"
