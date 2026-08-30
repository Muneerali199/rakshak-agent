# RAKSHAK-NET — Complete SIH 2026 PPT Update Package

>Everything needed to rebuild `Venom_Rakshak-ai.pdf` into a winner-pattern deck:
>slide-by-slide copy-paste content, which generated diagram goes where, and speaker notes.
>
>**Benchmarked against two SIH 2025 winning decks** (`sih winner ppt 2025.pdf` — Raksha-Setu,
>PS 25184 and `sih winning ppt.pdf` — EcoWipe, PS 25070) + the official `SIH2026-IDEA-Presentation-Format`.

---

## 0 · What the winners do (the selection pattern)

Studied end-to-end. Both winning decks follow the official 6-slide template and share these traits:

| Winning trait | Raksha-Setu (winner 1) | EcoWipe (winner 2) | Arpit's deck today |
| --- | --- | --- | --- |
| Team ID on title slide | ✅ filled (72808) | ✅ filled (53476) | ❌ **blank** |
| Slide 2 carries an **architecture diagram** | ✅ hierarchical diagram | ✅ architecture graphic | ❌ text only |
| Slide 3 carries a **big flowchart** | ✅ onboarding decision tree | ✅ 3-mode flow | ❌ none |
| Slide 4 feasibility split into **5–6 types** + risks/mitigations grid | ✅ 6 types + 4 risk/mitigation pairs | ✅ 4+4 types + risks | ❌ **EMPTY** |
| Slide 5 impact with **hard numbers** | ✅ 5 features + 5 impacts + 5 benefits | ✅ ₹50,000 Cr · 25,000+ jobs · 5L tonnes | ❌ **EMPTY** |
| Slide 6 shows **prototype screenshots** + demo links + competitor comparison | ✅ app screenshots | ✅ demo video + Figma + "existing vs ours" | ❌ references only |
| Template rule (slide 7 of the format) | *"avoid paragraphs — use points / diagrams / infographics / pictures"* | same | ⚠️ text-heavy where not empty |

**Conclusion:** our content is stronger than both winners (working mesh, three ledgers, warrant
gate — they had mockups), but the deck *shows* none of it. The fix is structural: put the proof
on the slides as diagrams + screenshots, fill the two empty slides, correct the stack claims.

---

## 1 · Slide inventory — what changes

| # | Slide | Status | Action |
| --- | --- | --- | --- |
| 1 | Title | OK | fill Team ID, add tagline |
| 2 | Idea | thin | add diagram `01` (or `07`), soften "6-layer" claim |
| 3 | Technical approach | wrong stack | correct stack, add flowchart `02` |
| 4 | Feasibility & viability | **empty** | full-bleed `04` + inset `warrant-gate-live.png` |
| 5 | Impact & benefits | **empty** | full-bleed `05` + inset `report-2-live.png` |
| 6 | References | good | keep citations, add `06` comparison + prototype screenshots + repo/demo links |

---

## 2 · Generated assets (in `app/ppt-assets/`)

All 200 DPI, brand-themed (`#0a0f1c` · cyan/purple/emerald), with a
`RAKSHAK-NET · Team Venom · SIH 2026 (SIH26189)` footer baked in.

| File | Shows | Put on |
| --- | --- | --- |
| `01-mesh-architecture.png` | Gateway ↔ 3 vaults, "queries travel, data stays" | **Slide 2** |
| `02-fir-to-report-pipeline.png` | 7-step FIR→evidence-chain flowchart | **Slide 3** |
| `03-warrant-gate-sequence.png` | IO → gate → SP+ countersign → unmask → ledger | **Slide 4** (alt) |
| `04-feasibility-grid.png` | 5 feasibility types + risks→mitigations | **Slide 4** |
| `05-impact-stats.png` | 58L+ FIRs · 16,000+ stations · days→seconds · 3 ledgers · 0 LLM | **Slide 5** |
| `06-comparison.png` | CCTNS / foreign SaaS / IJOP vs RAKSHAK-NET | **Slide 6** |
| `07-graph-layers.png` | 6-layer temporal graph (3 live, 3 planned) | Slide 2 or 3 |
| `08-three-guarantees.png` | Never lies / never tampers / never profiles | Slide 2 or 5 |

