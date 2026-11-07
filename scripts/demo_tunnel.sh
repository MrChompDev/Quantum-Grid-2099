#!/usr/bin/env bash
# Spin up a public, signup-free demo of Quantum Grid 2099 from this machine:
#   game server on 127.0.0.1:2222  +  a bore.pub TCP relay.
#
#   scripts/demo_tunnel.sh
#
# Prints the public address for players (e.g. ssh -p 19540 bore.pub).
# The relay assigns a random port each run, so always read the address from
# this script's output. Stop everything with:  pkill -f 'bore local|main.py'
#
# For a permanent install, deploy to a VPS instead (see README "Deployment").
set -euo pipefail

cd "$(dirname "$0")/.."
PORT="${PORT:-2222}"

if ! command -v bore >/dev/null 2>&1; then
    echo "[qgrid] installing bore (signup-free TCP relay)..."
    cargo install bore-cli
fi

pkill -f "bore local ${PORT}" 2>/dev/null || true
pkill -f "main.py --host 127.0.0.1 --port ${PORT}" 2>/dev/null || true
sleep 1

python3 main.py --host 127.0.0.1 --port "$PORT" &
GAME_PID=$!

bore local "$PORT" --to bore.pub 2>&1 | while read -r line; do
    port=$(printf '%s' "$line" | grep -oE 'remote_port=[0-9]+' | cut -d= -f2)
    if [ -n "$port" ]; then
        echo
        echo "=========================================================="
        echo "  QUANTUM GRID 2099 is live:"
        echo "      ssh -p ${port} bore.pub"
        echo "  (any username; the username is your save file)"
        echo "=========================================================="
    fi
done &
BORE_PID=$!

trap 'kill "$GAME_PID" "$BORE_PID" 2>/dev/null' EXIT INT TERM
echo "[qgrid] game pid $GAME_PID, relay pid $BORE_PID — Ctrl+C to stop."
wait
