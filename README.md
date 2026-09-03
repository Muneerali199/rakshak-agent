# RAKSHAK-NET

**The UPI of criminal intelligence — a constitutional evidence mesh.**

> *Also presented as **Rakshak AI** in the SIH 2026 idea-submission deck — same platform,
> internal codename RAKSHAK-NET. The 14B security model is **RakshakAI** (no space).*

Policing in India is a **State subject** (Seventh Schedule) — a central national crime
database is *legally impossible*. So RAKSHAK-NET does what India has already proven twice:
**UPI** made banks interoperable without centralizing money; **Account Aggregator (DEPA)**
shares data without storing it. RAKSHAK-NET makes **police districts interoperable without
centralizing FIRs** — each district vault keeps its own data, signed queries travel across
a mesh gateway (the NPCI-style switch that stores *receipts, never case data*), and every
protected-data access sits behind a **dual-signed warrant artifact** (the DEPA consent model).

> **Smart India Hackathon 2026** · Problem **SIH26189** · Ministry of Home Affairs — National Crime
> Records Bureau (NCRB), Women Safety Division.

This repository is a working monorepo: a **cinematic landing page**, a **dependency-free Python
pipeline** (synthetic-data → entity resolution → temporal graph), a **FastAPI** service runnable as
**3 district vaults + a mesh gateway**, and a **live Investigator Workbench** (React Flow) wired to
it end-to-end. The authoritative research proposal (architecture, algorithms, evaluation plan) is
`RAKSHAK_NET_Research_Proposal.pdf`, kept separately.

**One command, whole mesh:** `scripts/run_mesh.sh` → gateway `:8000`, Delhi/Mumbai/Jaipur vaults
`:8001-8003`, workbench `:3000`. Single-node dev mode still works untouched (`uvicorn api.main:app`).

---

## The three guarantees (the pitch)

> **India's first evidence-ledger criminal intelligence system.**

1. **Never lies** — the NL query is retrieval-only: every answer cites the edges that
   support it, and unknown entities are *refused*, not invented. No LLM in the serving
   path means no hallucination is possible by construction.
2. **Never forgets, never tampers** — every human review decision, every warrant event, and
   every cross-vault exchange is **hash-chained** (SHA-256, stdlib SQLite). Editing history
   breaks every link after it; `/api/reviews/verify`, `/api/warrants/verify`, and
   `/mesh/verify` walk their chains and name the first broken record.
3. **Never profiles the innocent** — *victim-shield* (Women Safety Division policy,
   enforced in code): complainants are pseudonymized; unmasking needs a **scoped, expiring,
   dual-signed warrant** (four-eyes principle) — and the access itself is ledgered.

**References fused:** Estonia **X-Road** (data sovereignty) · **UPI + DEPA/Account Aggregator**
(interoperability + consent artifacts — India's own DPI) · **INTERPOL** dual-authorization ·
China's **IJOP** studied and inverted (its detection capability, *with* the rights and
cryptographic accountability it lacked — and, per HRW's reverse engineering, the software
protection it lacked too: see RakshakAI Sentinel below).

---

## Status at a glance

