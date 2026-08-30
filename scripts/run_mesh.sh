#!/usr/bin/env bash
# RAKSHAK-NET mesh demo — one command boots the whole "UPI of criminal intelligence":
#   mesh gateway :8000  (NPCI-style switch — receipts only, no case data)
#   delhi vault  :8001  ·  mumbai vault :8002  ·  jaipur vault :8003
#   frontend     :3000  (talks to the delhi vault, like a UPI app talks to your bank)
#
# First run: python3 scripts/partition_bench.py   (creates backend/output-vaults/)
set -euo pipefail
cd "$(dirname "$0")/.."          # repo root (app/)

if [ ! -d backend/output-vaults/delhi ]; then
  echo "▸ partitioning benchmark into district vaults…"
  (cd backend && python3 scripts/partition_bench.py)
fi

export RAKSHAK_VAULT_SECRETS='{"delhi":"demo-delhi","mumbai":"demo-mumbai","jaipur":"demo-jaipur"}'

echo "▸ mesh gateway  → http://localhost:8000"
(cd backend && python3 -m uvicorn mesh.gateway:app --port 8000 &)

for V in delhi:8001 mumbai:8002 jaipur:8003; do
  VID="${V%%:*}"; PORT="${V##*:}"
  echo "▸ ${VID} vault → http://localhost:${PORT}"
  (cd backend && RAKSHAK_VAULT_ID="$VID" RAKSHAK_BENCH_DIR="output-vaults/$VID" \
     RAKSHAK_GATEWAY_URL="http://localhost:8000" \
     python3 -m uvicorn api.main:app --port "$PORT" &)
done

echo "▸ frontend      → http://localhost:3000  (connected to delhi vault)"
VITE_API_URL="http://localhost:8001" npm run dev &

echo
echo "✔ mesh is up — open http://localhost:3000/workbench and click  ＋ File FIR"
echo "  stop everything:  kill \$(pgrep -f 'uvicorn (mesh|api)') ; kill \$(pgrep -f vite)"
wait
