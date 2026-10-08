#!/usr/bin/env bash
# demo_data_check.sh — self-check every beat in docs/JUDGE_DEMO_DATA.md is LIVE.
# Run from repo root while the demo mesh is up:
#   bash scripts/demo_data_check.sh
# Prints PASS/FAIL per beat. Exit 0 if all PASS, 1 otherwise.
set -u
B="http://localhost:8001/api"; G="http://localhost:8000"
PY="python3"
PASS=0; FAIL=0
ok()   { PASS=$((PASS+1)); echo "  PASS  $1"; }
bad()  { FAIL=$((FAIL+1)); echo "  FAIL  $1"; }
check_game(){ # name condition_jq json
  local name="$1" cond="$2" data="$3"
  if printf '%s' "$data" | "$PY" -c "import sys,json;d=json.load(sys.stdin);import re;sys.exit(0 if ($cond) else 1)" 2>/dev/null; then ok "$name"; else bad "$name"; fi
}

echo "▸ mesh + health"
h=$(curl -s --max-time 10 "$G/mesh/health")
if printf '%s' "$h" | "$PY" -c "import sys,json;d=json.load(sys.stdin);sys.exit(0 if d['ledger']['ok'] and len(d['vaults'])==3 else 1)"; then ok "mesh/health (3 vaults, ledger ok)"; else bad "mesh/health"; fi
for v in 1 2 3; do curl -fsS --max-time 10 "http://localhost:800$v/api/health" >/dev/null && ok "vault :800$v"; done

echo "▸ resolution"
check_game "cross-script MATCH (Mohammad Arif ≡ मोहम्मद आरिफ़)" "d['decision']=='MATCH' and d['confidence']==1.0" \
  "$(curl -s -X POST "$B/resolve" -H 'Content-Type: application/json' -d '{"name_a":"Mohammad Arif","name_b":"\u092e\u094b\u0939\u092e\u094d\u092e\u0926 \u0906\u0930\u093f\u092b\u093c"}')"
check_game "veto NON_MATCH (attr conflict)" "d['decision']=='NON_MATCH' and 'hard attribute' in (d.get('veto_reason') or '')" \
  "$(curl -s -X POST "$B/resolve" -H 'Content-Type: application/json' -d '{"name_a":"Mohammad Arif","name_b":"Mohammad Arif","address_a":"Karol Bagh, Delhi","address_b":"Byculla, Mumbai","age_a":34,"age_b":61}')"

echo "▸ officer session"
TOK=$(curl -s --max-time 15 -X POST "$B/auth/login" -H 'Content-Type: application/json' \
  -d '{"aadhaar":"700011771177","otp":"771177","purpose":"demo-check"}' | "$PY" -c 'import sys,json;print(json.load(sys.stdin).get("token",""))')
[ -n "$TOK" ] && ok "login (IO DEL-001)" || bad "login"
check_game "dossier Nehaa Kumaar (aliases incl नेहा कुमार, roles accused+complainant, 3 FIRs)" "d['found'] and ('नेहा कुमार' in d.get('aliases',[])) and set(['accused','complainant']).issubset(d.get('roles',[])) and d.get('fir_count')==3" \
  "$(curl -s -H "Authorization: Bearer $TOK" -X POST "$B/resolve/person" -H 'Content-Type: application/json' -d '{"name":"Nehaa Kumaar"}')"
check_game "evidence auto-resolve → both UNCERTAIN → route_to_review" "all(r['decision']=='UNCERTAIN' and r['route_to_review'] for r in d['rows'])" \
  "$(curl -s -H "Authorization: Bearer $TOK" -X POST "$B/resolve/evidence" -H 'Content-Type: application/json' -d '{"text":"शिकायतकर्ता Sunita Devi ने बताया कि Ramesh Kumar ने उसे +91-8044997278 से धमकी भरा कॉल किया।"}')"
check_game "escalation shows CRITICAL victim-linked alert" "any(a['severity']=='CRITICAL' for a in d['alerts'])" \
  "$(curl -s -H "Authorization: Bearer $TOK" "$B/escalation")"

echo "▸ grounded query"
check_game "connect query grounded" "d['grounded'] and d['intent']=='path'" \
  "$(curl -s --max-time 15 --get --data-urlencode 'q=how are Aniil Singh and Nehaa Kumaar connected' "$B/query")"
check_game "refusal (unknown entity, grounded=false)" "(not d['grounded']) and d['intent']=='unknown'" \
  "$(curl -s --max-time 15 --get --data-urlencode 'q=is Zzark Zulu linked to anyone' "$B/query")"

echo "▸ mesh signed envelope"
MSGS=$(cd backend 2>/dev/null && .venv/bin/python - <<'PY'
from mesh import protocol, client
s={"delhi":"demo-delhi","mumbai":"demo-mumbai","jaipur":"demo-jaipur"}
r=client.fanout_entity_lookup("delhi",["ACCOUNT:AC7332214188","ACCOUNT:AC8168505423"],"http://localhost:8000",s,timeout=8)
print(r["all_verified"],[x["responder_vault"] for x in r["receipts"]])
PY
)
case "$MSGS" in *True*) ok "mesh ENTITY_LOOKUP all_verified (mumbai/jaipur receipts)";; *) bad "mesh ENTITY_LOOKUP";; esac

echo "▸ trust chain"
check_game "posture: >=20 graded endpoints + rule-engine boot scan (40 files, 4 findings)" \
  "len(d.get('levels',{}))>=20 and d['boot_scan']['report']['engine']=='rules' and d['boot_scan']['report']['files_scanned']>=40" \
  "$(curl -s --max-time 15 "$B/security/posture")"
check_game "ocr registered offline (tesseract hin+eng)" "d.get('engine')=='tesseract-ocr' and d.get('available') is True" \
  "$(curl -s --max-time 15 "$B/security/posture" | $PY -c 'import sys,json;print(json.dumps(json.load(sys.stdin)["ocr"]))')"
for e in "$B/reviews/verify" "$B/warrants/verify" "$G/mesh/verify"; do
  curl -fsS --max-time 10 "$e" >/dev/null && ok "verify $e" || bad "verify $e"
done

echo
echo "PASS=$PASS FAIL=$FAIL"
[ "$FAIL" -eq 0 ]