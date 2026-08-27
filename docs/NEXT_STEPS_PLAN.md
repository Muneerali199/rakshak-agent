# RAKSHAK-NET — SIH-Winning Execution Plan (Next Steps)

_Authoritative execution doc. Created 2026-08-26 after strategy review._
_Supersedes nothing in `PROJECT_STATUS_AND_NEXT_STEPS.md`; this doc layers on top._

---

## The Strategy (approved)

> **Pitch:** "India's first evidence-ledger criminal intelligence system —
> that **never lies**, **never forgets**, and **never profiles the innocent**."

Three copy-resistant layers, stacked on the existing working system (70/70 tests):

| Layer | Claim | Implementation status |
|---|---|---|
| 1 · Never lies | Anti-hallucination grounded query — retrieval-only, cites edge ids, refuses unknowns | ✅ already built (`api/query.py`) |
| 2 · Never forgets / never tampers | **Hash-CHAINED evidence ledger** — every review decision's hash includes the previous record's hash; any tamper breaks the chain | 🔨 this plan, task 2 |
| 3 · Never profiles the innocent | **Victim-Shield** — complainants/victims pseudonymized, access-restricted, never network-analyzed; offenders get full analysis | 🔨 this plan, task 3 |

Demo differentiators stacked on top:

| Demo moment | Implementation |
|---|---|
| **Time-Travel Investigation** — drag a slider, watch the trafficking money-ring form week by week | 🔨 task 5 (API `?start=&end=` already exists) |
| **Adversarial test** — plant a false-match twin live, watch the system refuse the merge | demo script (traps already exist in Experiment A) |
| **Auto-loaded case** — workbench opens on the circular-flow ring, not an empty screen | 🔨 task 4 |
| **Guided demo mode** — one button walks the 5-minute flow | 🔨 task 6 |

---

## Task 1 — This doc ✅

---

## Task 2 — Hash-Chained Evidence Ledger (Layer 2)

**Files:** `backend/api/review_store.py`, `backend/api/main.py`, `backend/api/schemas.py`,
`backend/tests/test_review.py` (+new `test_ledger.py`).

1. **Schema migration** — add columns `prev_hash TEXT NOT NULL` and `chain_hash TEXT NOT NULL`
   to `reviews` table. Migration: if table exists without columns, `ALTER TABLE ADD COLUMN`
   with backfill (`prev_hash = ""`, `chain_hash = sha256(row fields + "")`).
2. **Chain rule** — on `add_review`:
   - `prev_hash` = `chain_hash` of the row with `MAX(id)` (or `""` for the genesis row).
   - `chain_hash = sha256({edge_id, decision, reviewer_id, timestamp, evidence_hash, modifications, prev_status, prev_hash})`.
   - Genesis row: `prev_hash = ""`, `chain_hash` over payload with `prev_hash=""`.
3. **`ReviewStore.verify_chain() -> dict`** — walks rows in `id` order, recomputes each
   `chain_hash`, checks `prev_hash` linkage. Returns `{ok: bool, records: int, first_bad_id: int|None}`.
4. **API** — `GET /api/reviews/verify` → `{ok, records, first_bad_id, disclosure}`.
   Add `chain_hash` + `prev_hash` to `AuditRecordSchema` and `GET /api/reviews` output.
5. **Tamper demo support** — the endpoint must detect a manually `UPDATE`d row
   (test writes a row, tampers via raw SQL, asserts `ok: False` + `first_bad_id`).
6. **Overlay replay unaffected** — `_overlay_reviews` uses `latest_reviews()`; chaining is
   metadata only.
7. **Frontend** — EvidencePanel audit record shows chain hash (truncated) + a
   "ledger integrity: ✓ verified" badge fed by `GET /api/reviews/verify`.

**Tests (new, `test_ledger.py`):** genesis row chains to `""`; sequential chain links;
tamper detection (UPDATE decision → verify fails at that id); tamper propagation
(UPDATE row 1 → row 2+ also flagged via prev_hash linkage); verify endpoint shape;
chain survives restart (fresh store on same db file).

---

## Task 3 — Victim-Shield Mode (Layer 3)

**Files:** `backend/graph/build.py`, `backend/api/main.py`, `backend/api/query.py`,
`backend/api/schemas.py`, `frontend/src/workbench/EvidencePanel.tsx`,
`frontend/src/workbench/EntityNode.tsx`, new `backend/tests/test_victim_shield.py`.

1. **Role tagging at graph build** — synthgen FIR mentions already carry
   `field: "accused" | "complainant" | "narrative"`. In `build_graph`, PERSON nodes get
   `meta["role"]`: `"victim"` if the cluster appears as `complainant` in any FIR,
   `"accused"` if it appears as `accused`, `"mentioned"` otherwise (priority: accused > victim
   if both — a person can be complainant in one FIR and accused in another).
2. **API exposure** — `GraphNode.meta.role` flows through `_to_node` unchanged (already
   generic). `/api/entities` already returns `meta`.
