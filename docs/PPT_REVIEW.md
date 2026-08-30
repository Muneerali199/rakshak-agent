# Arpit's SIH Deck — Review & Update Plan

>Target: `app/Venom_Rakshak-ai.pdf` (6-page SIH 2026 submission, PS **SIH26189**, Team **Venom**).
>This tells you **exactly** what to fix and supplies the screenshots for the two empty slides.

---

## The single biggest problem

**Slides 4 (Feasibility) and 5 (Impact) are EMPTY** — title-only placeholders. In an SIH idea
submission these are the two slides that carry the pitch. They should be **images, not walls of
text** (per your instruction), using the live screenshots already captured in the repo root.

---

## Slide-by-slide

### Slide 1 — Title ✅ mostly fine
- Fill **Team ID** (blank) before submitting.
- Optional: append "Team Venom — RAKSHAK-NET" so the product name survives the team name.
- Consider a tagline: **"The UPI of criminal intelligence — a constitutional evidence mesh."**

### Slide 2 — Idea (text, OK but thin on proof)
Keep the 4 bullets, but **replace "6-layer Temporal Knowledge Graph" claim** — the built system has
**3 seeded layers** (Communication, Financial, Spatial) with 3 more planned. Saying "6-layer" when
only 3 are built is a fact-check risk under a judge's question. Say *"multi-layer temporal graph
(communication / financial / spatial seeded; 3 more planned)".*
- The `Mohd ↔ मोहम्मद` example is correct and is your strongest line — keep it, and it is **live-verifiable** (`POST /api/resolve` returns MATCH 1.00).

### Slide 3 — Technical approach ⚠️ **does not match the build**
Everything under "Languages / Graph / Databases / Hardware" describes the **proposal target**, not
the working demo:

| PPT says | Actually built | Fix |
| --- | --- | --- |
| Frontend **Next.js** | **Vite + React 19 + TypeScript + Tailwind** | correct it |
| Graph **Neo4j / Cypher** | **stdlib Python graph (+SQLite persist)** | correct it |
| Relational **PostgreSQL/pgvector** | **SQLite** (stdlib) | correct it |
| GPU **RTX 3090/4090, 24GB** | stdlib CPU pipeline, air-gapped | scope as *target* |
| AI4Bharat · Bhashini · IndicXlit | ✅ matches (`resolve/indic_xlit.py`) | keep |
| Qwen2.5-Coder 14B + LoRA | ✅ matches (RakshakAI, HF) | keep |

**Recommended reframe:** distinguish **"Built now (offline demo)"** from **"Production scale-up"**.
Present the *working* stack, then note Neo4j/pgvector/vLLM as the scale-up path for full rollout —
honest, and it turns a mismatch into a roadmap.

### Slide 4 — Feasibility & Viability (EMPTY → put an image)
> Replace the empty slide with **the live mesh / warrant demonstration**, not prose.

**Image:** `warrant-gate-live.png` (and/or `mesh-fir-live.png`).
**One-line caption:** *"District Vault Mesh (UPI-style switch): signed queries travel, FIR data never
leaves its district, every exchange hash-chained. Warrant Gate: scoped, expiring, dual-signed (SP+)
access — the DEPA consent artifact for police."*
**Backup bullets (1 line each) if space allows:** 119/119 tests · stdlib-only core runs air-gapped
offline · three tamper-evident ledgers (`/api/reviews/verify`, `/api/warrants/verify`, `/mesh/verify`
→ all `ok:true`) · policy/deployment host = NIC MeghRaj.

### Slide 5 — Impact & Benefits (EMPTY → put an image)
> Replace the empty slide with **the delivered output — the court-ready evidence chain**.

**Image:** `report-2-live.png` (and/or `mesh-fir-live.png`).
**One-line caption:** *"Report 2.0 — a court-ready evidence chain per entity: hash-verified source
rows + review log + jurisdiction chain (signed mesh exchanges) + protected-data access log.
Blindspot honesty layer states what the report cannot establish."*
**Backup bullets (1 line each):** Women-Safety focused (escalation trajectory → CRITICAL, victim
shield, repeat-offender networks) · NCRB scheme-mapped to CCTNS · no foreign cloud, no LLM in the
serving path → no hallucination by construction.

### Slide 6 — References ✅ fine
Accurate and strong. Keep. (Each cited paper maps to a real module: TGN→temporal edges,
multilayer→6/3-layer graph, COMI-LINGUA→Hinglish NER, GNNExplainer→evidence traceability.)
Minor: the 6-layer reference is claim-consistent only if Slide 2 is softened per above.

---

## Suggested new slide order (if you have a blank to play with)

1. Title
2. The **legal trap + the UPI/DEPA answer** (why a central DB is impossible; your architecture is the deployable one)
3. Idea (identity resolution + graph)
4. **Live demo — mesh + warrant gate** (image)
5. **Live demo — Report 2.0 + blindspot** (image)
6. Technical approach — built vs scale-up
7. Feasibility & impact (image, merged)
8. References

---

## Assets available (repo root, `*.png`, already captured live)

| File | Shows |
| --- | --- |
| `warrant-gate-live.png` | dual-signed warrant modal + unmask banner |
| `mesh-fir-live.png` | FIR ingest + district vault mesh receipts |
| `report-2-live.png` | Report 2.0 evidence chain |
| `fir-ingest-live.png` | entity highlight in FIR text |
| `query-live.png` | grounded NL query |
| `scanner-live.png` / `scanner-final.png` | RakshakAI code scan |

---

## If you want it generated for you

I can produce an **updated `Venom_Rakshak-ai_UPDATED.pdf`** with:
- corrected Slide 3 (Vite/React 19 + stdlib + SQLite, with Neo4j/pgvector marked "scale-up"),
- Slides 4 & 5 built as **full-bleed screenshots** + one-line captions,
- a fresh title/fill-in for Team ID.

Just confirm and I'll build it.
