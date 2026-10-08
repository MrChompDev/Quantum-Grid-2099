#!/usr/bin/env python3
"""Full-campaign playthrough: connects over SSH and beats all 16 nodes using
BFS-computed optimal solutions, then verifies the victory screen.

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

ANSI_RE = re.compile(r"\x1b\[[0-9;?]*[a-zA-Z]|\x1b[=>]")
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

    async def read_until(self, *needles: str, timeout: float = 10.0) -> str:
        start_len = len(self.buf)

        async def _pump():
            while True:
                delta = strip_ansi(self.buf[start_len:])
                if any(n in delta for n in needles):
                    return
                chunk = await asyncio.wait_for(self.stdout.read(8192), timeout)
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

        async with asyncssh.connect(
            HOST, PORT, known_hosts=None, username="runner"
        ) as conn:
            stdin, stdout, _ = await conn.open_session(
                term_type="xterm", term_size=(80, 24)
            )
            c = Client(stdin, stdout)

            await c.read_until("JACK IN")
            c.send(" ")
            await c.read_until("MAINFRAME NODE ACCESS")
            print("connected; starting campaign...", flush=True)

            for i, defn in enumerate(LEVELS):
                c.send("\r")  # ENTER -> next available node (select screen)
                await c.read_until("PRESS ANY KEY TO ENGAGE")
                c.send(" ")
                await c.read_until("STATUS:")
                keys = solve_keys(defn)
                c.send("".join(keys))
                if i == len(LEVELS) - 1:
                    # final node goes straight to the victory screen
                    await c.read_until("MAINFRAME COMPROMISED")
                    print(
                        f"NODE 0{i + 1} - {defn.name}: cleared ({len(keys)} actions)",
                        flush=True,
                    )
                    print("VICTORY SCREEN verified", flush=True)
                else:
                    await c.read_until("ACCESS GRANTED")
                    print(
                        f"NODE 0{i + 1} - {defn.name}: cleared ({len(keys)} actions)",
                        flush=True,
                    )
                    c.send(" ")  # dismiss complete screen -> node select
                    await c.read_until("MAINFRAME NODE ACCESS")

            c.send("q")
            await c.read_until("CONNECTION TERMINATED", timeout=5)
            print("clean disconnect verified", flush=True)

        print("\nFULL CAMPAIGN PLAYTHROUGH PASSED")
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
