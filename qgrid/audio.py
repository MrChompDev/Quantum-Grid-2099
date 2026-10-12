"""8-bit chiptune engine for Quantum Grid 2099.

Plays square-wave tones through the terminal bell: the pitch/duration
escape sequences (CSI 10;Hz / CSI 11;ms) followed by BEL. Terminals with
PC-speaker support (Linux console, some xterm builds) play real melodies;
everything else renders the bell rhythm - an honest retro compromise for
a game that ships over a text channel.

Every tone is ALSO wrapped in an invisible DCS marker:

    ESC P | qg | <freq> | <ms> ESC \\

The companion client (python3 -m qgrid.audio_client) runs on the player's
own machine, strips these markers before they reach the terminal, and
synthesizes the tones locally as real 8-bit audio. Set QG_BELL=off on the
server to mute the bell when using the companion (avoids double-beeps on
terminals with an audible bell).
"""

import asyncio
import os
import time

NOTE_SEMITONES = {
    "C": -9,
    "C#": -8,
    "DB": -8,
    "D": -7,
    "D#": -6,
    "EB": -6,
    "E": -5,
    "F": -4,
    "F#": -3,
    "GB": -3,
    "G": -2,
    "G#": -1,
    "AB": -1,
    "A": 0,
    "A#": 1,
    "BB": 1,
    "B": 2,
}

A4 = 440.0
MIN_FREQ = 30.0
MAX_FREQ = 8000.0

MODES = ("full", "music", "sfx", "off")

# Invisible per-tone marker for the companion audio client (a DCS sequence,
# ignored by terminals that do not understand it).
MARKER_FMT = "\x1bP|qg|{freq}|{ms}\x1b\\"
MARKER_RE = None  # compiled lazily by the companion client


def bell_enabled() -> bool:
    return os.environ.get("QG_BELL", "on").lower() not in ("off", "0", "no")


def note_freq(name: str) -> float:
    """'A4' -> 440.0, 'C5' -> ~523.25, 'F#3' -> ~185.0."""
    if len(name) < 2:
        raise ValueError(f"bad note {name!r}")
    pitch = name[:-1].upper()
    octave = int(name[-1])
    if pitch not in NOTE_SEMITONES:
        raise ValueError(f"bad pitch {name!r}")
    semis = NOTE_SEMITONES[pitch] + 12 * (octave - 4)
    return A4 * (2.0 ** (semis / 12.0))


def parse_track(tokens) -> list[tuple[float | None, int]]:
    """Parse ['A4', '.', 'C5*2', ...] into [(freq_or_None, steps), ...].

    '.' is a rest, 'X*n' holds note X for n steps.
    """
    track: list[tuple[float | None, int]] = []
    for tok in tokens:
        if tok == ".":
            track.append((None, 1))
            continue
        if "*" in tok:
            note, _, reps = tok.partition("*")
            track.append((note_freq(note), int(reps)))
        else:
            track.append((note_freq(tok), 1))
    return track


# ------------------------------------------------------------------- songs
# '.' rest, 'X*n' hold for n steps. One step = song tempo ms.

TITLE = parse_track(
    [
        "A4",
        ".",
        "E5",
        ".",
        "C5",
        ".",
        "A4",
        ".",
        "B4",
        "C5*1",
        "B4",
        "G4",
        "A4",
        ".",
        ".",
        ".",
        "F4",
        ".",
        "A4",
        ".",
        "C5",
        ".",
        "F5",
        ".",
        "E5",
        "D5",
        "C5",
        "D5",
        "E5",
        ".",
        ".",
        ".",
        "D4",
        ".",
        "F4",
        ".",
        "A4",
        ".",
        "D5",
        ".",
        "C5",
        "B4",
        "A4",
        "B4",
        "C5",
        ".",
        ".",
        ".",
        "E4",
        ".",
        "G4",
        ".",
        "B4",
        ".",
        "E5",
        ".",
        "D5",
        "C5",
        "B4",
        "C5",
        "A4",
        ".",
        ".",
        ".",
    ]
)

EXPLORE = parse_track(
    [
        "C4",
        ".",
        ".",
        ".",
        "E4",
        ".",
        "G4",
        ".",
        "A4",
        ".",
        ".",
        ".",
        "G4",
        ".",
        "E4",
        ".",
        "F4",
        ".",
        ".",
        ".",
        "A4",
        ".",
        "C5",
        ".",
        "B4",
        ".",
        "G4",
        ".",
        "E4",
        ".",
        ".",
        ".",
        "D4",
        ".",
        ".",
        ".",
        "F4",
        ".",
        "A4",
        ".",
        "G4",
        ".",
        ".",
        ".",
        "E4",
        ".",
        "C4",
        ".",
        "C4",
        ".",
        "D4",
        ".",
        "E4",
        ".",
        "G4",
        ".",
        "A4",
        ".",
        "G4",
        ".",
        "E4",
        ".",
        ".",
        ".",
    ]
)

