# RAKSHAK-NET · Testing Guide

Everything you can run to prove the system works — automated suite first, then live
single-node smoke tests, then the full district-vault mesh, then the workbench UI.

> **TL;DR** — fully automated: `cd app/backend && python3 -m pytest -q` → **139 passed**.
> For the live demo: `app/scripts/run_mesh.sh` → mesh gateway `:8000`, Delhi/Mumbai/Jaipur
> vaults `:8001–:8003`, workbench `:3000`.

---

## 0 · Prerequisites

| Piece | Install |
| --- | --- |
| Python 3.9+ | any (core packages are **stdlib-only**) |
| FastAPI / pytest | `cd app/backend && pip install -r requirements.txt` |
| Node 18+ + pnpm | `cd app && pnpm install` |

The core pipeline (`synthgen` → `resolve` → `graph` → `analytics`) runs **without any
dependency** — deterministic and seeded, so test outputs are reproducible byte-for-byte.

---

## 1 · Automated test suite (`backend/tests`, 139 tests)

```bash
cd app/backend
python3 -m pytest -q              # full suite → 139 passed
python3 -m pytest -q -k synthgen  # or scope by module (see table)
```

| Test file | Proves | Key assertion |
| --- | --- | --- |
| `test_synthgen.py` | synthetic benchmark generator | ground-truth clusters, noise types, manifests |
| `test_resolve.py` | hybrid entity resolution | all §23 targets; **beats exact/fuzzy baselines** |
| `test_graph.py` | temporal knowledge graph build | 3 layers, provenance, SHA-256 audit hashes |
| `test_analytics.py` | anomaly detector | cycles **P 1.000 / R 1.000**, bursts **P 1.000 / R 1.000** |
| `test_escalation.py` | stalking escalation | weekly trajectory + night-call CRITICAL signals |
| `test_blindspot.py` | honest-AI blindspot | corroboration scores, missing-layer detection |
| `test_indic_xlit.py` | IndicXlit adapter | Devanagari↔Latin transliteration & fallback |
| `test_api.py` | FastAPI end-to-end | all 20+ endpoints, response schemas, integrity |
| `test_ledger.py` | hash-chain ledger | tamper-evidence: breaks after the touched record |
| `test_review.py` | human-in-the-loop review | ACCEPT / REJECT / MODIFY persist, chained |
| `test_victim_shield.py` | victim-shield (Women Safety) | masking + redaction for protected parties |
| `test_warrant.py` | warrant gate | scoped / expiring / dual-sign / revoke / verify |
| `test_ingest.py` | live FIR ingestion | regex NER with source spans, graph grows |
| `test_query.py` | grounded NL query | refuses unknown entities, cites every claim |
| `test_mesh.py` | district vault mesh | HMAC envelopes, receipts, exchange ledger |
| `test_scanner.py` + `test_sentinel.py` | RakshakAI security | rule engine CWE scan + graded posture/self-scan + manifest comparison |
| `test_scan_repo.py` | scanner CLI + CI gate | walker exclusions, exit codes 0/1/2, SARIF structure + stable fingerprints, baseline mode, explicit model failure |
| `test_experiment_a.py` | Experiment A baselines | exact vs fuzzy vs hybrid — hybrid wins |

### RakshakAI scanner CLI (whole-repo gate)

```bash
cd app
# gate: fail only on NEW findings at/above a severity vs the committed baseline
python backend/scripts/scan_repo.py backend/api backend/mesh backend/scripts \
  --fail-on CRITICAL --baseline backend/scripts/scan_baseline.json --sarif rakshakai.sarif
# exit 0 = pass · 1 = new findings ≥ threshold · 2 = scanner/config error

# tamper demo (the judge moment): plant a vulnerable file and watch the gate fail
echo 'db.execute(f"SELECT * FROM t WHERE id={uid}")' > /tmp/plant.py
python backend/scripts/scan_repo.py backend/api /tmp/plant.py \
  --baseline backend/scripts/scan_baseline.json
```

---

## 2 · Single-node API smoke test (one vault = the whole app)

```bash
cd app/backend
uvicorn api.main:app --port 8000        # builds the seed-42 graph on first boot
# OpenAPI explorer: http://localhost:8000/docs
```

Run these (jq optional — read the JSON):