| Component | State | Where |
| --- | --- | --- |
| Synthetic benchmark generator (Phase 2) | ✅ built · planted anomaly ground truth · 8/8 tests | [`backend/synthgen`](backend/README.md) |
| Hybrid entity resolution (Phase 3) | ✅ built · all §23 targets met · **beats exact/fuzzy baselines (Experiment A)** | [`backend/resolve`](backend/resolve/README.md) |
| Temporal knowledge graph — 3 layers + vehicles/accounts | ✅ built · multi-layer hubs · **victim-shield role tagging** | [`backend/graph`](backend/graph/build.py) |
| Anomaly detection (§14) | ✅ built · **cycles P 1.000 / R 1.000, bursts P 1.000 / R 1.000** | [`backend/analytics`](backend/analytics/detect.py) |
| Human-review persistence (Algorithm 8) | ✅ built · **hash-chained tamper-evident ledger** · SQLite append-only, survives restarts | [`backend/api/review_store.py`](backend/api/review_store.py) |
| Victim-shield (Women Safety policy layer) | ✅ built · query masking + evidence redaction for protected parties | [`backend/api/query.py`](backend/api/query.py) |
| Grounded NL query (§16, Algorithm 7) | ✅ built · anti-hallucination: refuses unknown entities, cites every claim | [`backend/api/query.py`](backend/api/query.py) |
| **Live FIR ingestion** | ✅ built · paste raw FIR → regex NER with source spans → **cross-district collision alerts** → graph grows live | [`backend/api/ingest.py`](backend/api/ingest.py) |
| **Stalking escalation detection** (Women Safety) | ✅ built · weekly trajectory + night-call signal + victim-linked CRITICAL alerts · planted ground truth | [`backend/analytics/escalation.py`](backend/analytics/escalation.py) |
| **Evidence chain report** | ✅ built · court-ready per-entity chain: hash-verified rows + review log + ledger integrity · `/report/{id}` page | [`backend/api/main.py`](backend/api/main.py) |
| **District Vault Mesh** ("UPI of criminal intelligence") | ✅ built · 3 vaults + NPCI-style gateway · HMAC-signed envelopes/receipts · hash-chained exchange ledger · data never leaves its district | [`backend/mesh`](backend/mesh) |
| **Warrant Gate** (DEPA consent artifacts) | ✅ built · scoped/expiring/revocable · four-eyes dual-sign (SP+) · access ledgered · `WarrantGateModal` UI | [`backend/api/warrants.py`](backend/api/warrants.py) |
| **Blindspot analysis** (honest AI) | ✅ built · missing layers + inferred-ratio + source diversity + temporal gaps → corroboration score | [`backend/analytics/blindspot.py`](backend/analytics/blindspot.py) |
| **RakshakAI Sentinel** (self-security) | ✅ built · graded endpoint levels (MLPS-inspired) · boot self-scan hash-chained · build manifest · `/api/security/posture` | [`backend/api/sentinel.py`](backend/api/sentinel.py) |
| IndicXlit adapter (AI4Bharat) | ✅ built · neural transliteration when locally installed, honest fallback otherwise · zero new hard deps | [`backend/resolve/indic_xlit.py`](backend/resolve/indic_xlit.py) |
| RakshakAI code scanner (§18) | ✅ built · rule engine + `RAKSHAK_AI_URL` 14B hook · `/scanner` UI | [`backend/api/scanner.py`](backend/api/scanner.py) |
| FastAPI service (20 endpoints) + Mesh gateway | ✅ built · **119/119 tests** | [`backend/api`](backend/api/main.py) |
| Investigator Workbench + Scanner UI | ✅ live · responsive · **File-FIR w/ live mesh receipts · warrant-gate modal · blindspot panel · escalation sparklines · vault badge · time-travel slider** | [`src/workbench`](src/workbench) |
| RakshakAI 14B model | 🤖 published (supplementary, hook-ready) | [HF ↗](https://huggingface.co/Muneerali199/rakshak-cwe-14b-sft-final) |

Core Python packages (`synthgen`, `resolve`, `graph`, `analytics`) are **standard-library only** and
deterministic (seeded) — reproducible byte-for-byte. Third-party deps are isolated to the `api/` and
frontend layers.

---

## 🇮🇳 Indian-stack alignment (Atmanirbhar Bharat)

RAKSHAK-NET is designed to run on India's own digital infrastructure — by default, not as an
afterthought:

- **Bhashini (Government of India)** — the production speech-to-text / language-detection path for
  dictated FIRs and multilingual ingestion ([bhashini.gov.in](https://bhashini.gov.in)). The demo
  runs fully offline (air-gapped); Bhashini plugs in at the ingestion layer when connectivity exists.
- **AI4Bharat IndicNLP** — our transliteration and name normalization follows **IndicXlit**
  conventions (Devanagari↔Latin), with IndicNER/IndicTrans as the upgrade path for the full
  prototype ([ai4bharat.iitm.ac.in](https://ai4bharat.iitm.ac.in)).
- **NIC MeghRaj Cloud** — the target deployment host for the district/state data centre; the entire
  core is stdlib-only Python with no foreign cloud dependency.
- **CCTNS / ICJS / NCRB** — the canonical schema (§7) mirrors CCTNS record formats (FIR, CDR,
  financial) so integration is schema-mapping, not re-architecture.
- **Data sovereignty** — unlike SaaS analytics that route sensitive police data through foreign
  APIs, every component here runs **on-premise and offline**: no OpenAI, no Gemini, no external
  calls in the serving path.

---

## What RAKSHAK is — and is not

This framing is a core design principle, not a disclaimer bolted on afterward.

| RAKSHAK **is** | RAKSHAK is **not** |
| --- | --- |
| Investigative decision-support | A surveillance or real-time monitoring system |
| Text / record entity resolution (names, phones, vehicles, accounts) | Facial or voice biometric identification |
| Evidence-grounded, source-traceable analytics | An opaque "black-box" scoring engine |
| "Analytical anomaly requiring investigation" | A predictor of individual criminality or guilt |
| Human-in-the-loop for every consequential output | An autonomous enforcement tool |
| Case-bounded and data-minimized | A national dragnet over the whole population |

**Anomaly ≠ criminality.** Every flagged pattern is a lead for a human investigator to examine, never
a verdict.

---

## The problem (SIH26189)

Indian law-enforcement data is fragmented across incompatible systems, written in Hindi, English and
Hinglish across scripts, and full of noise, duplicates, and transliteration variants (`Mohammad Arif`
/ `Mohd Arif` / `मोहम्मद आरिफ` / `mohamad arif` — all one person). Manual correlation is slow,
error-prone, and misses latent cross-domain links (a phone call → a money transfer → a vehicle
sighting). Generic LLM interfaces risk hallucinating connections that do not exist in the source data.

---

## The four pillars

1. **Multilingual Identity Resolution** — ✅ *implemented.* Resolves entity mentions across scripts and
   spellings. MVP uses 4 of the 8 proposed features (identifier, name, phonetic, attribute) plus
   Devanagari→Latin transliteration; phone/vehicle/account matches are deterministic; uncertain merges
   route to human review. *No facial or voice biometrics.* (Embeddings and graph-neighborhood features
   are the next increment.)
2. **Temporal Knowledge Graph** — 🌱 *3 of 6 layers seeded* (Communication, Financial, Spatial). Every
   edge is classified **observed / inferred**, timestamped, and carries full provenance plus a
   **SHA-256 audit hash**. (Organizational, case/event, and digital/social layers + cross-layer
   correlation are planned.)
3. **Evidence & Human Verification** — ✅ *implemented.* No output without an **Evidence Panel** tracing
   back to source documents; the edge's SHA-256 hash is re-verified live. Inferred relationships require
   investigator **Accept / Reject / Modify** sign-off.
4. **RakshakAI Code Security** — 🤖 *published, supplementary.* A security-focused `Qwen2.5-Coder-14B`
   fine-tune that scans the platform's *own* codebase for vulnerabilities (CWE detection). Secure-by-
   design, **not** a runtime firewall. See [RakshakAI](#rakshakai-code-security-layer).

---

## Architecture

```
                          ┌─────────────────  FRONTEND (Vite + React 19 + Tailwind)  ─────────────────┐
                          │   Landing page  ·  /workbench  (React Flow, 3-pane analyst UI)             │
                          └───────────────────────────────┬───────────────────────────────────────────┘
                                                           │  src/lib/api.ts  (typed fetch, CORS)
                          ┌────────────────────────────────▼──────────────────────────────────────────┐
                          │                       FastAPI  (backend/api)                                │
                          │  /resolve   /graph/subgraph   /evidence/{id}   /entities   /health          │
                          └───────┬──────────────────────┬───────────────────────┬─────────────────────┘
                                  │                       │                       │
                     ┌────────────▼─────────┐  ┌──────────▼──────────┐  ┌─────────▼─────────────┐
                     │  resolve  (Phase 3)  │  │   graph  (Phase 4)   │  │  synthgen  (Phase 2)  │
                     │  hybrid identity     │  │  3-layer temporal    │  │  synthetic FIR/CDR/   │
                     │  resolution (§9)     │  │  graph + provenance  │  │  FIN + ground truth   │
                     └──────────────────────┘  └──────────────────────┘  └───────────────────────┘
                                    stdlib-only · deterministic (seeded) · cite the proposal by §
```

**Stack.** Frontend: Vite · React 19 · TypeScript · Tailwind v3 (shadcn/ui) · @xyflow/react · GSAP +
Framer Motion. Backend: Python 3.9+ stdlib (core) · FastAPI + Uvicorn (API). *Proposal targets Neo4j +
pgvector + IndicNER/IndicXlit for the full prototype.*

---

## Getting started

### 1 · The Python pipeline (no dependencies)

```bash
cd app/backend
python -m synthgen --seed 42 --out output   # Phase 2 — generate the synthetic benchmark
python -m resolve  --in  output --verbose    # Phase 3 — resolve entities + print the §23 report
python3 tests/test_synthgen.py               # 7/7    (or: pytest -q)
python3 tests/test_resolve.py                # 16/16
python3 tests/test_graph.py                  # 6/6
```

### 2 · The API + Investigator Workbench (end-to-end)

```bash
# terminal 1 — backend API (from app/backend)
pip install -r api/requirements.txt
uvicorn api.main:app --port 8000             # builds the seed-42 graph on first boot
#   → OpenAPI docs at http://localhost:8000/docs

# terminal 2 — frontend (from app/) — this project is pnpm-native
pnpm install
pnpm dev                                     # → http://localhost:5173/workbench
```

Override the API base with `VITE_API_URL` if the backend isn't on `localhost:8000`.

> **Note:** the frontend is **pnpm-managed** (`.pnpm/`, `pnpm-lock.yaml`) — use `pnpm`, not `npm`
> (mixing the two corrupts `node_modules`).

### Frontend scripts

```bash
pnpm dev        # dev server → http://localhost:5173  (landing page at /, workbench at /workbench)
pnpm build      # tsc -b && vite build → dist/
pnpm preview    # preview the production build
pnpm lint       # eslint
```

---

## API reference (`backend/api`)

| Method | Endpoint | Purpose |
| --- | --- | --- |
| `POST` | `/api/resolve` | Hybrid identity resolution (Algorithm 2): two names (+ optional ids/attrs) → `MATCH/UNCERTAIN/NON_MATCH`, confidence, and the 4-feature breakdown |
| `GET` | `/api/graph/subgraph` | Layered entity neighborhood: nodes, edges, `layer_assignments` (filter by `layers`, `depth`, **time-travel `start`/`end`**) |
| `GET` | `/api/evidence/{edge_id}` | Source-document snippets + **live SHA-256 verification** for an edge (Algorithm 7) · **victim-shield redaction** for protected parties |
| `GET` | `/api/entities` | Risk-ranked entity list (UI convenience) · `meta.role` = accused/victim/mentioned |
| `GET` | `/api/query` | Grounded NL investigation query (§16) — refuses unknowns, masks victims |
| `GET` | `/api/anomalies` | Circular-flow / burst leads + self-test evaluation vs planted positives |
| `POST` | `/api/review` | Human-in-the-loop ACCEPT/REJECT/MODIFY (Algorithm 8) — hash-chained |
| `GET` | `/api/reviews` | Append-only audit history (newest first) |
| `GET` | `/api/reviews/verify` | **Verify the hash-chained evidence ledger** — reports first tampered record id |
| `POST` | `/api/scan` | RakshakAI code security scan (§18) — rule engine or 14B model hook |
| `GET` | `/api/experiments/a` | Experiment A: exact vs fuzzy-only vs hybrid baselines (§22) |
| `GET` | `/api/health` | Liveness + graph size |

Example — `POST /api/resolve` with `{"name_a":"Mohammad Arif","name_b":"मोहम्मद आरिफ़"}` →
`{"decision":"MATCH","confidence":0.94,"features":{"name":0.97,"phonetic":1.0,...},"calibrated":false}`.

---

## Repository structure

```
app/                            ← git repo root
├─ src/                         Frontend (Vite + React 19 + TS + Tailwind)
│  ├─ sections/                 Landing page: Hero · Problem · Solution · VisualProof · Footer
│  ├─ pages/                    Home · Workbench
│  ├─ workbench/                Live analyst UI: GraphCanvas · EntityNode · LayeredEdge · QueryRail · EvidencePanel
│  ├─ lib/api.ts                Typed backend client
│  └─ components/ui/            shadcn/ui primitives
├─ backend/
│  ├─ synthgen/                 Phase 2 — synthetic FIR/CDR/FIN generator + ground truth   (stdlib)
│  ├─ resolve/                  Phase 3 — hybrid entity resolution + §23 evaluation         (stdlib)
│  ├─ graph/                    Phase 4 seed — 3-layer temporal graph + provenance/SHA-256  (stdlib)
│  ├─ api/                      FastAPI service (schemas + endpoints)                        (fastapi)
│  └─ tests/                    test_synthgen · test_resolve · test_graph · test_api
└─ docs/
   ├─ HACKATHON_EXECUTION_PLAN.md   API contracts, UI spec, 10-minute demo script
   └─ huggingface/                  MODEL_CARD.md · DATASETS.md
```

---

## RakshakAI code-security layer

RakshakAI is the secure-by-design component. It is **not** used for criminal-network analysis — its
sole job is to review the platform's own code.

- **Model:** [`Muneerali199/rakshak-cwe-14b-sft-final`](https://huggingface.co/Muneerali199/rakshak-cwe-14b-sft-final)
  — LoRA/SFT adapter on `Qwen/Qwen2.5-Coder-14B-Instruct` for CWE / vulnerability detection.
- **Datasets:** [`Muneerali199` on Hugging Face](https://huggingface.co/Muneerali199/datasets) —
  `rakshak-cwe-v3-data`, `rakshak-sft-dataset`, `RakshakAI-v4-instruct`, `RakshakAI-phase-b`, and more.
- See [`docs/huggingface/MODEL_CARD.md`](docs/huggingface/MODEL_CARD.md) and
  [`docs/huggingface/DATASETS.md`](docs/huggingface/DATASETS.md).

Consistent with the proposal, RakshakAI is a **supplementary** security layer until it is benchmarked
against established static-analysis tools (Semgrep, SonarQube, Bandit).

---

## Roadmap

**36-hour MVP** — 3 synthetic sources · 2 languages (Hindi + English) · 4 entity-resolution features ·
3 graph layers · z-score anomaly detector · evidence panel · RakshakAI code scan.
Built ✅: synthgen · resolve (all §23 targets) · 3-layer graph · FastAPI · live workbench.

**3-month prototype**
- *Month 1* — synthetic benchmark generator ✅ · ingestion pipeline · Hindi+English NER · basic entity
  resolution ✅ · Neo4j schema.
- *Month 2* — Hinglish support · temporal edge annotation · community detection + centrality · evidence
  panel UI ✅.
- *Month 3* — cross-layer edges · anomaly detectors · NL query interface · persisted human-review
  workflow · RakshakAI integration.

**6–12 months** — pilot at one NCRB-affiliated unit → investigator feedback & threshold tuning →
multi-district scaling and CCTNS/NCRB format integration → security audit, red-teaming, and legal
review of evidence panels.

---

## Ethics & governance

Investigative intelligence only · data minimization · purpose limitation · no protected-class
inference · no predictive policing · no victim profiling. For Women Safety Division use cases, victim
data is pseudonymized and access-controlled; the system analyzes repeat-offender networks and incident
hotspots, and never profiles potential victims.

---

## Links

- 🤖 RakshakAI model: https://huggingface.co/Muneerali199/rakshak-cwe-14b-sft-final
- 📊 Datasets: https://huggingface.co/Muneerali199/datasets
- 🛠️ Hackathon execution plan: [`docs/HACKATHON_EXECUTION_PLAN.md`](docs/HACKATHON_EXECUTION_PLAN.md)
- 🎬 **5-minute demo script: [`docs/DEMO_SCRIPT.md`](docs/DEMO_SCRIPT.md)**
- 🗺️ Winning-feature plan: [`docs/NEXT_STEPS_PLAN.md`](docs/NEXT_STEPS_PLAN.md)

---

> **Disclaimer.** All quantitative performance figures are measured **on a synthetic benchmark** and
> are explicitly preliminary. RAKSHAK does not predict individual criminality, determine guilt, or
> support autonomous enforcement decisions. Confidence scores are currently **uncalibrated** and shown
> as investigative leads, not verdicts.
