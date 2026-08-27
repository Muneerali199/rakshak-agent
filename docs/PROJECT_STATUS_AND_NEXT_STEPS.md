# RAKSHAK-NET — Project Status & Next Steps

_Last reviewed: 2026-08-26. Authoritative spec: `~/Desktop/RAKSHAK_NET_Research_Proposal.pdf`_
_(the repo `paper/` is a **stale SIH-2024 version** — do not treat it as the spec)._

> **2026-08-26 — SIH-winning layer shipped (see `docs/NEXT_STEPS_PLAN.md`).**
> Three guarantees now enforced in code: (1) **never lies** — grounded query refuses
> unknowns; (2) **never forgets/tampers** — review audit log is now a **hash-chained
> evidence ledger** (`prev_hash`/`chain_hash` per record, `GET /api/reviews/verify`
> names the first broken link; 6 new ledger tests incl. live tamper detection);
> (3) **never profiles the innocent** — **victim-shield**: complainant-only clusters
> are tagged `role: "victim"` at graph build, NL queries on them are masked with zero
> citations, path queries through them refuse, and evidence panels redact their
> identity (`victim_shield: true`; 6 new tests). Workbench: **auto-loads the lead
> circular-flow anomaly** on startup, **time-travel slider** (end-date scrubber over
> `?start=&end=`), **guided demo mode** (5-step walkthrough), victim nodes render
> 🛡 dashed-purple, evidence panel shows the ledger-integrity badge.
> Demo script: `docs/DEMO_SCRIPT.md`. **83/83 tests passing.**

## Why this doc exists

Two problems triggered a full review:

1. **The live tool was unreachable.** The `/workbench` route (`src/App.tsx:10`) is a *fully wired,
   working* three-pane analyst UI talking to the FastAPI backend via `src/lib/api.ts` (correct routes,
   typed, health check, "API offline" banner). But **nothing on the landing page linked to it** — the
   only "workbench" mentions on Home were decorative text in `VisualProof.tsx`; Hero's sole CTA was
   `href="#command-center"` (a scroll anchor). The tool could only be reached by hand-typing `/workbench`.
2. **The build lags the paper.** The demo's headline claims are not yet backed by the data structures,
   and several paper-specified capabilities (real anomaly detection, temporal reasoning, path-finding,
   review persistence, ingest) are absent or faked.

**Scope decided:** full spec-alignment roadmap; the **deployed** Vercel site must let visitors actually
use the workbench (⇒ host the backend, set `VITE_API_URL`, tighten CORS).

## Current state

| Area | Built | Reality vs. paper |
|---|---|---|
| `synthgen/` | ✅ deterministic FIR/CDR/FIN + ground truth (incl. planted circular fund-flows & call bursts as anomaly positives) | Solid. Small name pools ⇒ incidental collisions. |
| `resolve/` | ✅ 3 scored features (name/phonetic/attr) + deterministic identifier path + Devanagari translit + union-find + attribute veto; meets §23 P/R | Docs say "4 of 8 features / uniform weights"; code is 3 features, hand-tuned weights. Temporal / context-TF-IDF / graph-neighborhood **absent**. `cluster.py:62` silently *skips* oversized blocks (recall loss); false-merge rate uses an inflated cross-type denominator. |
| `graph/` | 🌱 3 layers (comm/fin/spatial), per-edge provenance + SHA-256 audit hash (Algorithm 3, correct & tamper-tested) | PERSON nodes always `{"spatial"}` (#5) → swimlanes/"multi-lane hub" unreachable. **No PERSON→ACCOUNT edge** (#6) → financial layer disconnected, "cross-layer hub" demo impossible. LOCATION nodes collide/mislabel (#7). No edge dedup (#8) → inflated degree. VEHICLE nodes never built (#11). No temporal/path/centrality/community. |
| anomaly | ⚠️ sigmoid-of-degree in `api/main.py:50-67` only | Does **not** detect the planted circular flows or bursts; ACCOUNT nodes excluded; no z-score exposed. Weakest, most-overstated claim. |
| `api/` | ✅ 5 routes (`/health`, `/resolve`, `/graph/subgraph`, `/entities`, `/evidence/{id}`) | Missing: search/typeahead, `POST /review`, path, timeline, ingest, auth. Wildcard CORS. Evidence panel: mislabeled `veto_reason` (#13), wrong `confidence` contract (#14), ignores exact NER spans it already has (#15), single-source only (#16). All in-memory, rebuilt at startup. Needs Py 3.10+ though docs say 3.9 (#17). |
| frontend | ✅ `/workbench` UI fully wired; landing page polished | **No entry point to `/workbench`** (being fixed, Phase 1). Accept/Reject/Modify in `EvidencePanel.tsx:117` is fake local state. `api.ts` defaults to `localhost:8000` (deploy breaks without `VITE_API_URL`). |

## Roadmap

- **Phase 0 — Baseline:** run `pytest` (expect 7/16/6/6), `tsc -b` + `pnpm build`, re-extract proposal
  PDF and lock exact §-targets, time cold start + `resolve` on default and `LARGE`.
- **Phase 1 — Usable + deployable (immediate unblock):** (1a) route-linked "Open Case Workbench" CTAs
  in `Hero`, `VisualProof`, and a new persistent `Nav`. (1b) host backend on **Render**
  (`uvicorn api.main:app --host 0.0.0.0 --port $PORT`, root `app/backend`), set `VITE_API_URL` in Vercel,
  tighten CORS in `api/main.py:83-87` from `"*"` to explicit origins; verify deployed `/workbench` is live.
- **Phase 2 — Demo-integrity fixes: ✅ DONE (2026-08-24).** #5 layer propagation pass → PERSON
  hubs now span lanes (5 three-layer hubs on seed 42); #6 inferred OWNED person→ACCOUNT edges
  (enabled by a new FIR "payments traced to account…" narrative sentence in synthgen — benchmark
  regenerated, still seed-42 deterministic, 1,217 mentions); #7 LOCATION keyed by station+district
  (12 nodes, zero label collisions); #8 INFERRED dedupe by (src,tgt,type) keeping strongest claim +
  risk now uses distinct-neighbour degree; #11 VEHICLE nodes from FIR co-mentions (13 vehicles,
  OWNED→spatial). Evidence-panel #13/#14/#15/#16 still open. Tests: 48 passing (5 new graph
  integrity tests). Verified live: root hub C00143 spans all 3 lanes w/ account + phone + 2 vehicles.
