# RAKSHAK-NET

**AI-powered temporal criminal-network intelligence & evidence graph platform.**

An investigative **decision-support** system that fuses fragmented, multilingual crime records —
FIRs, call detail records, financial trails — into a single **temporal, evidence-grounded knowledge
graph**. Every relationship traces back to its source document, carries a confidence score, and is
verified by a human before it informs any consequential decision.

> **Smart India Hackathon 2026** · Problem **SIH26189** · Ministry of Home Affairs — National Crime
> Records Bureau (NCRB), Women Safety Division.

This repository is a working monorepo: a **cinematic landing page**, a **dependency-free Python
pipeline** (synthetic-data → entity resolution → temporal graph), a **FastAPI** service, and a **live
Investigator Workbench** (React Flow) wired to it end-to-end. The authoritative research proposal
(architecture, algorithms, evaluation plan) is `RAKSHAK_NET_Research_Proposal.pdf`, kept separately.

---

## Status at a glance

| Component | State | Where |
| --- | --- | --- |
| Synthetic benchmark generator (Phase 2) | ✅ built · 7/7 tests | [`backend/synthgen`](backend/README.md) |
| Hybrid entity resolution (Phase 3) | ✅ built · 16/16 tests · all §23 targets met | [`backend/resolve`](backend/resolve/README.md) |
| Temporal knowledge graph — 3 MVP layers (Phase 4) | 🌱 seeded · 6/6 tests | [`backend/graph`](backend/graph/build.py) |
| FastAPI service (5 endpoints) | ✅ built · 6/6 tests | [`backend/api`](backend/api/main.py) |
| Investigator Workbench UI (`/workbench`) | ✅ wired to the API | [`src/workbench`](src/workbench) |
| RakshakAI code-security model | 🤖 published (supplementary) | [HF ↗](https://huggingface.co/Muneerali199/rakshak-cwe-14b-sft-final) |

Core Python packages (`synthgen`, `resolve`, `graph`) are **standard-library only** and deterministic
(seeded) — reproducible byte-for-byte. Third-party deps are isolated to the `api/` and frontend layers.

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
| `GET` | `/api/graph/subgraph` | Layered entity neighborhood: nodes, edges, `layer_assignments` (filter by `layers`, `depth`) |
| `GET` | `/api/evidence/{edge_id}` | Source-document snippets + **live SHA-256 verification** for an edge (Algorithm 7) |
| `GET` | `/api/entities` | Risk-ranked entity list (UI convenience) |
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

---

> **Disclaimer.** All quantitative performance figures are measured **on a synthetic benchmark** and
> are explicitly preliminary. RAKSHAK does not predict individual criminality, determine guilt, or
> support autonomous enforcement decisions. Confidence scores are currently **uncalibrated** and shown
> as investigative leads, not verdicts.
