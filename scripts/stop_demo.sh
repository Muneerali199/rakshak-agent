#!/usr/bin/env bash
# stop_demo.sh — halt every demo service started by demo_reset.sh.
set -euo pipefail
cd "$(dirname "$0")/.."
PORTS=(8000 8010 8011 8012 8013 3000 5173)
for PORT in "${PORTS[@]}"; do
  PIDS=$(lsof -ti ":$PORT" 2>/dev/null || true)
  [ -n "$PIDS" ] && { kill $PIDS 2>/dev/null || true; echo "stopped :$PORT → $PIDS"; }
done
echo "✔ demo stopped"