DANGER = parse_track(
    [
        "A3",
        "A3",
        ".",
        "A3",
        "C4",
        ".",
        "A3",
        ".",
        "A3",
        "A3",
        ".",
        "A3",
        "D#4",
        ".",
        "D#4",
        ".",
        "A3",
        "A3",
        ".",
        "A3",
        "E4",
        ".",
        "D#4",
        ".",
        "C4",
        ".",
        "A3",
        ".",
        "G#3",
        ".",
        "A3",
        ".",
        "A3",
        "A3",
        ".",
        "A3",
        "C4",
        ".",
        "A3",
        ".",
        "F4",
        ".",
        "E4",
        ".",
        "D#4",
        ".",
        "D4",
        ".",
        "A3",
        "A3",
        ".",
        "A3",
        "E4",
        ".",
        "D#4",
        ".",
        "C4",
        ".",
        "B3",
        ".",
        "A3",
        ".",
        ".",
        ".",
    ]
)

SONGS = {"title": TITLE, "explore": EXPLORE, "danger": DANGER}
SONG_TEMPO = {"title": 140, "explore": 160, "danger": 110}

# --------------------------------------------------------------------- SFX
# (name -> track) played inline as one-shots at 90ms/step.

SFX_STEP_MS = 90
SFX: dict[str, list[tuple[float | None, int]]] = {
    "blip": parse_track(["C6"]),
    "rotate": parse_track(["E6"]),
    "menu": parse_track(["A5"]),
    "power": parse_track(["C5", "E5"]),
    "all_powered": parse_track(["C5", "E5", "G5"]),
    "shard": parse_track(["E5", "G5", "B5", "E6"]),
    "teleport": parse_track(["C4", "F4", "A4", "C5"]),
    "strike": parse_track(["C4", "C3*2"]),
    "emp": parse_track(["A5*2", "E5", "A4", "E4*2"]),
    "hint": parse_track(["G5", "C6"]),
    "unlock": parse_track(["C5", "C5", "G5", "C6*2"]),
    "engage": parse_track(["E5", "A5"]),
    "gameover": parse_track(["E4*2", "C4*2", "A3*2", "F3*3"]),
    "victory": parse_track(["C5", "E5", "G5", "C6", "E5", "G5", "C6*3"]),
}


def default_mode() -> str:
    mode = os.environ.get("QG_AUDIO", "full").lower()
    return mode if mode in MODES else "full"


class Tone:
    """Terminal tone writer: pitch escape + BEL, plus an invisible marker
    for the companion audio client; emits pitch escapes only on change."""

    def __init__(self, write):
        self.write = write
        self._freq: float | None = None
        self.bell = bell_enabled()

    def tone(self, freq: float, dur_ms: int) -> None:
        freq = max(MIN_FREQ, min(MAX_FREQ, freq))
        self.write(MARKER_FMT.format(freq=int(freq), ms=max(20, int(dur_ms))))
        if freq != self._freq:
            self.write(f"\x1b[10;{int(freq)}]\x1b[11;{max(20, int(dur_ms))}]")
            self._freq = freq
        if self.bell:
            self.write("\a")

    def play(self, track: list[tuple[float | None, int]], step_ms: int) -> None:
        """Play a one-shot track synchronously (caller blocks via sleep)."""
        for freq, steps in track:
            if freq is not None:
                self.tone(freq, steps * step_ms)
            time.sleep(steps * step_ms / 1000.0)


class MusicPlayer:
    """Asyncio task: loops the current song through the Tone channel."""

    def __init__(self, tone: Tone):
        self.tone = tone
        self.song: str | None = "title"
        self.mode = default_mode()
        self._index = 0
        self._task: asyncio.Task | None = None

    def cycle_mode(self) -> str:
        idx = MODES.index(self.mode)
        self.mode = MODES[(idx + 1) % len(MODES)]
        return self.mode

    @property
    def music_on(self) -> bool:
        return self.mode in ("full", "music")

    @property
    def sfx_on(self) -> bool:
        return self.mode in ("full", "sfx")

    def set_song(self, song: str | None) -> None:
        if song != self.song:
            self.song = song
            self._index = 0

    def sfx(self, name: str) -> None:
        """Queue a one-shot: write its tones immediately (interleaves with
        the music loop - reads as a drum hit in the mix)."""
        if not self.sfx_on:
            return
        track = SFX.get(name)
        if not track:
            return
        loop = asyncio.get_running_loop()
        loop.call_soon(self._play_sfx, track)

    def _play_sfx(self, track) -> None:
        for freq, steps in track:
            if freq is not None:
                self.tone.tone(freq, steps * SFX_STEP_MS)

    async def run(self) -> None:
        while True:
            if not self.music_on or self.song is None or self.song not in SONGS:
                await asyncio.sleep(0.08)
                continue
            song = self.song
            track = SONGS[song]
            tempo = SONG_TEMPO[song]
            n = len(track)
            while self.music_on and self.song == song:
                freq, steps = track[self._index % n]
                self._index = (self._index + 1) % n
                hold = steps * tempo / 1000.0
                if freq is not None:
                    self.tone.tone(freq, steps * tempo)
                # Yield in small slices so song/mode switches stay snappy.
                slept = 0.0
                while slept < hold and self.music_on and self.song == song:
                    chunk = min(0.05, hold - slept)
                    await asyncio.sleep(chunk)
                    slept += chunk

    def start(self) -> None:
        if self._task is None:
            self._task = asyncio.get_running_loop().create_task(self.run())

    async def stop(self) -> None:
        if self._task is not None:
            self.song = None
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
