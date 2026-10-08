"""SSH server core for Quantum Grid 2099.

Runs an asyncssh server on port 2222. Every incoming connection gets its
own independent asyncio session: title screen -> node select -> gameplay.
Keypresses are read non-blocking (1 byte at a time) from the SSH channel.
"""

import asyncio
import os

import asyncssh

from .game import DIR_VECTORS, Game, start_bandwidth
from .levels import LEVELS
from .render import (
    CLEAR,
    HIDE_CURSOR,
    MIN_H,
    MIN_W,
    SHOW_CURSOR,
    render_frame,
    render_game_over,
    render_goodbye,
    render_level_complete,
    render_level_intro,
    render_level_select,
    render_title,
    render_victory,
)

# Arrow-key escape sequences mapped onto WASD equivalents.
ARROW_MAP = {"A": "w", "B": "s", "C": "d", "D": "a"}

QUIT = None  # EOF, Ctrl-C or 'q'
NOOP = ""  # ignored input
_TIMEOUT = object()  # digit-buffer window expired (distinct from QUIT)


class QuantumGridServer(asyncssh.SSHServer):
    """SSH server that requires no authentication and runs the game."""

    def connection_made(self, conn: asyncssh.SSHServerConnection) -> None:
        self._conn = conn

    def begin_auth(self, username: str) -> bool:
        # No authentication required for this game.
        return False

    def session_requested(self):
        return handle_session


class Session:
    def __init__(self, stdin, stdout, peer: str):
        self.stdin = stdin
        self.stdout = stdout
        self.peer = peer
        self.bandwidth = 100
        self.unlocked = 0
        self.total_actions = 0
        self.unlock_all = os.environ.get("QG_UNLOCK_ALL", "") == "1"
        self.width, self.height = self._frame_size()

    def _frame_size(self) -> tuple[int, int]:
        """Terminal size, clamped to at least 80x24 (re-read per frame)."""
        try:
            size = self.stdout.channel.get_terminal_size()
            # (width, height, pixel_width, pixel_height)
            return max(MIN_W, size[0]), max(MIN_H, size[1])
        except Exception:  # noqa: BLE001 - fall back to the default
            return MIN_W, MIN_H

    def write(self, data: str) -> None:
        self.stdout.write(data)

    # ------------------------------------------------------------------ input

    async def read_key(self) -> str | None:
        """Read one keypress.

        Returns QUIT on EOF / Ctrl-C / 'q', or a normalized key character:
        one of 'w','a','s','d','r','k','\\r','\\n',' ' or a digit.
        """
        while True:
            try:
                data = await self.stdin.read(1)
            except (asyncssh.SignalReceived, asyncssh.BreakReceived) as exc:
                if getattr(exc, "signal", "") == "INT":
                    return QUIT
                continue
            if not data:
                return QUIT
            if isinstance(data, bytes):
                data = data.decode("utf-8", "replace")
            ch = data
            if ch == "\x1b":
                ch = await self._consume_escape()
                if ch == NOOP:
                    continue
            if ch in ("q", "Q"):
                return QUIT
            if ch in DIR_VECTORS:
                return ch
            if ch in ("r", "R", "k", "K"):
                return ch.lower()
            if ch.isdigit() or ch in ("\r", "\n", " "):
                return ch
            # Ignore anything else and wait for the next real keypress.
            continue

    async def _consume_escape(self) -> str:
        """Consume an ANSI escape sequence; map arrow keys to WASD."""
        try:
            nxt = await asyncio.wait_for(self.stdin.read(1), 0.05)
        except (asyncio.TimeoutError, TimeoutError):
            return NOOP
        if not nxt or nxt != "[":
            return NOOP
        try:
            final = await asyncio.wait_for(self.stdin.read(1), 0.05)
        except (asyncio.TimeoutError, TimeoutError):
            return NOOP
        return ARROW_MAP.get(final, NOOP)

    # ------------------------------------------------------------------- flow

    async def run(self) -> None:
        try:
            self.write(HIDE_CURSOR + CLEAR + render_title(self.width, self.height))
            if await self.read_key() is QUIT:
                return
            while True:
                index = await self._level_select()
                if index is None:
                    return
                result = await self._play_level(index)
                if result == "quit":
                    return
                if result == "gameover":
                    self.write(
                        CLEAR
                        + render_game_over(self._last_game, self.width, self.height)
                    )
                    await self.read_key()
                    return
                if result == "victory":
                    self.write(CLEAR + render_victory(self, self.width, self.height))
                    await self.read_key()
                    return
        finally:
            self.write(SHOW_CURSOR + render_goodbye(self.width, self.height))

    async def _level_select(self) -> int | None:
        while True:
            self.write(
                CLEAR
                + render_level_select(
                    self.unlocked, self.unlock_all, self.width, self.height
                )
            )
            key = await self.read_key()
            if key is QUIT:
                return None
            if key in ("\r", "\n", " "):
                return 0 if self.unlock_all else self.unlocked
            if key and key.isdigit():
                num = key
                # buffer a second digit for two-digit node numbers (10+)
                try:
                    nxt = await asyncio.wait_for(self.read_key(), 0.3)
                except (asyncio.TimeoutError, TimeoutError):
                    nxt = _TIMEOUT
                if nxt is QUIT:
                    return None
                if nxt is not _TIMEOUT and nxt and nxt.isdigit():
                    num += nxt
                idx = int(num) - 1
                if 0 <= idx < len(LEVELS) and (self.unlock_all or idx <= self.unlocked):
                    return idx

    async def _play_level(self, index: int) -> str:
        defn = LEVELS[index]
        bandwidth = start_bandwidth(defn, self.bandwidth)
        game = Game(index, bandwidth, self.unlocked)
        self._last_game = game
        self.width, self.height = self._frame_size()
        self.write(CLEAR + render_level_intro(defn, bandwidth, self.width, self.height))
        if await self.read_key() is QUIT:
            return "quit"
        self.write(render_frame(game, self.width, self.height))
        while True:
            key = await self.read_key()
            if key is QUIT:
                return "quit"
            if key == "k":
                game.restart()
                self.write(render_frame(game, self.width, self.height))
                continue
            if key in DIR_VECTORS:
                acted = game.do_move(*DIR_VECTORS[key]) == "ok"
            elif key == "r":
                acted = game.do_rotate()
            else:
                # Enter/space during gameplay: no-op, no re-render needed.
                continue
            if acted:
                self.total_actions += 1
            if game.check_win():
                self.bandwidth = game.finish_level()
                self.unlocked = max(self.unlocked, index + 1)
                if index == len(LEVELS) - 1:
                    return "victory"
                self.width, self.height = self._frame_size()
                self.write(
                    CLEAR
                    + render_level_complete(game, index + 1, self.width, self.height)
                )
                if await self.read_key() is QUIT:
                    return "quit"
                return "next"
            if game.game_over:
                return "gameover"
            self.width, self.height = self._frame_size()
            self.write(render_frame(game, self.width, self.height))


