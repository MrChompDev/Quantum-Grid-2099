"""Tests for the companion audio client: marker parsing, WAV synthesis,
player selection, and the PTY bridge."""

import io
import subprocess
import sys
import time
import wave

import pytest

from qgrid import audio_client as ac


def test_parse_stream_extracts_tones():
    chunk = b"hello \x1bP|qg|440|90\x1b\\ world \x1bP|qg|880|45\x1b\\"
    clean, tones = ac.parse_stream(chunk)
    assert tones == [(440, 90), (880, 45)]
    assert clean == b"hello  world "


def test_parse_stream_leaves_other_escape_sequences_alone():
    chunk = b"\x1b[31mred\x1b[0m\x1bP|qg|440|90\x1b\\"
    clean, tones = ac.parse_stream(chunk)
    assert clean == b"\x1b[31mred\x1b[0m"
    assert tones == [(440, 90)]


def test_server_markers_round_trip_through_parser():
    from qgrid.audio import MARKER_FMT

    marker = MARKER_FMT.format(freq=523, ms=90).encode()
    clean, tones = ac.parse_stream(b"abc" + marker + b"def")
    assert tones == [(523, 90)]
    assert clean == b"abcdef"


def test_parse_stream_clamps_values():
    _clean, tones = ac.parse_stream(b"\x1bP|qg|99999|5\x1b\\")
    assert tones[0][0] == ac.MAX_FREQ
    assert tones[0][1] == 20


def test_square_wave_wav_is_mono_u8_square():
    rate = 8000
    data = ac.square_wave_wav(440, 100, rate=rate)
    buf = io.BytesIO(data)
    with wave.open(buf, "rb") as w:
        assert w.getnchannels() == 1
        assert w.getsampwidth() == 1
        assert w.getframerate() == rate
        frames = w.readframes(w.getnframes())
    assert len(frames) == pytest.approx(rate * 0.1, abs=rate // 50)
    # duty cycle: roughly half the samples above and half below the midpoint
    hi = sum(1 for b in frames if b > 128)
    assert 0.35 < hi / len(frames) < 0.65


def test_find_player_respects_env_override(monkeypatch):
    monkeypatch.setenv("QG_PLAYER_CMD", "true")
    assert ac.find_player() == ["true"]


def test_tone_player_drops_backlog(monkeypatch):
    monkeypatch.setenv("QG_PLAYER_CMD", "true")
    p = ac.TonePlayer()
    try:
        for _ in range(10):
            p.schedule(440, 20)
        time.sleep(0.5)
        assert p.q.qsize() <= 3
    finally:
        p.stop()


def test_tone_markers_embedded_by_engine():
    from qgrid.audio import Tone

    out = []
    tone = Tone(out.append)
    tone.tone(440, 90)
    text = "".join(out)
    assert "\x1bP|qg|440|90\x1b\\" in text
    _clean, tones = ac.parse_stream(text.encode())
    assert tones == [(440, 90)]


def test_bell_env_toggle(monkeypatch):
    from qgrid.audio import Tone

    monkeypatch.setenv("QG_BELL", "off")
    out = []
    Tone(out.append).tone(440, 90)
    assert "\a" not in "".join(out)
    monkeypatch.setenv("QG_BELL", "on")
    out = []
    Tone(out.append).tone(440, 90)
    assert "\a" in "".join(out)


def test_pty_bridge_forwards_output_and_strips_markers():
    """End-to-end: bridge a fake session that emits markers + reads stdin."""
    fake = (
        "import sys, time\n"
        "sys.stdout.write('GRID-ONLINE \\x1bP|qg|440|30\\x1b\\\\\\n')\n"
        "sys.stdout.flush()\n"
        "data = sys.stdin.buffer.read(1)\n"
        "sys.stdout.write('ECHO:' + repr(data) + '\\n')\n"
        "sys.stdout.flush()\n"
    )
    proc = subprocess.Popen(
        [
            sys.executable,
            "-u",
            "-m",
            "qgrid.audio_client",
            "--",
            sys.executable,
            "-u",
            "-c",
            fake,
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        stdin=subprocess.PIPE,
    )
    try:
        time.sleep(1.5)  # let the PTY session start and print
        # the fake session's pty is in canonical mode: send a full line
        proc.stdin.write(b"x\n")
        proc.stdin.flush()
        out, _err = proc.communicate(timeout=10)
        assert b"GRID-ONLINE" in out
        assert b"ECHO:b'x'" in out
        assert b"\x1bP|qg|440|30" not in out  # marker stripped before terminal
    finally:
        if proc.poll() is None:
            proc.kill()
            proc.wait(timeout=5)