Mermaid sources for the three flow diagrams are in `ppt-assets/mermaid/*.mmd`
(editable at mermaid.live). Regenerate PNGs any time:
`backend/.venv/bin/python ppt-assets/generate_diagrams.py`

Live screenshots already in repo root: `mesh-fir-live.png` · `warrant-gate-live.png` ·
`report-2-live.png` · `fir-ingest-live.png` · `query-live.png`.

---

## 3 · Slide-by-slide copy-paste content

### SLIDE 1 — TITLE PAGE
> Keep Arpit's layout. Two edits:

```
SMART INDIA HACKATHON 2026
Problem Statement ID   – SIH26189
Problem Statement Title – AI-Powered Criminal Network Analysis System
Theme                  – Blockchain & Cybersecurity
PS Category            – Software
Team ID                – [FILL FROM SIH PORTAL]        ← every winner had this filled
Team Name              – Team Venom
Product                – RAKSHAK-NET
Tagline                – The UPI of criminal intelligence — a constitutional evidence mesh
```

**Speaker note:** *"Policing is a State subject — a national crime database is legally
impossible. So we did what UPI did for banks and DEPA did for data sharing."*

---

### SLIDE 2 — IDEA TITLE
**Layout:** text left, **`01-mesh-architecture.png` right** (or `07-graph-layers.png` as alternate).

**Proposed Solution (paste-ready):**
- RAKSHAK-NET fuses fragmented FIRs, CDRs and financial trails into one canonical,
  CCTNS-shaped schema — without centralizing a single record.
- Resolves identities across Hindi / English / Hinglish — `Mohd ↔ Mohamad ↔ मोहम्मद`
  — with hybrid 4-feature scoring (live: MATCH at 1.00 confidence).
- Builds a multi-layer temporal knowledge graph (Communication / Financial / Spatial
  seeded and live; 3 more layers planned) where every edge is timestamped,
  source-cited and SHA-256 hashed.
- District Vault Mesh: signed queries travel between district vaults; FIR data never
  leaves its district — the UPI pattern, applied to policing.
- Warrant Gate: protected (victim) data unmasks only behind a dual-signed, scoped,
  expiring warrant — the DEPA consent artifact for police.

**Innovation & uniqueness:**
- Only entry that is constitutional BY DESIGN (Seventh Schedule) — mesh, not centralization.
- Anti-hallucination by construction: retrieval-only answers, unknowns refused, every
  claim cites its edges. Zero LLM in the serving path.
- Three tamper-evident hash-chained ledgers: human reviews, warrant events, mesh exchanges.
- RakshakAI (14B, published on Hugging Face) secures the platform's own code.

**Speaker note:** point at the diagram — *"The gateway is the NPCI switch. It stores
receipts, never case data. Delhi, Mumbai, Jaipur each keep their own graph."*

---

### SLIDE 3 — TECHNICAL APPROACH
**Layout:** **`02-fir-to-report-pipeline.png` full-width on top**, corrected stack below.

**Stack — CORRECTED (must replace Next.js/Neo4j claims):**

| Layer | Built & running today | Production scale-up path |
| --- | --- | --- |
| Frontend | Vite · React 19 · TypeScript · Tailwind | same |
| Backend API | FastAPI · Pydantic · Uvicorn | same |
| Core intelligence | **stdlib-only Python** — deterministic, seed-42, air-gapped | same |
| Graph & ledgers | in-memory temporal graph + **SQLite hash-chained ledgers** | Neo4j cluster |
| Identity / transliteration | hybrid scorer + **AI4Bharat IndicXlit** adapter | IndicNER · IndicTrans |
| Security model | RakshakAI — Qwen2.5-Coder-14B LoRA (published, HF) | vLLM on NIC GPU |
| Deployment | single script, 3 vaults + gateway, fully offline | NIC MeghRaj |

