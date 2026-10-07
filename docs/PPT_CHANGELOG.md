# PPT_CHANGELOG — Executable Deck-Edit Checklist (verified against the real file)

> Basis: `~/Downloads/Venom_Rakshak-ai Final (1).pdf_20260914_231401_0000.pdf`
> (latest — 14 Sep 23:14, 6 pages). Every slide below was read from THIS file, not
> guessed: text extracted + image counts per slide.
>
> This is the *what to actually change now* list. For full copy-paste slide content and
> source SVG/PNG diagrams go to `PPT_UPDATE_PACKAGE.md`. This file only tracks the gap
> between what the deck already has and our Phase 1–6 reality.

---

## LATEST — Aadhaar-verified officer auth (added 22 Sep)

Deck has warrants + HITL but **no identity story**. Add one claim + one screenshot:

1. **Slide 2 USP (or slide 5 features if space is tight)** — new bullet:
   *"DigiLocker e-KYC verified officer sessions over API Setu — every write to the
   case graph is bound to a rank-enforced identity (IO / FORENSIC / SP),
   purpose-bound consent, 8h-expiring bearer token, and a hash-chained auth ledger.
   Identity is read from the signed token, never from the client; the warrant gate
   still requires a countersigning SP (four-eyes)."*
2. **Slide 6 prototype row** — add `aadhaar-login.png` + `warrant-counter.png` (SP
   countersign step) as proof-of-life screenshots next to the workbench shot.
3. **Do NOT claim live DigiLocker / API Setu integration.** The bridge is
   `digilocker-ekyc-sim` (offline simulation, synthetic) — production = the real
   DigiLocker e-KYC API through API Setu (DGoI APIGW) under the Aadhaar Act 2016
   framework. Deck wording must say "DigiLocker e-KYC · delivered over API Setu —
   simulated on this box".

---

## LATEST — Bhashini voice channel (added 22 Sep)

Deck's "Indic NLP" line already cites AI4Bharat/Bhashini. Now it's demo-able — a
**vocal FIR intake**: officer taps *dictate* in the FIR panel and speaks Hindi;
on-device speech-to-text drops the transcript into the narrative (vetted before
ingest), and *listen* reads it back in Hindi. Add to better tell the story:

1. **Slide 5 features** (or slide 2 USP if space): *"Bhāshinī voice channel — file
   a Hindi FIR by speaking, not typing: statement → on-device STT → vetted narrative →
   graph; listen-back TTS. Production runs Bhashini (MeitY NLM) ASR/TTS over API Setu
   for 20+ Indic languages."*
2. **Slide 6 prototype row** — add `voice-fir-dictation.png` (mic toggle live in the
   FIR panel).
3. **Do NOT claim live Bhashini API.** Running bridge is `bhashini-ondevice-sim`
   (Web Speech, offline); live needs a Bhashini token. Deck wording must say
   "on-device Hindi speech on this box — production Bhashini/API Setu".

---

## LATEST — Evidence auto-resolution (added 23 Sep)

Deck's "identity resolution" fires on two typed names. Now the pitch is
**document-in, leads-out**: paste the FIR/PDF and every person in it is extracted
and scored against the case graph at once. Add to strengthen the demo:

1. **Slide 5 features (or slide 2 USP)** — *"Evidence auto-resolution — paste the
   FIR or a PDF; every person is extracted and scored against the case graph in
   one pass (name · phonetic · attribute), ambiguous rows auto-route to review."*
2. **Slide 6 prototype row** — add `evidence-autoresolve.png` (workbench rail:
   pasted FIR → per-person MATCH/REVIEW/REJECT table with confidence + engine chip).
3. **Do NOT claim neural IndicXlit in this path.** Auto-resolve reuses the same
   Hybrid resolver; the exposed engine on this box remains `builtin-rule-romanizer`
   (neural export offline). Wording: "deterministic + machine-assisted, human-review
   gated". Officer session required (`POST /api/resolve/evidence[/pdf]`, L1).

---

## 0 · Per-slide status (from the actual 14 Sep file)

| # | Slide | Content detected | Status |
| --- | --- | --- | --- |
| 1 | Title | Title "Rakshak.NET", tagline, Team Venom (4 img) | ⚠️ minor |
| 2 | Idea / Problem / USP | full text (silos, State subject, Mohd↔मोहम्द, mesh, warrants, HITL) (14 img) | ✅ strong |
| 3 | Technical approach | mostly diagram images (9 img), 30 chars of text | ⚠️ verify stack text |
| 4 | Feasibility & viability | mostly diagram images (20 img), 27 chars of text | ⚠️ captions may be missing |
| 5 | Impact & benefits | stats (58.8L · 17,798 · 1,210/day · 93.9% · repeat-offender networks line) (13 img) | ✅ good |
| 6 | References | all citations kept (9 refs incl. RakshakAI HF link) (7 img) | ⚠️ add prototype-proof strip |

