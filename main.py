#!/usr/bin/env python3
"""Quantum Grid 2099 — SSH laser-reflection puzzle game.

Usage:
    python main.py [--host HOST] [--port PORT] [--host-key PATH]
"""

import argparse
import asyncio
import signal

from qgrid import __version__
from qgrid.server import start_server


async def amain(host: str, port: int, host_key: str) -> None:
    stop = asyncio.get_running_loop().create_future()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            asyncio.get_running_loop().add_signal_handler(
                sig, lambda: (not stop.done()) and stop.set_result(None)
            )
        except NotImplementedError:
            pass
    server_task = asyncio.create_task(start_server(host, port, host_key))
    await stop
    print("\n[QGRID] shutting down...")
    server_task.cancel()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Quantum Grid 2099 SSH game server")
    parser.add_argument(
        "--host", default="0.0.0.0", help="bind address (default: 0.0.0.0)"
    )
    parser.add_argument(
        "--port", type=int, default=2222, help="listen port (default: 2222)"
    )
    parser.add_argument("--host-key", default="ssh_host_key", help="SSH host key path")
    parser.add_argument(
        "--version", action="version", version=f"%(prog)s {__version__}"
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    try:
        asyncio.run(amain(args.host, args.port, args.host_key))
    except KeyboardInterrupt:
        pass
