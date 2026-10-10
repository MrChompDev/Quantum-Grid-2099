#!/usr/bin/env python3
"""End-to-end smoke test: boots a real asyncssh server, connects as a client,
and plays through NODE 01 (FIRST LIGHT) over the wire — including the new
sector-select and node-select menus.

Run:  python3 scripts/smoke_test.py
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


def level_keys(index: int) -> str:
    """BFS-optimal key sequence for a node from the shared level data."""
    defn = LEVELS[index]
    path = solve_level(parse_level(defn.rows, defn.name))
    assert path is not None, f"{defn.name} unsolvable"
    return "".join(
        KEY_FOR_DIR[(dx, dy)] if act == "m" else "r" for act, dx, dy in path
    )


class Client:
    def __init__(self, stdin, stdout):
        self.stdin = stdin
        self.stdout = stdout
        self.buf = ""

    async def read_until(self, *needles: str, timeout: float = 6.0) -> str:
        """Read until a needle appears in NEW output; returns stripped delta."""
        start_len = len(self.buf)

        async def _pump():
            while True:
                delta = strip_ansi(self.buf[start_len:])
                if any(n in delta for n in needles):
                    return
                chunk = await asyncio.wait_for(self.stdout.read(4096), timeout)
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
        env={**os.environ, "QG_SAVE_DIR": "/tmp/opencode/qgrid_smoke_saves"},
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

        username = f"smoke{int(time.time())}"
        async with asyncssh.connect(
            HOST, PORT, known_hosts=None, username=username
        ) as conn:
            stdin, stdout, _ = await conn.open_session(
                term_type="xterm", term_size=(80, 24)
            )
            c = Client(stdin, stdout)

            await c.read_until("JACK IN")
            c.send(" ")
            await c.read_until("SECTOR ACCESS")
            print("connected; menus verified", flush=True)

            c.send("c")  # open the codex
            await c.read_until("CODEX")
            print("codex screen verified", flush=True)
            c.send("q")

            c.send("\r")  # ENTER on sector select -> node select (sector 1)
            await c.read_until("Press 1-8")
            c.send("\r")  # ENTER -> first uncleared node (NODE 01)
            await c.read_until("PRESS ANY KEY TO ENGAGE")
            c.send(" ")
            await c.read_until("STATUS:")
            c.send(level_keys(0))
            await c.read_until("ACCESS GRANTED")
            print("NODE 01 - FIRST LIGHT: cleared via SSH", flush=True)

            c.send(" ")  # dismiss complete -> node select
            await c.read_until("Press 1-8")
            c.send("q")  # q disconnects from anywhere
            await c.read_until("CONNECTION TERMINATED", timeout=5)
            print("clean disconnect verified", flush=True)

        print("\nSMOKE TEST PASSED")
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
        print(f"\nSMOKE TEST FAILED: {exc}")
        sys.exit(1)