---

## 1 · Slide-by-slide edits needed (exact copy-paste lines)

### SLIDE 1 — TITLE
Already has: title + tagline + Team Venom.
Add:
- **Team ID** — fill from SIH portal (still not in extract = still blank).
- Check title naming: deck says **"Rakshak.NET"** — decided deck name is **"Rakshak AI"**
  (space), repo alias RAKSHAK-NET. Pick ONE, apply on every slide.
- Optional stronger tagline below existing one: *"The UPI of criminal intelligence — a
  constitutional evidence mesh."*

### SLIDE 2 — IDEA / USP (strongest slide — only ADD 2-3 bullets, don't rework)
Missing our Phase 1/2/6 proof — add as USP bullets under Key Features:
1. *"Extracts **7 entity kinds** live from Hindi/English FIR text — person, phone,
   account, vehicle, IPC section, **organization** ('Desi Traders Pvt Ltd') and
   **Devanagari locations** ('करोल बाग मार्केट')."*
2. *"**Key-influencer score (★)** — deterministic, finds the person who bridges
   communication + financial + spatial. A lead-finder, never a verdict."*
3. *"**Repeat-involvement signal** — every suspect carries a distinct-FIR count; ≥2
   flags a history-sheet lead (live: 'Nehaa Kumaar · 3 FIRs')."*
4. *"**Lawful intake only — we never scrape.** Social / CDR / financial data arrive via
   legal channels (IT Act, BNSS, PMLA) and flow through the same pipeline."*

> Source of truth for all four: runbook Q3/Q8/Q9 + screenshots
> `repeat-offender-live.png`, `fir-ingest-live.png`.

### SLIDE 3 — TECHNICAL APPROACH (text is only 30 chars → the images carry it)
Open the actual slide images and verify, then fix on-diagram text:
- If images claim **Next.js / Neo4j / RTX-3090 / pgvector** as "*built*" → relabel to
  "**production scale-up path**". Built today: **Vite · React · TS · Tailwind + FastAPI +
  stdlib-only Python core + SQLite hash-chained ledgers**.
- If images claim **"6-layer graph"** → annotate "3 layers live (communication, financial,
  spatial), 3 planned" (same honesty rule as slide 6 reference).
- If the methodology tree is missing → drop `02-fir-to-report-pipeline.png` in
  (`app/ppt-assets/`, or regenerate with `generate_diagrams.py`).
- Add system stat line if there is room: *"142 tests, all passing, offline, seed-42."*

### SLIDE 4 — FEASIBILITY & VIABILITY (27 text chars — images only)
Verify the 20 images actually cover the 5 feasibility types + risk/mitigation pairs.
If they don't, use `04-feasibility-grid.png` (already rendered in `app/ppt-assets/`).
Add ONE caption line so the judge sees it's tested, not drawn:
- *"Live: 3-vault mesh, warrant-gated unmask, 142/142 tests, fully offline."*

### SLIDE 5 — IMPACT (stats already great)
The "repeat-offender networks" line is a good hook — turn it into OUR FEATURE:
- Replace/augment with: *"Every suspect carries their **distinct-FIR count**; ≥2 flags a
  history-sheet lead, deterministic and audit-able — officers find the REPEAT offender,
  not just the well-connected one."* → screenshot `repeat-offender-live.png`.
- Add honesty line (our differentiator): *"Every report states its own blindspots —
  source-coverage score; what the graph cannot show, it says so."*

### SLIDE 6 — REFERENCES (citations all correct — keep them)
Two additions, winner-style:
1. Soften the **"6-layer graph architecture"** citation line → "(3 live, 3 planned)" so a
   judge can't catch an overclaim next to our live graph.
2. Add a **Prototype & proof** strip: repo `github.com/Muneerali199/rakshak-agent` +
   RakshakAI HF link (already present) + one live screenshot on-slide
   (e.g. `warrant-gate-live.png` or `repeat-offender-live.png`).

---

## 2 · What NOT to touch (already correct in this file)

- Mohd ↔ मोहम्मद identity-resolution example ✅
- Mesh / "data never leaves its district" ✅
- Zero-LLM-in-serving-path + warrants + 3 ledgers ✅
- Impact numbers (58.8L FIRs, 17,798 stations, 1,210/day, 93.9%, 55 min, 29.2%) ✅
- All 9 citations incl. RakshakAI HF link ✅

