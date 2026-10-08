#!/usr/bin/env python3
"""End-to-end smoke test: boots a real asyncssh server, connects as a client,
and plays through Node 01 (FIRST LIGHT) over the wire.

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

from qgrid.level_data import LEVEL_DATA
from qgrid.levels import parse_level
from qgrid.solver import solve_level

PORT = 2299
HOST = "127.0.0.1"
KEY = "/tmp/opencode/qgrid_smoke_key"

ANSI_RE = re.compile(r"\x1b\[[0-9;?]*[a-zA-Z]|\x1b[=>]")
KEY_FOR_DIR = {"w": "w", "a": "a", "s": "s", "d": "d"}


def strip_ansi(s: str) -> str:
    return ANSI_RE.sub("", s)


def level1_keys() -> str:
    """BFS-optimal key sequence for Node 01 from the shared level data."""
    path = solve_level(parse_level(LEVEL_DATA[0]["rows"], "l1"))
    return "".join(KEY_FOR_DIR[(dx, dy)] if act == "m" else "r" for act, dx, dy in path)


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
            f"timeout ({timeout}s) waiting for {needles}; last output:\n{delta[-2000:]}"
        )

    def send(self, keys: str) -> None:
        self.stdin.write(keys)


async def main() -> int:
    subprocess.run(["mkdir", "-p", "/tmp/opencode"], check=True)
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
        # wait for the server to come online
        deadline = time.time() + 10
        started = False
        while time.time() < deadline:
            ready, _, _ = select.select([proc.stdout], [], [], 0.5)
            if ready:
                line = proc.stdout.readline()
                if "online on" in line:
                    started = True
                    break
        if not started:
            raise AssertionError("server did not start")

        async with asyncssh.connect(
            HOST, PORT, known_hosts=None, username="judge"
        ) as conn:
            stdin, stdout, _ = await conn.open_session(
                term_type="xterm", term_size=(80, 24)
            )
            c = Client(stdin, stdout)

            # -- title screen
            await c.read_until("JACK IN")
            print("PASS title screen")

            # -- level select
            c.send(" ")
            out = await c.read_until("MAINFRAME NODE ACCESS")
            assert "NODE 01" in out
            assert "[LOCKED]" in out  # node 2+ still locked
            print("PASS level select (locked nodes shown)")

            # -- level 1 intro
            c.send("1")
            await c.read_until("FIRST LIGHT", "ENGAGE OPTICAL PROBE")
            print("PASS level intro")

            # -- gameplay
            c.send(" ")
            out = await c.read_until("NODE 01")
            assert "STATUS:" in out
            print("PASS gameplay frame")

            # -- rotate the mirror -> all receptors online, then walk to E
            keys = level1_keys()
            r_idx = keys.index("r")
            c.send(keys[: r_idx + 1])
            out = await c.read_until("ALL RECEPTORS ONLINE", "UNLOCKED")
            assert "RECEPTORS: 1/1" in out
            print("PASS solver keys -> receptor powered, exit unlocked")

            c.send(keys[r_idx + 1 :])
            await c.read_until("ACCESS GRANTED")
            print("PASS extraction -> level complete screen")

            # -- back to node select, node 02 unlocked now
            c.send(" ")
            out = await c.read_until("MAINFRAME NODE ACCESS")
            assert "[2] NODE 02 - COLD BOOT" in out
            assert "[LOCKED]" in out  # node 03+ still locked
            print("PASS progression unlock (node 02 available)")

        # -- concurrent session check
        async def second_player():
            async with asyncssh.connect(
                HOST, PORT, known_hosts=None, username="judge2"
            ) as conn2:
                s2_in, s2_out, _ = await conn2.open_session(
                    term_type="xterm", term_size=(80, 24)
                )
                c2 = Client(s2_in, s2_out)
                await c2.read_until("JACK IN")
                c2.send(" ")
                await c2.read_until("SELECT NODE")
                c2.send("1")
                await c2.read_until("FIRST LIGHT")
                return "second-ok"

        result = await asyncio.wait_for(second_player(), timeout=10)
        assert result == "second-ok"
        print("PASS concurrent independent session")

        print("\nALL SMOKE TESTS PASSED")
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
