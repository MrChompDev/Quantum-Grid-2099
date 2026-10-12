#!/usr/bin/env python3
"""Full-campaign playthrough: connects over SSH and beats all 48 nodes across
the 6 sectors using BFS-computed optimal solutions, then verifies the victory
screen.

Run:  python3 scripts/full_playthrough.py
"""

import asyncio
import os
import re
import select
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncssh

from qgrid.game import DIR_VECTORS
from qgrid.levels import LEVELS, parse_level
from qgrid.solver import solve_level

PORT = 2299
HOST = "127.0.0.1"
KEY = "/tmp/opencode/qgrid_smoke_key"

ANSI_RE = re.compile(
    r"\x1b\[[0-9;?]*[a-zA-Z]|\x1b[=>]|\x1bP.*?\x1b\\"  # CSI + DCS tone markers"
)
KEY_FOR_DIR = {v: k for k, v in DIR_VECTORS.items()}


def strip_ansi(s: str) -> str:
    return ANSI_RE.sub("", s)


def solve_keys(defn) -> list[str]:
    """BFS-optimal SSH key sequence for a level definition."""
    path = solve_level(parse_level(defn.rows, defn.name))
    assert path is not None, f"{defn.name} unsolvable"
    return [KEY_FOR_DIR[(dx, dy)] if act == "m" else "r" for act, dx, dy in path]


class Client:
    def __init__(self, stdin, stdout):
        self.stdin = stdin
        self.stdout = stdout
        self.buf = ""

    async def read_until(self, *needles: str, timeout: float = 25.0) -> str:
        start_len = len(self.buf)
        loop = asyncio.get_event_loop()
        deadline = loop.time() + timeout

        async def _pump():
            # absolute deadline: the game streams animated frames (typewriter
            # cutscenes, fx loop), so per-read timeouts never fire
            while loop.time() < deadline:
                delta = strip_ansi(self.buf[start_len:])
                if any(n in delta for n in needles):
                    return
                chunk = await asyncio.wait_for(
                    self.stdout.read(8192), max(0.05, deadline - loop.time())
                )
                if not chunk:
                    return
                self.buf += chunk

        try:
            await _pump()
        except asyncio.TimeoutError:
            pass
        delta = strip_ansi(self.buf[start_len:])
        for n in needles:
            if n in delta:
                return delta
        raise AssertionError(
            f"timeout waiting for {needles}; last output:\n{delta[-1500:]}"
        )

    def send(self, keys: str) -> None:
        self.stdin.write(keys)


async def main() -> int:
    proc = subprocess.Popen(
        [
            sys.executable,
            "-u",
            "main.py",
            "--host",
            HOST,
            "--port",
            str(PORT),
            "--host-key",
            KEY,
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        # QG_NO_ICE: this script replays BFS-optimal key sequences blindly,
        # which live ICE would disrupt (by design - the daemons punish
        # rote play). Laser-puzzle verification over the wire happens with
        # daemons disabled; real ICE playthroughs are covered by
        # tests/test_ice_playability.py (adaptive bot).
        env={
            **os.environ,
            "QG_SAVE_DIR": "/tmp/opencode/qgrid_play_saves",
            "QG_NO_ICE": "1",
        },
    )
    try:
        deadline = time.time() + 10
        started = False
        while time.time() < deadline:
            ready, _, _ = select.select([proc.stdout], [], [], 0.5)
            if ready and "online on" in proc.stdout.readline():
                started = True
                break
        if not started:
            raise AssertionError("server did not start")

        username = f"bot{int(time.time())}"
        async with asyncssh.connect(
            HOST, PORT, known_hosts=None, username=username
        ) as conn:
            stdin, stdout, _ = await conn.open_session(
                term_type="xterm", term_size=(80, 24)
            )
            c = Client(stdin, stdout)

            await c.read_until("JACK IN")
            c.send(" ")
            await c.read_until("PROLOGUE")
            c.send("x")  # skip the opening cutscene
            await c.read_until("SECTOR ACCESS")
            c.send("\r")  # sector select -> node select (sector 1)
            await c.read_until("1-8 NODE")
            print("connected; starting full campaign...", flush=True)

            for i, defn in enumerate(LEVELS):
                c.send("\r")  # node select -> level intro
                await c.read_until("PRESS ANY KEY TO ENGAGE")
                c.send(" ")
                await c.read_until("STATUS:")
                keys = solve_keys(defn)
                c.send("".join(keys))
                if i == len(LEVELS) - 1:
                    # final node: ending cutscene, then the victory screen
                    await c.read_until("EPILOGUE")
                    c.send("x")  # skip the ending cutscene
                    await c.read_until("MAINFRAME COMPROMISED")
                    print(
                        f"NODE {i + 1:02d} - {defn.name}: cleared ({len(keys)} actions)",
                        flush=True,
                    )
                    print("VICTORY SCREEN verified", flush=True)
                else:
                    await c.read_until("ACCESS GRANTED")
                    print(
                        f"NODE {i + 1:02d} - {defn.name}: cleared ({len(keys)} actions)",
                        flush=True,
                    )
                    c.send(" ")  # dismiss complete screen
                    if (i + 1) % 8 == 0:
                        # sector boundary: cutscene + stats intermission
                        await c.read_until("SECTOR CLEARED")
                        c.send("x")  # skip the cutscene pages
                        await c.read_until("PRESS ANY KEY TO DESCEND")
                        c.send(" ")
                        await c.read_until("SECTOR ACCESS")
                        c.send("\r")  # jump into the next sector
                    await c.read_until("1-8 NODE")

            c.send(" ")  # dismiss the victory screen -> session ends
            await c.read_until("CONNECTION TERMINATED", timeout=5)
            print("clean disconnect verified", flush=True)

        print("\nFULL CAMPAIGN PLAYTHROUGH PASSED (48/48 nodes)")
        return 0
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()


if __name__ == "__main__":
    try:
        sys.exit(asyncio.run(main()))
    except AssertionError as exc:
        print(f"\nPLAYTHROUGH FAILED: {exc}")
        sys.exit(1)
