# RAKSHAK-NET — Tech Stack & Algorithms

>What runs where, which standard-library algorithm does what, and how each "pitch line"
>maps to a concrete, testable implementation. 119/119 tests green · `tsc -b` clean · `pnpm build` clean.

---

## 1. Stack snapshot

| Layer | Technology | Notes |
| --- | --- | --- |
| Frontend | **Vite · React 19 · TypeScript · Tailwind v3** · @xyflow/react · GSAP + Framer Motion | pnpm-managed. Agents must use `pnpm`, not `npm`. |
| Backend API | **FastAPI · Uvicorn · Pydantic · httpx** | thin layer only |
| Core intelligence | **Python 3.9+ standard library** | deterministic, seeded-42, air-gapped |
| Graph | in-memory Python + SQLite persistence | proposal targets Neo4j for scale |
| Ledgers | SQLite append-only, SHA-256 hash-chained | reviews · warrants · mesh exchanges |
| UI | `bg-[#0a0f1c]` slate dark · glassmorphism · mono data · cyan/purple/emerald accents |

> ⚠️ The deck historically said "Next.js / Neo4j / pgvector". The **actual build is Vite+React
> 19 with a stdlib Python core + SQLite**. The deck must be updated to match reality.

---

## 2. The algorithm map

### Identity resolution (`resolve/`)
`Mohammad Arif` / `Mohd Arif` / `मोहम्मद आरिफ़` / `mohamad arif` → one person.

- **Features (Algorithm 2):** identifier, name similarity, **phonetic** (custom Soundex/phonex for
  Indic scripts), attribute (phone/vehicle/account — deterministic).
- **IndicXlit adapter** (`resolve/indic_xlit.py`): AI4Bharat-style Devanagari↔Latin. Works when the
  neural model is locally installed; **honest fallback** otherwise — zero new hard dependencies.
- Output per pair: `MATCH / UNCERTAIN / NON_MATCH` + calibrated confidence + broken-down features.
  Uncertain merges route to human review — never silently merged.

### Temporal knowledge graph (`graph/`)
- **3 seeded layers:** Communication · Financial · Spatial (of 6 proposed).
- Every edge is `observed | inferred`, timestamped, carries full **provenance** (source record +
  span) and a **SHA-256 audit hash** re-verified live in the evidence panel.
- Inferred edges shown at their confidence (e.g. `60% · pending review`) — a *lead*, not a verdict.

### Anomaly detection (`analytics/detect.py`)
- Circular-flow + burst detectors. On the planted ground-truth set: **cycles P 1.000 / R 1.000,
  bursts P 1.000 / R 1.000** (full benchmark, Experiment A honest baselines).

### Stalking escalation (`analytics/escalation.py`)
- Weekly call-trajectory + **night-call signal** + victim-linked CRITICAL alert.
- The "see the curve, not the file" intervention story.

### Blindspot / corroboration (`analytics/blindspot.py`)
- Explicitly scores **what the report cannot establish**: missing layers, inferred-ratio,
  source diversity, temporal gaps → a corroboration score. Honest-AI differentiator.

### District Vault Mesh (`mesh/`)
- **gateway.py:** `/mesh/route` — HMAC-sign envelope → forward to vaults → collect → return.
  Stores **receipts, never data**. `/mesh/health`, `/mesh/receipts`, `/mesh/verify`.
- **client.py:** fan-out from the central API (`POST /mesh/query`) to each vault.
- **protocol.py:** the request/response envelope format + signing.
- **ledger.py:** SHA-256 hash-chained SQLite exchange log.