```bash
BASE=http://localhost:8000

# 1. liveness + graph size
curl -s $BASE/api/health

# 2. hybrid identity resolution (cross-script match)
curl -s $BASE/api/resolve -X POST -H 'Content-Type: application/json' \
  -d '{"name_a":"Mohammad Arif","name_b":"मोहम्मद आरिफ़"}'
#   → decision MATCH, confidence ≈ 0.94, 4-feature breakdown

# 3. ground a real question against the graph (grab an id first)
curl -s "$BASE/api/entities?type=PERSON&limit=5"
curl -s -G $BASE/api/query --data-urlencode \
  'q=what is the phone linked to this person' --data-urlencode 'limit=10'
#   → cited answer or an explicit refusal — never a hallucination

# 4. evidence integrity walk
curl -s "$BASE/api/evidence/<edge_id>"     # hash_verified: true + source snippets
curl -s $BASE/api/reviews/verify           # walk review chain → no broken record

# 5. warrant-gate artifact lifecycle (DEPA consent)
W=$BASE/api/warrants
curl -s $W -X POST -H 'Content-Type: application/json' \
  -d '{"scope":"edge:E-<edge_id>","requester_id":"inspector-01","requester_role":"INSPECTOR","reason":"stalking investigation"}'
curl -s $W/<warrant_id>/approve -X POST -H 'Content-Type: application/json' \
  -d '{"approver_id":"sp-01","approver_role":"SP"}'      # dual-sign (four-eyes)
curl -s $W/verify                                        # chain intact
curl -s $W/<warrant_id>/revoke -X POST                   # revoke → access stops

# 6. live FIR ingestion (paste a raw Hindi FIR)
curl -s $BASE/api/ingest/fir -X POST -H 'Content-Type: application/json' -d '{
  "narrative":"दिनांक 12/04/2026 को शिकायतकर्ता ने बताया कि संदिग्ध ने +91-9812345678 से धमकी भरा कॉल किया। वाहन DL3C 9423 देखा गया।",
  "district":"Delhi","police_station":"PS Karol Bagh","date":"2026-04-12",
  "complainant_name":"Sunita Devi","accused_names":["Ramesh Kumar"]}'
#   → extracted entities with source spans, graph_stats grew
curl -s "$BASE/api/report/<entity_id>"     # court-ready evidence-chain report
curl -s $BASE/api/escalation               # stalking CRITICAL signals
curl -s $BASE/api/anomalies                # circular-flow / burst leads
curl -s $BASE/api/security/posture         # Sentinel graded posture + build manifest
```

---

## 3 · Full mesh (the "UPI of criminal intelligence")

```bash
cd app
./scripts/run_mesh.sh
#   gateway :8000 (NPCI-style switch — receipts only, never case data)
#   delhi :8001 · mumbai :8002 · jaipur :8003 vaults
#   workbench :3000 (pointing at the delhi vault)
```

```bash
curl -s http://localhost:8000/mesh/health        # all vaults reachable
curl -s http://localhost:8000/mesh/receipts      # signed exchange ledger
curl -s http://localhost:8000/mesh/verify        # walk the ledger → intact

# fan-out one query to every district from the delhi vault
curl -s http://localhost:8001/mesh/query -X POST -H 'Content-Type: application/json' \
  -d '{}'                                        # see docs/ARCHITECTURE.md for the envelope shape
```

Verify: `data never leaves its district` — the gateway ledger stores **receipts and
record ids only**, never case content; each vault answers locally behind an HMAC-signed
envelope.

---

## 4 · Investigator Workbench (manual UI checklist)

| Scenario | Steps | Expected |
| --- | --- | --- |
| Landing | open `http://localhost:5173` (dev, pnpm) or `:3000` (mesh) | cinematic hero, no console errors |
| Graph view | `/workbench` | layered entity graph renders; time-travel slider rewinds the graph |
| Query rail | type an investigation question | cited answer with source edges, no invented entities |
| Evidence panel | click an edge | source snippets + **hash verified: true** live check |
| File FIR (**demo star**) | paste a raw FIR (Hindi) | entities extracted with spans, cross-district collision alerts, graph grows in real time |
| Warrant gate | try protected/victim data | **scoped, expiring, dual-sign warrant** modal — access ledgered |
| Report | `/report/{entity_id}` | court-ready hash-verified evidence chain |
| Blindspot | entity panel | missing layers + corroboration score |
| Escalation | `/workbench` alerts | weekly trajectory + night-call sparklines |
| Scanner | `/scanner` | paste vulnerable code → CWE findings |
| Sentinel | `/api/security/posture` via UI/curl | graded endpoint levels + boot self-scan |

---

## 5 · Integrity & security checks (the three guarantees)

1. **Never lies (retrieval-only ask)** — `GET /api/query` with a *fabricated* entity name
   must **refuse**, not invent; every returned claim has a cited edge.
2. **Never forgets / never tampers** — `POST /api/review` then re-run
   `GET /api/reviews/verify`; the chain names any broken record. Touching the SQLite
   ledger directly (a manual edit) must flip `hash_verified: false` at that point.
   `GET /api/warrants/verify` and `GET /mesh/verify` do the same for their ledgers.
3. **Never profiles the innocent** — victim-shield is enforced in code: protected
   complainants come back pseudonymized; unmasking requires a granted (dual-signed,
   non-expired) warrant, and the access itself is ledgered.

---

## 6 · Expected numbers on the synthetic benchmark

| Quantity | Value |
| --- | --- |
| Automated suite | **139 / 139** |
| Event-loop cycles | P **1.000** / R **1.000** (planted positives) |
| Transfer bursts | P **1.000** / R **1.000** |
| Entity resolution | all §23 targets met; hybrid beats exact & fuzzy-only baselines |
| Tale of two scripts | `Mohammad Arif` ↔ `मोहम्मद आरिफ़` → `MATCH`, conf ≈ 0.94 |
| Core dependencies | **zero** (synthgen / resolve / graph / analytics = stdlib) |

> **Disclaimer.** Figures are measured on the **synthetic benchmark**, not real data;
> confidence scores are currently **uncalibrated** — investigative leads, not verdicts.