# RAKSHAK-NET — Executable Hackathon Plan (SIH26189)

> Companion to the 26-page research proposal. This is the **build sheet**, not more theory:
> completed peer-review rebuttals, exact API contracts, the Investigator Workbench UI spec, and
> the 10-minute finale script. Scoped to the **36-hour MVP** (3 sources, 2 languages, 4-of-8
> resolution features, 3-of-6 graph layers, z-score anomaly, evidence panel, RakshakAI scan).

---

## 1. Expert Review — completed rebuttals

### Criticism 3: Arbitrary Weighting vs. Calibrated Influence
**Reviewer Concern:** Calibration via expert rankings is prone to cognitive bias, and uniform weights are arbitrary.

**Correction:** Weights `w_k` are initially uniform (`w_k = 1/K`) so no factor dominates without justification.
When expert rankings become available (pilot, Months 4–6), weights are calibrated via **constrained linear
regression maximizing Kendall's τ** between model output and an expert-ranked validation set, under
`Σ w_k = 1, w_k ≥ 0` (keeps the score a convex, interpretable blend). To counter cognitive bias, expert labels
are collected **blind and independently** (reviewers never see the model score first), inter-annotator agreement
is reported (Fleiss' κ), and disputed pairs go to a third adjudicator. Absent sufficient expert data, uniform
weights are used **with explicit UI disclosure** that the ranking is uncalibrated. A **±20% sensitivity analysis**
per `w_k` measures ranking stability; if the top-k suspect set is unstable, the numeric score is suppressed in
favor of a qualitative "requires review" flag — so automation bias can't be induced by a number the data doesn't
justify.

### Criticism 4: Hackathon Demo Feasibility *(new)*
**Reviewer Concern:** The full architecture cannot be genuinely demonstrated in 36 hours; a live demo risks either
faking outputs or collapsing under real-time compute on stage.

**Correction:** De-risked along four axes, with the reduction made **explicit**:
1. **Scope contract, not scope creep.** Demo runs the MVP subset only (3 sources, 2 languages, 4-of-8 features,
   3-of-6 layers, z-score anomaly). Every deferred piece is labeled "Roadmap →" in the UI.
2. **Determinism as safety net.** Whole pipeline is seeded and stdlib-only (`synthgen --seed 42`, `resolve`).
   The dataset is committed and its **SHA-256 manifest shown on screen** — provably not hard-coded; re-runnable
   to a byte-identical graph.
3. **Pre-warm, then compute live.** Heavy artifacts (RakshakAI 14B on vLLM, indices) load *before* the demo; the
   inference the jury watches runs on the warm service. If the GPU node is unavailable, RakshakAI falls back to a
   **recorded-but-real** scan against the same commit, disclosed as such.
4. **Honest fallback.** All quantitative claims are labeled *preliminary on synthetic data* (Criticism 2). The demo
   proves **capability and provenance**, not field accuracy — the one claim a 36-hour build defends under fire.

---

## 2. FastAPI backend schemas

Grounded in Algorithm 2 (Hybrid Identity Resolution), Algorithm 3 (Evidence-Weighted Edge Construction), and
Algorithm 7 (Evidence-Grounded Query). **Live in code:** [`backend/api/schemas.py`](../backend/api/schemas.py)
and [`backend/api/main.py`](../backend/api/main.py). `/api/resolve`'s feature breakdown is the real output of
`resolve.features.score_pair()`.

### Endpoints
| Method + path | Input | Output |
| --- | --- | --- |
| `POST /api/resolve` | two raw entity strings (+ optional ids/attrs) | decision, confidence, 4-feature breakdown, normalized forms |
| `GET /api/graph/subgraph` | entity id (+ depth, layers) | nodes, edges, edge_types, layer_assignments |
| `GET /api/evidence/{edge_id}` | edge id | source documents, timestamps, SHA-256 hash, confidence |

### Mock payload — `POST /api/resolve` for "Mohammad Arif / Mohd Arif"
```json
// REQUEST
{ "name_a": "Mohammad Arif", "name_b": "Mohd Arif",
  "address_a": "H.No 76, Aminabad, Lucknow", "address_b": "Aminabad Rd, Lucknow",
  "age_a": 34, "age_b": 35 }

// RESPONSE 200
{
  "decision": "MATCH",
  "confidence": 0.94,
  "calibrated": false,
  "weights": { "name": 0.55, "phonetic": 0.20, "attribute": 0.25 },
  "features": { "identifier": null, "name": 0.97, "phonetic": 1.0, "attribute": 0.83 },
  "normalized_a": "arif mohammad",
  "normalized_b": "arif mohammad",
  "veto_reason": null,
  "route_to_review": false
}
```

### Mock payload — `GET /api/graph/subgraph?entity_id=P0003`
```json
{
  "root": "P0003",
  "nodes": [
    { "id": "P0003", "label": "Mohammad Arif", "type": "PERSON",
      "layers": ["communication","financial","spatial"], "risk": 0.71,
      "meta": { "district": "Lucknow", "aliases": ["Mohd Arif","मोहम्मद आरिफ़"] } },
    { "id": "P0017", "label": "Imran Khan", "type": "PERSON", "layers": ["communication"], "risk": 0.44 },
    { "id": "P0009", "label": "Salman Sheikh", "type": "PERSON", "layers": ["financial"], "risk": 0.38 },
    { "id": "L0002", "label": "Aminabad, Lucknow", "type": "LOCATION", "layers": ["spatial"], "risk": null }
  ],
  "edges": [
    { "id": "E10231", "source": "P0003", "target": "P0017", "type": "CONTACTED", "layer": "communication",
      "creation_method": "EXTRACTED", "confidence": 1.0, "timestamp": "2026-02-12T10:57:16",
      "provenance": "CDR-000001", "audit_hash": "7f8b2614…a1", "review_status": "ACCEPTED" },
    { "id": "E10244", "source": "P0003", "target": "P0009", "type": "TRANSFERRED_TO", "layer": "financial",
      "creation_method": "EXTRACTED", "confidence": 1.0, "timestamp": "2026-01-10T02:04:30",
      "provenance": "FIN-000001", "audit_hash": "c1ff1ca5…9d", "review_status": "ACCEPTED" },
    { "id": "E10290", "source": "P0017", "target": "P0009", "type": "ASSOCIATE_OF", "layer": "communication",
      "creation_method": "INFERRED", "confidence": 0.62, "timestamp": "2026-02-20T00:00:00",
      "provenance": "ANALYTICS/co-mention", "audit_hash": "3a9e77b0…4c", "review_status": "PENDING" }
  ],
  "layer_assignments": {
    "communication": ["P0003","P0017","P0009"],
    "financial": ["P0003","P0009"],
    "spatial": ["P0003","L0002"]
  },
  "stats": { "nodes": 4, "edges": 3, "inferred": 1 }
}
```

### Mock payload — `GET /api/evidence/E10231`
```json
{
  "edge_id": "E10231",
  "claim": "Mohammad Arif (P0003) CONTACTED Imran Khan (P0017)",
  "confidence": 1.0,
  "creation_method": "EXTRACTED",
  "audit_hash": "7f8b2614009708a7e0920082dd0e36864408963606b0a135eba6d1392ff57003",
  "hash_verified": true,
  "source_documents": [
    { "doc_id": "CDR-000001", "doc_type": "CDR", "timestamp": "2026-02-12T10:57:16",
      "snippet": "caller +917321819600 → receiver +918044997278, 63s, tower Dadar, Mumbai",
      "highlight_span": [7, 20], "language": null },
    { "doc_id": "FIR-2026-0001", "doc_type": "FIR", "timestamp": "2026-03-16",
      "snippet": "…complainant मोहम्मद आरिफ़ … accused was contacted on +918044997278…",
      "highlight_span": [13, 27], "language": "hi-en" }
  ],
  "review_status": "ACCEPTED",
  "reviewer_actions": ["ACCEPT", "REJECT", "MODIFY"]
}
```

---

## 3. Investigator Workbench UI spec

**Stack:** Next.js/React + Tailwind + React Flow · dark control-room theme (`bg-[#050505]`, `zinc-200` text,
`zinc-800` 1px dividers). Three fixed panes, full viewport height; top bar `h-14` (logo · case selector · global
search · amber "uncalibrated" pill).

```
┌── LEFT 320px ──┬──────── CENTER flex-1 ─────────┬── RIGHT 400px ──┐
│  QUERY RAIL    │   GRAPH CANVAS (React Flow)     │ EVIDENCE PANEL  │
│  border-r      │   3 horizontal layer lanes      │ border-l        │
└────────────────┴────────────────────────────────┴─────────────────┘
```

### Left — Query Rail (`w-80 border-r border-zinc-800 p-4 space-y-6`)
- **Entity search** with typeahead (calls `/api/resolve` for fuzzy suggestions); shows alias chips (`Mohd Arif`, `मोहम्मद आरिफ़`).
- **Layer toggles** with swatches: 🔵 Communication · 🟢 Financial · 🟠 Spatial.
- **Time scrubber** — dual-handle range over `[start, start+days]`; drives temporal play.
- **Confidence floor** slider (default `0.5` = θ_low); hides weaker edges.
- **Edge-type filter** checkboxes; **"Show inferred"** switch (off by default — reveal on stage).
- **Anomaly list** — top-N z-score entities, click to focus-center.

### Center — React Flow canvas
- **Swimlanes:** three horizontal bands (Communication / Financial / Spatial). `node.y = laneIndex*260`, `x` via dagre within lane. Faint lane backgrounds (`bg-blue-500/5`, `bg-emerald-500/5`, `bg-amber-500/5`) with left-edge labels.
- **Nodes** — `bg-zinc-900 border border-zinc-700 rounded-xl`, avatar + name + district. `risk > 0.6` → `ring-2 ring-red-500 animate-pulse`. Multi-lane hubs get a white halo.
- **Edge encoding (the core contract):**

| | Observed (`EXTRACTED`) | Inferred (`INFERRED`) |
| --- | --- | --- |
| Stroke | **solid** | **dashed** (`6 4`) |
| Color | layer color (🔵`#3b82f6`/🟢`#10b981`/🟠`#f59e0b`) | **grey** `#71717a` |
| Width | `2px` | `1.5px` |
| Opacity | `1.0` | `0.4 + 0.6·confidence` |
| Label | type+time on hover | `inferred · 0.62` always |
| Animated | no | dots flow during temporal play |

- Click node → expand depth-1 subgraph. Click **edge → open Evidence panel**. MiniMap + Controls.

### Right — Evidence Panel (`w-100 border-l border-zinc-800 flex flex-col`)
```
┌ EVIDENCE ───────────────────────── ✕ ┐
│ Mohd Arif ─CONTACTED▶ Imran Khan       │  claim + layer-color pill
│ 🔵 Communication · Observed            │
├────────────────────────────────────────┤
│ CONFIDENCE ▓▓▓▓▓▓▓▓▓▓ 1.00  uncalibrated│
├────────────────────────────────────────┤
│ PROVENANCE                              │
│ audit (SHA-256) 7f8b2614…ff57003 [copy] │  mono, truncated middle
│                          ✓ verified     │  green if hash_verified, else ⚠ TAMPERED
│ SOURCE 1 · CDR-000001 · 2026-02-12      │
│  caller +91732…600 → +91804…278  63s    │  mono card, highlight_span in amber/20
│ SOURCE 2 · FIR-2026-0001 · hi-en        │
│  …complainant मोहम्मद आरिफ़ reported…   │  Devanagari native, matched span marked
├────────────────────────────────────────┤
│ [ ✓ Accept ]  [ ✕ Reject ]  [ ✎ Modify ]│  HITL → POST /api/review (Algorithm 8)
└────────────────────────────────────────┘
```
- **SHA-256:** monospace, truncated middle, full value in tooltip + copy button; green `✓ verified` when server recomputed `SHA256(edge.to_json())` matches (Algorithm 3); red `⚠ TAMPERED` on mismatch.
- **FIR snippet:** `bg-zinc-900 rounded-md p-3 font-mono`; `highlight_span` wrapped in `<mark class="bg-amber-400/20">`; Devanagari native + `hi-en` tag.
- **Confidence:** read-only bar for the model score; an interactive slider appears only for `PENDING` `INFERRED` edges (feeds `MODIFY`).
- **Accept/Reject/Modify:** emerald / red / zinc → `POST /api/review`; optimistic UI flips `review_status` (accepted inferred edge turns **solid**; rejected fades). Visible payoff of Algorithm 8.

---

## 4. The 10-minute SIH demo script

**Cast:** Presenter (narrates + drives UI), Engineer (terminal). **Pre-warmed:** graph loaded, RakshakAI on vLLM up, seed-42 data committed. Split screen: Workbench + terminal.

**[0:00–1:00] Cold open.** "An investigator has a phone dump, a stack of FIRs, a bank statement. The same man is written five ways — Mohammad, Mohd, मोहम्मद. Today this takes weeks. RAKSHAK-NET does it in seconds — and shows its work. Watch."

**[1:00–2:30] Step 1 — Ingest.** Drag `fir.csv` + `cdr.csv`. Terminal: `ingested 40 FIR · 300 CDR · 120 FIN`. "Synthetic, seed-42, reproducible. Note the manifest hash `7f8b2614…` — regenerate and you get the same hash. **Nothing is hard-coded.**"

**[2:30–4:00] Step 2 — Identity Resolution reveal.** Point at Hindi FIR `…शिकायतकर्ता मोहम्मद आरिफ़ ने…`. "NLP extracts मोहम्मद आरिफ़. The English CDR has Mohd Arif. Same person?" Click **Resolve** → bars animate: **Name 0.97 · Phonetic 1.0 · Address 0.83 → 0.94 MATCH**. "Transliteration, Double-Metaphone, address overlap. And it says **uncalibrated** — we never fake precision. A lead, not a verdict."

**[4:00–5:30] Step 3 — Community forms.** Hit time-scrubber **play**. Nodes fly into 3 lanes (calls/money/places), edges draw over time; a cluster tightens; one node **pulses red**. "A community emerged. Mohammad Arif is a **cross-layer hub** — calls, money, *and* a recurring location. The z-score flagged him. No human drew this — the evidence did."

**[5:30–7:00] Step 4 — Evidence & provenance.** "Can I trust it?" Click the solid blue edge Arif→Imran. Panel slides in. "Every edge traces to source: the **CDR row**, the **Hindi FIR snippet** with the matched span highlighted, the timestamp — and the **SHA-256 audit hash `7f8b2614…`, ✓ verified live**. Tamper-evident provenance on every claim." Flip **Show inferred** → dashed grey edges. "Solid blue = observed fact. Dashed grey = a hypothesis to confirm." Click **Accept** → it turns solid. "Human-in-the-loop, and that decision is itself logged and hashed."

**[7:00–9:00] Step 5 — The RakshakAI twist.** Switch to terminal, open our FastAPI file with `f"SELECT * FROM citizens WHERE id={id}"`. "This is *our own* code. A police platform is the highest-value target in the state — so we turned our security AI on **ourselves**." Run `rakshak scan api/routes.py`:
```
⚠ CWE-89  SQL Injection · api/routes.py:42 · CRITICAL
  f-string interpolates untrusted `id` into SQL.
  Fix → db.execute("… WHERE id=%s", (id,))
```
Slowly: **"Before we catch the criminals, we must ensure our own systems cannot be breached."** "Air-gapped, on-premise. The platform that guards the data guards itself."

**[9:00–10:00] Close.** "In ten minutes: fragmented multilingual records → a resolved, evidence-grounded, self-auditing intelligence graph. Built in 36 hours, reproducible from seed 42, honest about every number. We don't ask you to trust the AI — **we show you the evidence.**"

**Q&A landmines:** *Real data?* → synthetic, and that's a feature (C2/C4). *Accuracy?* → preliminary, uncalibrated, sensitivity-tested (C3). *Blockchain?* → hash-chained append-only log = equivalent tamper-evidence, better privacy (C4-blockchain).