async def handle_session(stdin, stdout, stderr) -> None:
    peer = ""
    try:
        peer = str(stdout.channel.get_extra_info("peername") or "")
    except Exception:  # noqa: BLE001, S110 - peername is best-effort only
        pass
    session = Session(stdin, stdout, peer)
    print(f"[QGRID] session opened: {session.peer}")
    try:
        await session.run()
    except (asyncssh.DisconnectError, ConnectionError, OSError):
        pass
    except Exception as exc:  # noqa: BLE001 - keep the server alive no matter what
        print(f"[QGRID] session error: {exc!r}")
    finally:
        print(f"[QGRID] session closed: {session.peer}")


async def start_server(
    host: str = "0.0.0.0", port: int = 2222, host_key: str = "ssh_host_key"
):
    """Start the asyncssh server and wait forever."""
    if not os.path.exists(host_key):
        key = asyncssh.generate_private_key("ssh-ed25519")
        key.write_private_key(host_key)
        try:
            os.chmod(host_key, 0o600)
        except OSError:
            pass
        print(f"[QGRID] generated host key: {host_key}")
    server = await asyncssh.listen(
        host,
        port,
        server_factory=QuantumGridServer,
        server_host_keys=[host_key],
        login_timeout=60,
        # Raw-mode input: disable the server-side line editor and echo so
        # keystrokes reach the game immediately, one byte at a time.
        line_editor=False,
        line_echo=False,
    )
    print(f"[QGRID] Quantum Grid 2099 online on {host}:{port}")
    print(f"[QGRID] connect with: ssh -p {port} <user>@<host>")
    await server.wait_closed()