## 3 · Do / Don't (hard rules for this edit pass)

**Do** — every slide ≥1 diagram; quantified proof over paragraphs; Team ID filled;
one naming choice deck-wide; add repeat-offender + 7-entity-kinds + lawful-intake bullets.
**Don't** — say "6-layer built" (3 live, 3 planned); list scale-up stack as running
stack; add a 7th slide; claim the 14B model is in the demo serving path (on-prem
advisory only); use "Next.js/Neo4j" anywhere as current.

---

## 4 · Assets ready to paste

| File | For |
| --- | --- |
| `repeat-offender-live.png` (repo root) | Slide 5 (repeat-offender proof) |
| `fir-ingest-live.png` / `warrant-gate-live.png` / `report-2-live.png` (repo root) | Slide 4/6 proof |
| `app/ppt-assets/01..08-*.png` | Slide 2/3/4/6 diagram fills |
| `app/ppt-assets/technical/*.svg|png` | Slide 3 two-up (methodology + stack) |
| regenerate anytime | `backend/.venv/bin/python ppt-assets/generate_diagrams.py` |

---

## 5 · GRAND FINALE AUDIT — `Venom_Rakshak-ai Grand_Final round_(1).pdf` (17 Sep 21:52)

Verified slide-by-slide: PDF text layer + OCR of every embedded diagram image.
**Score: 7.5/10 → ~9.5 with the 8 fixes below.**

### Must-fix (credibility — do before uploading)

1. **Slide 1: Team ID is blank** (`Team ID -`). Fill from the SIH portal. Every winner had it.
2. **Slide 4: test count is wrong AND self-contradictory** — text layer says
   "141 tests, all passing", the feasibility-grid image says "119/119 tests passing".
   Actual = **142**. Make both read `142/142 tests, all passing`.
3. **Slide 2: the 7-entity-kinds line is sitting under PROBLEM OVERVIEW** — it's a
   feature ("Extracts 7 entity kinds live…"). Move it to KEY FEATURES as a 5th bullet.
4. **Slide 6: "Foundation for our 6-layer graph architecture"** contradicts slide 3's
   diagram ("communication · financial · spatial" = 3). Change to
   "(3 live — communication · financial · spatial; 3 planned)".

### Should-add (grand-finale differentiators, currently absent)

5. **Slide 5: repeat-offender feature** (deck only has the NCRB hook) — add:
   *"Every suspect carries a distinct-FIR count; ≥2 flags a history-sheet lead
   (live: Nehaa Kumaar · 3 FIRs) — deterministic, audit-able."* + `repeat-offender-live.png`.
6. **Slide 2 USP: key-influencer (★)** — word "influence" appears 0× in the whole deck.
   Add: *"Key-influencer score (★) — the person bridging communication + financial +
   spatial. A lead-finder, never a verdict."*
7. **Slide 4 data-availability: lawful intake** — add: *"Lawful intake only — we never
   scrape: social / CDR / financial via IT Act / BNSS / PMLA channels, same pipeline."*
8. **Slide 6: GitHub repo link** next to the HF link:
   `github.com/Muneerali199/rakshak-agent`.

### Verify visually (OCR couldn't read)

9. Slide 1 title graphic — OCR reads "SIH **2022**"; confirm it says **2026**.
10. Slide 3 bottom strip (`s3_1`, below the flowchart) — unreadable even with
    preprocessing; check it manually. Also ensure today's stack (Vite · React · FastAPI ·
    stdlib core · SQLite) appears somewhere on slide 3 — the ten-steps image only names
    "Neo4j · pgvector **scale-up**" (correctly labeled, but the *current* stack must be
    visible too).
11. Naming: deck uses **RAKSHAK.NET** consistently (headline + diagrams + workbench
    screenshot). Decision doc said "Rakshak AI". Keep RAKSHAK.NET (matches repo alias
    RAKSHAK-NET) or change everywhere — just one choice.

### Confirmed good — don't touch

- 6 slides = official format ✓ · problem/solution/USP/features structure ✓
- Mesh, warrant gate, zero-LLM-in-serving-path, 3 ledgers, HITL ✓
- 7-entity-kinds line now present (only misplaced) ✓
- Slide 4 blindspot / no-fake-sources honesty block ✓
- Feasibility grid = 5 types + risks→mitigations (winner pattern) ✓
- Impact stats: 58.8L · 17,798 · 1,210/day · 55 min · 29.2% ✓
- Prototype screenshots on slide 6 (workbench) + all 9 references incl. HF link ✓
- Neo4j · pgvector correctly labeled "scale-up path", not current stack ✓