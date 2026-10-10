"""SSH server core for Quantum Grid 2099: BLACKOUT PROTOCOL.

Runs an asyncssh server on port 2222. Every incoming connection gets its
own independent asyncio session:
  title -> save menu -> sector select -> node select -> gameplay loop
  (+ codex screen, persistent per-username saves).
Keypresses are read non-blocking (1 byte at a time) from the SSH channel.
"""

import asyncio
import os

import asyncssh

from . import save as save_mod
from .game import DIR_VECTORS, Game, start_bandwidth
from .levels import LEVELS
from .lore import (
    CODEX,
    CODEX_ON_NODE,
    CODEX_ON_START,
    CODEX_ON_ZONE,
)
from .render import (
    CLEAR,
    HIDE_CURSOR,
    MIN_H,
    MIN_W,
    SHOW_CURSOR,
    ZONE_COUNT,
    ZONE_SIZE,
    render_codex,
    render_frame,
    render_game_over,
    render_goodbye,
    render_level_complete,
    render_level_intro,
    render_node_select,
    render_save_menu,
    render_title,
    render_victory,
    render_zone_select,
)

# Arrow-key escape sequences mapped onto WASD equivalents.
ARROW_MAP = {"A": "w", "B": "s", "C": "d", "D": "a"}

QUIT = None  # EOF, Ctrl-C or 'q'
NOOP = ""  # ignored input
_TIMEOUT = object()  # digit-buffer window expired (distinct from QUIT)


class QuantumGridServer(asyncssh.SSHServer):
    """SSH server that requires no authentication and runs the game."""

    def __init__(self):
        self.username = "guest"

    def connection_made(self, conn: asyncssh.SSHServerConnection) -> None:
        self._conn = conn

    def begin_auth(self, username: str) -> bool:
        # No authentication required for this game; remember the handle.
        self.username = username or "guest"
        return False

    def session_requested(self):
        username = self.username

        def _handler(stdin, stdout, stderr):
            return handle_session(stdin, stdout, stderr, username)

        return _handler


