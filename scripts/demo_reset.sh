#!/usr/bin/env bash
# demo_reset.sh — ONE command for a clean final-round demo:
#   kill stale services → wipe state → reseed seed-42 → re-partition → boot mesh.
#
#   gateway :8000      (NPCI-style switch — receipts only, never case data)
#   delhi vault :8001  ·  mumbai vault :8002  ·  jaipur vault :8003
#   frontend :3000     (talks to the delhi vault, like a UPI app talks to its bank)
#
# Run from repo root:  bash scripts/demo_reset.sh
set -euo pipefail
cd "$(dirname "$0")/.."          # repo root (app/)

LOG_DIR="backend/output/logs"
PORTS=(8000 8010 8011 8012 8013 3000 5173)

echo "▸ 1/5  killing anything on demo ports (${PORTS[*]})…"
for PORT in "${PORTS[@]}"; do
  PIDS=$(lsof -ti ":$PORT" 2>/dev/null || true)
  if [ -n "$PIDS" ]; then
    kill $PIDS 2>/dev/null || true
    echo "   :$PORT → $PIDS"
  fi
done
sleep 1
for PORT in "${PORTS[@]}"; do
  PIDS=$(lsof -ti ":$PORT" 2>/dev/null || true)
  [ -n "$PIDS" ] && kill -9 $PIDS 2>/dev/null || true
done

echo "▸ 2/5  wiping demo state (benchmark, vault partitions, ledgers, sentinel)…"
rm -rf backend/output backend/output-vaults

echo "▸ 3/5  regenerating seed-42 benchmark…"
(cd backend && python3 -m synthgen --seed 42 --out output)

echo "▸ 4/5  partitioning into district vaults…"
(cd backend && python3 scripts/partition_bench.py)

export RAKSHAK_VAULT_SECRETS='{"delhi":"demo-delhi","mumbai":"demo-mumbai","jaipur":"demo-jaipur"}'

mkdir -p "$LOG_DIR"

echo "▸ 5/5  booting: gateway :8000 · vaults :8001-8003 · UI :3000 → delhi vault"

(cd backend && nohup python3 -m uvicorn mesh.gateway:app --port 8000 \
   > "../$LOG_DIR/gateway.log" 2>&1 & disown)

for V in delhi:8001 mumbai:8002 jaipur:8003; do
  VID="${V%%:*}"; PORT="${V##*:}"
  (cd backend && RAKSHAK_VAULT_ID="$VID" RAKSHAK_BENCH_DIR="output-vaults/$VID" \
     RAKSHAK_GATEWAY_URL="http://localhost:8000" \
     nohup python3 -m uvicorn api.main:app --port "$PORT" \
     > "../$LOG_DIR/vault-$VID.log" 2>&1 & disown)
done

VITE_API_URL="http://localhost:8001" \
  nohup npm run dev > "$LOG_DIR/ui.log" 2>&1 & disown

echo
echo "✔ mesh is up — open http://localhost:3000/workbench and click  ＋ File FIR"
echo "  gateway log:  $LOG_DIR/gateway.log"
echo "  vault logs:   $LOG_DIR/vault-{delhi,mumbai,jaipur}.log"
echo "  ui log:       $LOG_DIR/ui.log"
echo
echo "  verify checklist:"
echo "    curl -s http://localhost:8000/mesh/health          → vaults + ledger ok"
echo "    curl -s http://localhost:8001/api/health           → delhi vault"
echo "    curl -s http://localhost:8002/api/health           → mumbai vault"
echo "    curl -s http://localhost:8003/api/health           → jaipur vault"
echo "    curl -s http://localhost:8001/api/security/posture → engine 'rules', manifest_check"
echo "  stop everything: bash scripts/stop_demo.sh"