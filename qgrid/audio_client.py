"""Companion audio client for Quantum Grid 2099.

Runs ON THE PLAYER'S MACHINE next to ssh. It spawns the ssh session on a
PTY, forwards your keystrokes and the game's rendering untouched, but
intercepts the invisible tone markers the server embeds in the stream
(ESC P |qg|<freq>|<ms> ESC \\) and synthesizes them locally as real
8-bit square-wave audio - actual chiptune you can hear, independent of
terminal bell settings.

Usage:
    python3 -m qgrid.audio_client -- ssh -p 2222 <host>
    python3 -m qgrid.audio_client -- ssh -p 2222 -l myuser localhost

Env:
    QG_PLAYER_CMD  force a player command (testing / custom players)
    QG_SAMPLE_RATE wav sample rate (default 44100)

Unix only (requires a PTY); on Windows use WSL.
"""

import fcntl
import io
import os
import queue
import re
import select
import shutil
import signal
import struct
import subprocess
import sys
import tempfile
import termios
import threading
import tty
import wave

from .audio import MAX_FREQ, MIN_FREQ

MARKER_RE = re.compile(rb"\x1bP\|qg\|(\d+)\|(\d+)\x1b\\")
SAMPLE_RATE = int(os.environ.get("QG_SAMPLE_RATE", "44100"))
VOLUME = 0.55


def parse_stream(chunk: bytes) -> tuple[bytes, list[tuple[int, int]]]:
    """Strip tone markers from a stream chunk; return (clean, tones)."""
    tones = [
        (max(MIN_FREQ, min(MAX_FREQ, int(f))), max(20, int(ms)))
        for f, ms in MARKER_RE.findall(chunk)
    ]
    clean = MARKER_RE.sub(b"", chunk)
    return clean, tones


def square_wave_wav(freq: int, ms: int, rate: int = SAMPLE_RATE) -> bytes:
    """Synthesize an 8-bit mono square-wave WAV in memory (duty 50%)."""
    n = max(1, int(rate * ms / 1000))
    half_period = max(1.0, rate / freq / 2.0)
    amp = int(VOLUME * 127)
    fade = max(1, int(rate * 0.004))  # 4ms fade to kill clicks
    samples = bytearray(n)
    for i in range(n):
        hi = int(i / half_period) % 2 == 0
        samples[i] = 128 + amp if hi else 128 - amp
    for i in range(min(fade, n)):
        t = i / fade
        samples[i] = int(128 + (samples[i] - 128) * t)
        samples[n - 1 - i] = int(128 + (samples[n - 1 - i] - 128) * t)
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(1)
        w.setframerate(rate)
        w.writeframes(bytes(samples))
    return buf.getvalue()


def find_player() -> list[str] | None:
    """Pick a local player command; None means no audio path available."""
    forced = os.environ.get("QG_PLAYER_CMD", "")
    if forced:
        return forced.split()
    if os.name == "nt":
        return ["powershell", "-NoProfile", "-Command"]  # [console]::beep
    if sys.platform == "darwin":
        if shutil.which("afplay"):
            return ["afplay"]
        return None
    for name, args in (
        ("paplay", []),
        ("pw-play", []),
        ("ffplay", ["-nodisp", "-autoexit", "-loglevel", "quiet"]),
        ("mpv", ["--really-quiet", "--no-video"]),
        ("aplay", ["-q"]),
    ):
        if shutil.which(name):
            return [name, *args]
    return None


class TonePlayer:
    """Worker thread: plays queued (freq, ms) tones via the local player."""

    def __init__(self):
        self.q: queue.Queue = queue.Queue(maxsize=3)
        self.player = find_player()
        self._tmp = tempfile.mkdtemp(prefix="qgrid-audio-")
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def schedule(self, freq: int, ms: int) -> None:
        if self.player is None:
            return
        try:
            self.q.put_nowait((int(freq), int(ms)))
        except queue.Full:
            try:
                self.q.get_nowait()  # drop the oldest, keep the newest
                self.q.put_nowait((int(freq), int(ms)))
            except (queue.Full, queue.Empty):
                pass

    def _wav_path(self, freq: int, ms: int) -> str:
        path = os.path.join(self._tmp, f"t{freq}_{ms}.wav")
        if not os.path.exists(path):
            with open(path, "wb") as fh:
                fh.write(square_wave_wav(freq, ms))
        return path

    def _loop(self) -> None:
        windows = os.name == "nt"
        while True:
            item = self.q.get()
            if item is None:
                break
            freq, ms = item
            try:
                if windows:
                    subprocess.run(
                        [
                            "powershell", "-NoProfile", "-Command",
                            f"[console]::beep({freq},{ms})",
                        ],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        check=False,
                    )
                else:
                    subprocess.run(
                        [*self.player, self._wav_path(freq, ms)],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        check=False,
                    )
            except OSError:
                continue

    def stop(self) -> None:
        self.q.put(None)
        shutil.rmtree(self._tmp, ignore_errors=True)


def _set_winsize(master: int) -> None:
    try:
        size = shutil.get_terminal_size()
        fcntl.ioctl(
            master, termios.TIOCSWINSZ, struct.pack("HHHH", size.lines, size.columns, 0, 0)
        )
    except (OSError, ValueError):
        pass


def run_bridge(cmd: list[str]) -> int:
    """Spawn `cmd` on a PTY and bridge it to the local terminal."""
    if not hasattr(os, "openpty"):
        print("qgrid.audio_client requires a Unix PTY (use WSL on Windows)")
        return 1

    player = TonePlayer()
    master, slave = os.openpty()
    _set_winsize(master)

    old_attrs = None
    stdin_fd = sys.stdin.fileno()
    try:
        old_attrs = termios.tcgetattr(stdin_fd)
        tty.setraw(stdin_fd)
    except termios.error:  # stdin is not a terminal (piped/redirected)
        old_attrs = None
    proc = subprocess.Popen(
        cmd,
        stdin=slave,
        stdout=slave,
        stderr=slave,
        close_fds=True,
    )
    os.close(slave)

    def on_winch(_sig, _frm):
        _set_winsize(master)

    try:
        signal.signal(signal.SIGWINCH, on_winch)
    except (ValueError, OSError):
        pass

    try:
        while proc.poll() is None:
            try:
                readable, _, _ = select.select([master, stdin_fd], [], [], 0.2)
            except InterruptedError:
                continue
            if master in readable:
                try:
                    data = os.read(master, 65536)
                except OSError:
                    break
                if not data:
                    break
                clean, tones = parse_stream(data)
                for freq, ms in tones:
                    player.schedule(freq, ms)
                if clean:
                    sys.stdout.buffer.write(clean)
                    sys.stdout.buffer.flush()
            if stdin_fd in readable:
                try:
                    data = os.read(stdin_fd, 4096)
                except OSError:
                    break
                if data:
                    os.write(master, data)
    finally:
        if old_attrs is not None:
            try:
                termios.tcsetattr(stdin_fd, termios.TCSADRAIN, old_attrs)
            except termios.error:
                pass
        player.stop()
        try:
            proc.wait(timeout=2)
        except subprocess.TimeoutExpired:
            proc.kill()
        os.close(master)
    return proc.returncode or 0


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if "--" in argv:
        cmd = argv[argv.index("--") + 1 :]
    else:
        cmd = ["ssh", "-p", "2222", "localhost"]
    if not cmd:
        print("usage: python3 -m qgrid.audio_client -- ssh -p 2222 <host>")
        return 2
    return run_bridge(cmd)


if __name__ == "__main__":
    sys.exit(main())