class Session:
    def __init__(self, stdin, stdout, peer: str, username: str):
        self.stdin = stdin
        self.stdout = stdout
        self.peer = peer
        self.username = username or "guest"
        self.bandwidth = 100
        self.unlock_all = os.environ.get("QG_UNLOCK_ALL", "") == "1"
        self.no_ice = os.environ.get("QG_NO_ICE", "") == "1"
        self.save = save_mod.load(self.username)
        if self.unlock_all:
            self.save["unlocked"] = len(LEVELS) - 1
        self.total_actions = 0
        self.session_score = 0
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
        wasd/r/k/c/n digits, ENTER, or space.
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
            if ch in ("r", "R", "k", "K", "c", "C", "n", "N", "s", "S", "w", "W"):
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

    # ------------------------------------------------------------------ saves

    def unlock_codex(self, key: str) -> bool:
        codex = self.save.setdefault("codex", [])
        if key not in codex:
            codex.append(key)
            save_mod.store(self.username, self.save)
            return True
        return False

    def _codex_for_node(self, index: int) -> str | None:
        if index in CODEX_ON_NODE:
            return CODEX_ON_NODE[index]
        defn = LEVELS[index]
        if defn.zone > 1 and index == defn.zone * ZONE_SIZE - 1:
            return CODEX_ON_ZONE.get(defn.zone)
        return None

    def bank_win(self, index: int, game: Game) -> None:
        """Persist progress after clearing a node."""
        self.save["unlocked"] = max(self.save.get("unlocked", 0), index + 1)
        self.save["total_score"] = self.save.get("total_score", 0) + game.score()
        self.save["total_actions"] = self.save.get("total_actions", 0) + game.actions
        shards = self.save.setdefault("shards", {})
        taken = {str(game.layout.shards.index(s)) for s in game.shards_taken}
        prev = set(shards.get(str(index), []))
        shards[str(index)] = sorted(prev | taken)
        key = self._codex_for_node(index)
        if key:
            self.unlock_codex(key)
        save_mod.store(self.username, self.save)

    # ------------------------------------------------------------------- flow

    async def run(self) -> None:
        try:
            self.write(HIDE_CURSOR + CLEAR + render_title(self.width, self.height))
            if await self.read_key() is QUIT:
                return
            await self._save_menu()
            for key in CODEX_ON_START:
                self.unlock_codex(key)
            while True:
                result = await self._sector_flow()
                if result == "quit":
                    return
                if result == "victory":
                    self.width, self.height = self._frame_size()
                    self.write(
                        CLEAR
                        + render_victory(
                            self.save, _total_shards_in_game(), self.width, self.height
                        )
                    )
                    await self.read_key()
                    return
        finally:
            self.write(SHOW_CURSOR + render_goodbye(self.width, self.height))

    async def _save_menu(self) -> None:
        has_progress = (
            self.save.get("unlocked", 0) > 0 or self.save.get("total_score", 0) > 0
        )
        if not has_progress:
            return
        while True:
            self.width, self.height = self._frame_size()
            self.write(
                CLEAR + render_save_menu(self.save, self.username, self.width, self.height)
            )
            key = await self.read_key()
            if key is QUIT:
                return
            if key == "n":
                self.save = save_mod.default_save()
                if self.unlock_all:
                    self.save["unlocked"] = len(LEVELS) - 1
                save_mod.store(self.username, self.save)
                return
            if key in ("\r", "\n", " "):
                return

    async def _codex_screen(self) -> None:
        sel = 0
        detail = False
        while True:
            self.width, self.height = self._frame_size()
            self.write(
                CLEAR
                + render_codex(self.save, sel, detail, self.width, self.height)
            )
            key = await self.read_key()
            if key is QUIT or key == "c":
                return
            if key in ("w", "s"):
                detail = False
                sel = (sel + (-1 if key == "w" else 1)) % len(CODEX)
            elif key in ("\r", "\n", " "):
                detail = not detail
            elif key == "k":
                return

    def _first_uncleared(self) -> int:
        return min(self.save.get("unlocked", 0), len(LEVELS) - 1)

    def _sector_for(self, index: int) -> int:
        return index // ZONE_SIZE + 1

    async def _sector_flow(self) -> str:
        """Sector select -> node select -> play. Returns quit/victory/loop."""
        while True:
            self.width, self.height = self._frame_size()
            self.write(
                CLEAR
                + render_zone_select(
                    self.save, self.unlock_all, self.width, self.height
                )
            )
            key = await self.read_key()
            if key is QUIT:
                return "quit"
            if key == "c":
                await self._codex_screen()
                continue
            if key in ("\r", "\n", " "):
                index = self._first_uncleared()
                result = await self._node_flow(self._sector_for(index))
                if result != "back":
                    return result
                continue
            if key and key.isdigit() and key != "0":
                zone = int(key)
                if 1 <= zone <= ZONE_COUNT:
                    unlocked = self.unlock_all or self.save.get("unlocked", 0) >= (zone - 1) * ZONE_SIZE
                    if unlocked:
                        result = await self._node_flow(zone)
                        if result != "back":
                            return result

    async def _node_flow(self, zone: int) -> str:
        start = (zone - 1) * ZONE_SIZE
        while True:
            self.width, self.height = self._frame_size()
            self.write(
                CLEAR
                + render_node_select(
                    zone, self.save, self.unlock_all, self.width, self.height
                )
            )
            key = await self.read_key()
            if key is QUIT:
                return "quit"
            if key == "c":
                await self._codex_screen()
                continue
            if key in ("\r", "\n", " "):
                cleared_all = self.save.get("unlocked", 0) >= start + ZONE_SIZE
                if cleared_all:
                    return "back"  # sector complete: pick the next sector
                # jump to the first uncleared node in this sector
                unlocked = min(self.save.get("unlocked", 0), start + ZONE_SIZE - 1)
                if unlocked < start:
                    index = start
                else:
                    index = unlocked
                result = await self._play_level(index)
                if result == "next":
                    continue
                return result
            if key and key.isdigit() and key != "0":
                n = int(key)
                idx = start + n - 1
                if 0 <= idx < len(LEVELS) and idx < start + ZONE_SIZE:
                    selectable = self.unlock_all or idx <= self.save.get("unlocked", 0)
                    in_sector = idx >= start
                    if selectable and in_sector:
                        result = await self._play_level(idx)
                        if result == "next":
                            continue
                        return result

    async def _play_level(self, index: int) -> str:
        defn = LEVELS[index]
        bandwidth = start_bandwidth(defn, self.bandwidth)
        game = Game(
            index,
            bandwidth,
            self.save.get("unlocked", 0),
            no_ice=self.no_ice,
        )
        self._last_game = game
        self.width, self.height = self._frame_size()
        self.write(
            CLEAR
            + render_level_intro(defn, index, bandwidth, self.width, self.height)
        )
        if await self.read_key() is QUIT:
            return "quit"
        self.write(render_frame(game, self.width, self.height, self.session_score))
        while True:
            key = await self.read_key()
            if key is QUIT:
                return "quit"
            if key == "k":
                game.restart()
                self.write(
                    render_frame(game, self.width, self.height, self.session_score)
                )
                continue
            if key in DIR_VECTORS:
                acted = game.do_move(*DIR_VECTORS[key]) == "ok"
            elif key == "r":
                acted = game.do_rotate()
            else:
                continue
            if acted:
                self.total_actions += 1
            if game.check_win():
                self.bank_win(index, game)
                self.session_score = self.save.get("total_score", 0)
                self.bandwidth = game.finish_level()
                if index == len(LEVELS) - 1:
                    return "victory"
                self.width, self.height = self._frame_size()
                self.write(
                    CLEAR
                    + render_level_complete(
                        game, index + 1, self.session_score, self.width, self.height
                    )
                )
                if await self.read_key() is QUIT:
                    return "quit"
                return "next"
            if game.game_over:
                self.write(
                    CLEAR + render_game_over(game, self.width, self.height)
                )
                await self.read_key()
                return "next"  # back to node select, progress kept
            self.width, self.height = self._frame_size()
            self.write(
                render_frame(game, self.width, self.height, self.session_score)
            )


def _total_shards_in_game() -> int:
    from .levels import parse_level

    total = 0
    for defn in LEVELS:
        try:
            total += len(parse_level(defn.rows, defn.name).shards)
        except ValueError:
            continue
    return total


async def handle_session(stdin, stdout, stderr, username: str = "guest") -> None:
    peer = ""
    try:
        peer = str(stdout.channel.get_extra_info("peername") or "")
    except Exception:  # noqa: BLE001, S110 - peername is best-effort only
        pass
    session = Session(stdin, stdout, peer, username)
    print(f"[QGRID] session opened: {session.username}@{session.peer}")
    try:
        await session.run()
    except (asyncssh.DisconnectError, ConnectionError, OSError):
        pass
    except Exception as exc:  # noqa: BLE001 - keep the server alive no matter what
        print(f"[QGRID] session error: {exc!r}")
    finally:
        print(f"[QGRID] session closed: {session.username}@{session.peer}")


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
