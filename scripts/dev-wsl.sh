#!/usr/bin/env bash
set -euo pipefail

PORT="${PORT:-29393}"
HOST_IP=""

if [ -f /etc/resolv.conf ]; then
  HOST_IP=$(awk '/^nameserver /{print $2; exit}' /etc/resolv.conf || true)
fi

if [ -z "$HOST_IP" ]; then
  HOST_IP="127.0.0.1"
fi

echo "WSL host: http://${HOST_IP}:${PORT}"

exec npx vite --host 0.0.0.0 --port "${PORT}"