**Methodology:** the pipeline diagram is the methodology — FIR → extract → resolve →
mesh query → graph+ledger → warrant gate → Report 2.0.

**Speaker note:** *"No foreign API in the serving path. The stack a judge can audit is
the stack running on this laptop — 119 tests, all passing."*

---

### SLIDE 4 — FEASIBILITY AND VIABILITY  *(currently empty — build it)*
**Layout:** **`04-feasibility-grid.png` as the slide body** (it already contains the 5
feasibility types + risks→mitigations grid). Inset `warrant-gate-live.png` (top-right,
~30% width) as the working-prototype proof, or use `03-warrant-gate-sequence.png` instead
if you want a pure-diagram slide.

**One-line caption under the screenshot:**
*"Live: warrant-gated unmasking — dual-signed, scoped, expiring, ledgered."*

**If the template demands text too, add these three lines only:**
- Feasibility proven by a running system: 119/119 tests, 3-vault live mesh, offline.
- Legality is the moat: no central FIR store → deployable where centralized rivals are not.
- Risks are named and mitigated in code (HMAC→NIC PKI, synthetic→CCTNS mapping, human-in-loop).

---

### SLIDE 5 — IMPACT AND BENEFITS  *(currently empty — build it)*
**Layout:** **`05-impact-stats.png` as the slide body** (5 stat cards + social / economic /
governance bands). Inset `report-2-live.png` (~30% width) as the delivered-output proof.

**One-line caption:**
*"Report 2.0 — the court-ready evidence chain, with jurisdiction chain, protected-access
log and a blindspot honesty score."*

**Target-audience framing (say it):**
- NCRB Women Safety Division: stalking-escalation detection flags the pattern *before*
  the next FIR; victims are shielded, never profiled.
- Investigating officers: days of cross-district correspondence collapse to one signed query.
- Courts & auditors: every claim traceable to a hash-verified source row.

---

### SLIDE 6 — RESEARCH AND REFERENCES
**Keep all of Arpit's citations** (they are accurate: TGN, multilayer networks, Christen,
COMI-LINGUA, AI4Bharat/Bhashini, GNNExplainer, HITL, RakshakAI HF link).

**Add a bottom strip — "Prototype & proof" (winners both did this):**
- **`06-comparison.png`** (existing solutions vs RAKSHAK-NET) — left half.
- Right half, link card:
  - Working repo: `github.com/Muneerali199/rakshak-agent`
  - RakshakAI model: `huggingface.co/Muneerali199/rakshak-cwe-14b-sft-final`
  - Live demo script: `scripts/run_mesh.sh` (gateway + 3 vaults + workbench, offline)
  - Screenshots: mesh-fir-live · warrant-gate-live · report-2-live

---

## 4 · Do / Don't (from the winner decks)

**Do**
- Fill Team ID before upload (both winners had it).
- One diagram per slide minimum — the template explicitly asks for diagrams over paragraphs.
- Use the quantified stats on slide 5 — winners quantified everything.
- Keep the Mohd ↔ मोहम्मद example — it is our most concrete, demo-able line.

**Don't**
- Claim "6-layer graph" as built (3 are live, 3 planned — the diagram says it honestly).
- List Next.js / Neo4j / pgvector / RTX-3090 as the running stack (it is the scale-up path).
- Add a 7th slide (format allows max 6 including title).
- Paragraphs. Points, diagrams, pictures only.

---

## 5 · Asset regeneration

```bash
cd app
backend/.venv/bin/python ppt-assets/generate_diagrams.py   # re-renders all 8 PNGs
```

Edit text/colors in `ppt-assets/generate_diagrams.py` (palette constants at top), or
hand the `ppt-assets/mermaid/*.mmd` files to anyone with mermaid.live for quick restyles.