3. **Query masking (`api/query.py`)** — if the grounded entity has `role == "victim"`:
   return `grounded: true`, masked answer: `"<label> is a protected party in this case.
   Victim data is pseudonymized and access-restricted (Women Safety Division policy).
   Network analysis is restricted to accused persons."` with **zero results/citations**.
   This must apply to every intent (contact/associate/location/owned/path — for path, if
   EITHER endpoint is a victim, refuse with the same message).
4. **Evidence restriction** — `GET /api/evidence/{edge_id}`: if either endpoint node has
   `role == "victim"`, redact victim-identifying spans from snippets (mask the victim label
   in `claim` as `[PROTECTED VICTIM]`) and add `victim_shield: true` to the response.
5. **UI** — victim nodes render with a distinct shield marker + grey/purple color and a
   `VICTIM-SHIELDED` tag; EvidencePanel shows the protection banner when `victim_shield`.
6. **Docs/disclosure** — query + evidence responses carry the shield disclosure line.

**Tests (new):** role tagging (complainant cluster gets `victim`); query victim → masked,
no results, no citations; query accused → normal; path query touching victim → masked;
evidence on victim-touching edge → claim redacted + flag; evidence on accused-only edge →
unchanged; non-PERSON nodes unaffected.

---

## Task 4 — Auto-Load the Anomaly Case on Startup

**Files:** `frontend/src/pages/Workbench.tsx`.

1. On bootstrap, after `api.anomalies()` resolves, set `activeId` to the **top
   CIRCULAR_FLOW anomaly's `entity_id`** (fallback: first PERSON entity, as today).
2. Depth defaults to 2 when auto-loading an anomaly (the ring needs 2 hops to render).
3. A subtle "CASE AUTO-LOADED · CIRCULAR FUND FLOW" chip in the header; clicking it
   re-opens the anomaly panel.

**Tests:** manual/E2E verification only (no frontend test infra in repo).

---

## Task 5 — Time-Travel Slider

**Files:** `frontend/src/pages/Workbench.tsx`, `frontend/src/lib/api.ts`,
new `frontend/src/workbench/TimeSlider.tsx`.

1. **API client** — `api.subgraph(entityId, depth, layers?, start?, end?)` passes
   `start`/`end` through (backend already supports them).
2. **Range discovery** — derive min/max from the loaded subgraph's edge timestamps
   (fallback: 2026-01-01 → 2026-06-30).
3. **UI** — a bottom-overlay slider (single handle = "show evidence up to this date",
   simplest mental model: end-date scrubber). As it moves, subgraph refetches with
   `end=<date>`; edges appear as the ring forms. Debounced 300 ms.
4. **Readout** — current date + `stats.edges` count beside the slider; a small
   "RESET TIME" chip.
5. Slider hidden until a subgraph is loaded; disabled while fetching.

---

## Task 6 — Guided Demo Mode + Adversarial Script

**Files:** new `frontend/src/workbench/DemoMode.tsx`, `frontend/src/pages/Workbench.tsx`,
`docs/DEMO_SCRIPT.md`.

1. **"▶ DEMO" button** in the header. Opens a step overlay (top-center card):
   - Step 1: focuses the circular-flow anomaly (auto-loads its subgraph).
   - Step 2: pre-fills the query bar with `what does <hub person> own?` and runs it.
   - Step 3: runs `Sherlock Holmes` → shows the refusal (the killer moment).
   - Step 4: opens evidence panel for an INFERRED edge → highlights hash + review buttons.
   - Step 5: shows the ledger badge (`/api/reviews/verify`) — "tamper-evident audit chain".
   - Each step: short caption, Next/Back, Esc to exit. All client-side, driven by existing
     callbacks (`setActiveId`, query run, `setSelectedEdge`).
2. **`docs/DEMO_SCRIPT.md`** — the full 5-minute spoken script incl. the adversarial
   false-match-twin moment (uses `POST /api/resolve` with a planted twin pair) and the
   victim-shield query.
3. Demo mode never mutates the review store (read-only steps only).

---

## Task 7 — Verification & Docs Sync

1. `pytest` — all existing 70 + new ledger/victim-shield tests green.
2. `tsc -b && vite build` clean.
3. Live E2E: health → auto-load → query → refusal → victim mask → ledger verify →
   time slider.
4. Update `README.md` status table (ledger ✔, victim-shield ✔) + `docs/PROJECT_STATUS_AND_NEXT_STEPS.md`
   marking this plan's tasks done.
5. `docs/DEMO_SCRIPT.md` finalized.

---

## Non-Goals (explicitly NOT doing)

- ❌ Real LLM in the serving path (kills the never-lies USP)
- ❌ Auth/RBAC (Phase 7, post-SIH; reviewer_id placeholder stays)
- ❌ CSV ingest endpoint (Phase 6, post-SIH)
- ❌ Federated cross-district hashing (vision slide only)
- ❌ npm (repo is pnpm-native), ❌ new runtime deps in core packages (stdlib-only)

## Order of execution

**2 → 3 → 4 → 5 → 6 → 7.** Ledger and victim-shield first (they are the pitch),
then the demo polish, then docs.
