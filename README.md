# RAKSHAK

**AI-powered temporal criminal-network intelligence & evidence graph platform.**

An investigative **decision-support** system that fuses fragmented, multilingual crime records —
FIRs, call detail records, financial trails, surveillance notes — into a single **temporal,
evidence-grounded knowledge graph**. Every relationship traces back to its source document, carries
a calibrated confidence, and is verified by a human before it informs any consequential decision.

> Smart India Hackathon 2026 · Problem **SIH26189** · Ministry of Home Affairs — National Crime
> Records Bureau (NCRB), Women Safety Division.

This repository hosts the **landing page** (Vite + React + TypeScript + Tailwind). The full research
proposal, architecture, algorithms, and evaluation plan are in
[`RAKSHAK_NET_Research_Proposal.pdf`](../RAKSHAK_NET_Research_Proposal.pdf).

---

## What RAKSHAK is — and is not

RAKSHAK is deliberately scoped. This framing is a core design principle, not a disclaimer bolted on
afterward.

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

1. **Multilingual Identity Resolution** — resolves entity mentions across scripts and spellings using
   transliteration (IndicXlit), phonetic matching, embeddings, and graph-neighborhood context. Phone,
   vehicle, account, and IMEI matches are deterministic; uncertain merges are routed to human review.
   *No facial or voice biometrics.*
2. **Temporal Knowledge Graph** — a six-layer graph (communication, financial, geospatial,
   organizational, case/event, digital/social) with cross-layer edges. Every edge is classified as
   **observed / inferred / uncertain**, timestamped, and carries full provenance plus a SHA-256
   audit hash.
3. **Evidence & Human Verification** — no output without an **Evidence Panel** tracing back to source
   documents with calibrated confidence. Entity merges, inferred relationships, and high-priority
   alerts require investigator sign-off; accept/reject decisions feed back as training signal.
4. **RakshakAI Code Security** — a security-focused `Qwen2.5-Coder-14B` fine-tune that scans the
   platform's *own* codebase for vulnerabilities (CWE detection, dependency and auth-logic review).
   Secure-by-design, **not** a runtime firewall. See [RakshakAI](#rakshakai-code-security-layer).

---

## Architecture (summary)

```
Secure Ingestion ─▶ Normalization ─▶ Multilingual NLP ─▶ Hybrid Identity Resolution
        │                                                          │
        ▼                                                          ▼
  Six-Layer Temporal Graph ─▶ Graph Analytics ─▶ Influence & Anomaly Detection
        │                                                          │
        ▼                                                          ▼
  Evidence Ranking ─▶ NL Query (retrieval-grounded) ─▶ Human Verification
                                                                   │
  Security (RakshakAI code scan · RBAC · encryption · immutable audit log) ◀┘
```

**Planned stack** (per the proposal): Next.js/React/TypeScript/Tailwind frontend · FastAPI backend ·
PostgreSQL + pgvector · Neo4j graph database · Cytoscape.js / React Flow graph visualization ·
IndicNER / IndicXlit for Indian-language NLP · RakshakAI (Qwen2.5-Coder-14B fine-tune) for code
security.

---

## RakshakAI code-security layer

RakshakAI is the secure-by-design component. It is **not** used for criminal-network analysis — its
sole job is to review the platform's code.

- **Model:** [`Muneerali199/rakshak-cwe-14b-sft-final`](https://huggingface.co/Muneerali199/rakshak-cwe-14b-sft-final)
  — LoRA/SFT adapter on `Qwen/Qwen2.5-Coder-14B-Instruct` for CWE / vulnerability detection.
- **Datasets:** [`Muneerali199` on Hugging Face](https://huggingface.co/Muneerali199/datasets) —
  `rakshak-cwe-v3-data`, `rakshak-sft-dataset`, `RakshakAI-v4-instruct`, `RakshakAI-phase-b`, and more.
- See [`docs/huggingface/MODEL_CARD.md`](docs/huggingface/MODEL_CARD.md) and
  [`docs/huggingface/DATASETS.md`](docs/huggingface/DATASETS.md).

Consistent with the proposal, RakshakAI is a **supplementary** security layer until it is benchmarked
against established static-analysis tools (Semgrep, SonarQube, Bandit).

---

## This repository — the landing page

Vite + React 19 + TypeScript + Tailwind CSS v3 (shadcn/ui components), with GSAP + Framer Motion for
the cinematic scroll experience.

```bash
# from this directory
npm install        # or pnpm install
npm run dev        # dev server → http://localhost:5173
npm run build      # tsc -b && vite build → dist/
npm run preview    # preview the production build
npm run lint       # eslint
```

**Sections** (`src/sections/`): `Hero` · `Problem` · `Solution` (the four pillars) · `VisualProof`
(analyst workbench mockup) · `Footer`.

---

## Roadmap

**36-hour MVP** — 3 synthetic sources · 2 languages (Hindi + English) · 4 entity-resolution features ·
3 graph layers · NetworkX/Cypher analytics · z-score anomaly detector · evidence panel · template NL
query · RakshakAI code scan.

**Progress** — the Python backend (see [`backend/`](backend/README.md)) has landed the first two data
phases, both stdlib-only and reproducible:
- ✅ **Synthetic benchmark generator** ([`synthgen`](backend/README.md)) — noisy FIR/CDR/FIN + ground truth.
- ✅ **Hybrid entity resolution** ([`resolve`](backend/resolve/README.md)) — the 4 MVP features
  (identifier, name, phonetic, attribute) + Devanagari transliteration; meets every paper-§23 target
  (Precision 0.998, Recall 0.999, false-merge < 0.0001) on the synthetic benchmark.

**3-month prototype**
- *Month 1* — synthetic benchmark generator ✅, ingestion pipeline, Hindi+English NER, basic entity
  resolution ✅, Neo4j schema.
- *Month 2* — Hinglish support, temporal edge annotation, community detection + centrality, evidence
  panel UI.
- *Month 3* — cross-layer edges, anomaly detectors, NL query interface, human-review workflow,
  RakshakAI integration.

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

- 📄 Research proposal: [`RAKSHAK_NET_Research_Proposal.pdf`](../RAKSHAK_NET_Research_Proposal.pdf)
- 🤖 RakshakAI model: https://huggingface.co/Muneerali199/rakshak-cwe-14b-sft-final
- 📊 Datasets: https://huggingface.co/Muneerali199/datasets

---

> **Disclaimer.** All quantitative performance claims in the proposal are *expected outcomes* pending
> evaluation on a synthetic benchmark. RAKSHAK does not predict individual criminality, determine
> guilt, or support autonomous enforcement decisions.
