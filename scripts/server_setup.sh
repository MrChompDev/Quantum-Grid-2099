#!/usr/bin/env bash
# Bootstrap Quantum Grid 2099 on a fresh Ubuntu VPS (tested target: Oracle
# Cloud Ubuntu 22.04/24.04, works on any Debian-ish box).
#
# Assumes the project files are already in /opt/qgrid (rsync them from your
# machine) and that you run this as a sudo-capable user:
#
#   rsync -av --exclude '.git' --exclude 'saves' --exclude 'ssh_host_key' \
#       ./ ubuntu@<VM_IP>:/opt/qgrid/
#   ssh ubuntu@<VM_IP> 'sudo bash /opt/qgrid/scripts/server_setup.sh'
#
# Handles the three things a bare Oracle Ubuntu image needs:
#   1. Docker Engine
#   2. OS firewall: Oracle images ship iptables REJECT rules — port 2222
#      must be opened there too, not just in the cloud security list.
#   3. The game itself (docker compose, saves + host key on a volume).
set -euo pipefail

APP_DIR="${APP_DIR:-/opt/qgrid}"
PORT="${PORT:-2222}"

cd "$APP_DIR"

# --- 1. Docker Engine -------------------------------------------------------
if ! command -v docker >/dev/null 2>&1; then
    echo "[qgrid] installing Docker..."
    curl -fsSL https://get.docker.com | sh
    systemctl enable --now docker
else
    echo "[qgrid] Docker already installed"
fi

# --- 2. Firewall: cloud-level rules are separate; open the OS level ---------
echo "[qgrid] opening TCP ${PORT} in the OS firewall..."
if command -v ufw >/dev/null 2>&1; then
    ufw allow "${PORT}/tcp" || true
fi
# Oracle Ubuntu images ship default iptables rules that REJECT everything
# except 22. Insert accepts for our port and make them persistent.
iptables -C INPUT -p tcp --dport "$PORT" -j ACCEPT 2>/dev/null || \
    iptables -I INPUT 5 -p tcp --dport "$PORT" -j ACCEPT
if command -v netfilter-persistent >/dev/null 2>&1; then
    netfilter-persistent save
else
    DEBIAN_FRONTEND=noninteractive apt-get install -y iptables-persistent
    netfilter-persistent save
fi
echo "[qgrid] NOTE: also allow TCP ${PORT} in the cloud provider's
        security list (OCI console: VCN -> Security Lists -> Add Ingress Rule)."

# --- 3. Launch the game ------------------------------------------------------
docker compose up -d --build
sleep 2
docker compose ps
echo
echo "[qgrid] done. Players connect with:  ssh -p ${PORT} <this-vm-ip>"