- **Phase 3 — Real anomaly detection: ✅ DONE (2026-08-24).** stdlib `analytics/` package:
  `CIRCULAR_FLOW` (cycle detection ≤len 5 + temporal filter — rings must layer within 7 days,
  which kills coincidental random cycles), `COMM_BURST` + `TRANS_BURST` (z-score ≥ 2σ).
  synthgen now plants ground-truth positives (`num_planted_cycles=4` rings closing in 6h,
  `num_call_bursts=3` × 15 calls/48h) into `ground_truth.planted_anomalies` — benchmark
  regenerated, still seed-42 deterministic. **Measured on seed 42: cycles P 1.000 / R 1.000,
  bursts P 1.000 / R 1.000** (the paper's §23 targets). `GET /api/anomalies` serves leads +
  the self-test evaluation + §14.2 disclosure; workbench "Suspicious activity" panel lists
  them with severity bars, click focuses the entity in the graph. 53/53 tests (5 new).
- **RakshakAI scanner (§18): ✅ DONE (2026-08-24).** `api/scanner.py` — deterministic rule engine
  for CWE-89 (f-string/.format/concat SQLi), CWE-78 (os.system/shell=True), CWE-79,
  CWE-798, CWE-327, CWE-22; comment-aware, deduped, line-attributed with remediations.
  `POST /api/scan` + `/scanner` page (code editor, severity chips, finding cards with fixes).
  Engine honestly labeled `rule-based-fallback`; `RAKSHAK_AI_URL` env hook proxies the fine-tuned
  14B model (vLLM OpenAI-compatible) with rule fallback on any failure. The paper's exact
  vulnerable endpoint is the preloaded sample → flagged CRITICAL CWE-89 with the
  parameterized-query fix. 60/60 tests (7 new).
- **Grounded NL query (§16, Algorithm 7): ✅ DONE (2026-08-24).** `api/query.py` — template
  intent parsing (contact / associate / location / owned / path / anomalies / help), fuzzy entity
  grounding via labels+aliases (difflib, cutoff 0.85), BFS shortest path via
  `Graph.shortest_path`. Anti-hallucination contract enforced: unknown names are REFUSED
  ("not in the case graph"), every claim cites edge ids. `GET /api/query` + workbench query bar
  (grounded/refused badge, clickable cited results → focus entity + open evidence panel).
  66/66 tests (6 new).
- **Phase 4 — Temporal + analytics:** `?start=&end=` on subgraph; real timestamps on USES edges (#9);
  time-scrubber UI; `GET /api/graph/path` shortest path + UI; community detection + centrality.
- **Phase 5 — Review persistence (Algorithm 8): ✅ DONE (2026-08-24).** `api/review_store.py`
  (stdlib sqlite3, append-only, thread-safe, SHA-256 of the evidence-panel payload per decision);
  `POST /api/review` + `GET /api/reviews`; decisions replay onto the graph at startup (`_overlay_reviews`)
  so they survive restarts; MODIFY re-hashes the edge after applying reviewed confidence.
  Frontend: `api.review()`/`api.reviews()`, EvidencePanel wired (optimistic flip + rollback,
  confidence-slider MODIFY for PENDING INFERRED edges), LayeredEdge promotes accepted inferences
  to solid/✓ and ghosts rejected edges; Workbench patches subgraph state in place.
  Verified: 43/43 pytest (incl. 8 new review tests), live curl roundtrip, restart persistence,
  and an Accept through the real UI. CORS defaults now include Vite :3000 as well as :5173.
  Note: reviewer identity is a session placeholder until Phase-7 auth.
- **Phase 6 — Ingest + resolve rigor:** `POST /api/ingest` CSV; `GET /api/search?q=` typeahead;
  #1 cap-not-skip oversized blocks; #2 per-type false-merge rate; reconcile 4-of-8/uniform-weights
  doc-vs-code (implement temporal+context features, then update §24 A4 story).
- **Phase 7 — Security, docs & paper sync:** API-key auth; fix Py 3.9→3.10 claim (#17); reconcile
  README/HACKATHON_EXECUTION_PLAN; update or re-mark stale `paper/`.

## Reused utilities (don't reinvent)
`deterministic_key` (`resolve/io.py:48`), union-find (`resolve/cluster.py:30`), `Graph.subgraph` BFS
(`graph/build.py:119`), `score_pair` (`resolve/features.py`), audit-hash `canonical()`
(`graph/build.py:75`), exact NER spans in `output/mentions.jsonl`, `api.ts` typed client + `VITE_API_URL`.

## Constraints
pnpm-native (never npm). Core packages stay stdlib-only; web/DB deps isolated to `api/`. Commits carry
**no** Co-Authored-By trailer. Cite the *current* proposal PDF, not the stale `paper/`.