- *Mesh trigger:* the `＋ File FIR` ingest of cross-district identifiers (or a Report "jurisdiction
  chain"). It is **not** visible in normal graph browsing — it fires when the mesh would add value.

### Warrant gate (`api/warrants.py`)
- Scoped, expiring, **revocable**; **four-eyes dual-sign** — IO requests, an SP+ countersigns
  (self-approval is rejected in code). Access itself is ledgered; `/api/warrants/verify`.

### Sentinel self-security (`api/sentinel.py`)
- Graded endpoint levels (**MLPS-inspired**), boot self-scan **hash-chained** into a ledger,
  code-build manifest, `/api/security/posture`.

### RakshakAI 14B (supplementary, security)
- Fine-tune on `Qwen/Qwen2.5-Coder-14B-Instruct` for CWE/vulnerability detection of the
  platform's *own* code. Rule-engine default, `RAKSHAK_AI_URL` model hook. Not a runtime firewall.

---

## 3. Full mesh + API surface (live)

Boot: `scripts/run_mesh.sh` → gateway `:8000` · Delhi `:8001` · Mumbai `:8002` · Jaipur `:8003` · UI `:3000`.

| Method | Endpoint | Purpose |
| --- | --- | --- |
| `GET` | `/api/health` | liveness + graph size |
| `POST` | `/api/resolve` | 2 names → MATCH/UNCERTAIN/NON_MATCH + feature breakdown |
| `GET` | `/api/graph/subgraph` | layered neighborhood (filter layers/depth/time-travel) |
| `GET` | `/api/entities` | risk-ranked entity list (role = accused/victim/mentioned) |
| `GET` | `/api/evidence/{edge_id}` | source snippets + **live SHA-256 verify** + victim redaction |
| `GET` | `/api/query` | grounded NL query — retrieval-only, refuses unknowns |
| `GET` | `/api/anomalies` | circular-flow / burst leads + self-test eval |
| `POST` | `/api/review` · `GET /api/reviews` · `GET /api/reviews/verify` | human sign-off · audit · verify |
| `POST` | `/api/warrants` · `/approve` · `/revoke` · `GET /verify` | DEPA-consent warrant lifecycle |
| `POST` | `/api/ingest/fir` | raw FIR → regex NER (source spans) → **mesh collision alerts** → graph grows live |
| `GET` | `/api/escalation` | stalking/escalation CRITICAL alerts |
| `GET` | `/api/blindspot/{id}` | corroboration / blind-spot report |
| `GET` | `/api/security/posture` | sentinel graded posture + boot self-scan |
| `GET` | `/api/experiments/a` | exact vs fuzzy vs hybrid baseline eval |
| `POST` | `/api/scan` | RakshakAI code-security scan |
| `GET` | `/mesh/route` · `/mesh/health` · `/mesh/receipts` · `/mesh/verify` | gateway switch (mesh) |

**Reference call:** `POST /api/resolve {"name_a":"Mohammad Arif","name_b":"मोहम्मद आरिफ़"}`
→ `{"decision":"MATCH", ...}` (demo returned MATCH 100%, name 1.00 · phonetic 1.00).

---

## 4. Determinism & reproducibility

- `synthgen --seed 42 --out output` reproduces byte-for-byte.
- Full test-suite: `pytest -q` → **119/119 passing**.
- The three ledgers verify with `ok:true` on a clean run: `/api/reviews/verify`, `/api/warrants/verify`, `/mesh/verify`.

---

## 5. Indian-stack alignment (Atmanirbhar Bharat)

- **Bhashini** — production speech-to-text/language-detection for dictated FIRs (offline in demo;
  plugs in at ingestion when connectivity exists).
- **AI4Bharat IndicNLP** — IndicXlit conventions for Devanagari↔Latin; IndicNER/IndicTrans as the
  upgrade path.
- **NIC MeghRaj Cloud** — target deployment host; entire core is stdlib Python with no foreign
  cloud dependency.
- **CCTNS / ICJS / NCRB** — canonical schema mirrors CCTNS record formats (FIR, CDR, financial) so
  integration is schema-mapping, not re-architecture.
- **Data sovereignty** — on-premise, offline, no OpenAI/Gemini/external calls in the serving path.
