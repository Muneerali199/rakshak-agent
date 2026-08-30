# RAKSHAK-NET — System Architecture

>The constitutional evidence mesh: how 3 district vaults, an NPCI-style gateway, and a
>investigator workbench fit together, why the data never leaves its district, and where every
>guarantee ("never lies · never tampers · never profiles") is enforced *in code*.

---

## 1. The fundamental constraint

Policing is a **State subject** (Seventh Schedule, Constitution of India). A single national
crime database is therefore **legally impossible**. RAKSHAK-NET does not fight this — it
exploits it, exactly as India's own digital-public-infrastructure has twice before:

| India's DPI | What it proves | RAKSHAK-NET analogue |
| --- | --- | --- |
| **UPI** | Banks interoperable *without* centralizing money | Police districts interoperable *without* centralizing FIRs |
| **Account Aggregator (DEPA)** | Data shared *without* storing it | Signed queries travel; case data stays in its district |
| — | — | **Dual-signed, scoped, expiring warrant artifacts** (the DEPA consent model) gate every protected-data access |

The gateway stores **receipts, never case data**.

---

## 2. Topology

```
                          ┌────────────────────────── Tile/Workbench ──────────────────────────┐
                          │  Vite + React 19 + TS + Tailwind  (src/)                            │
                          │  Landing · /workbench (React Flow, 3-pane) · /report/{id} · /scanner │
                          └───────────────┬─────────────────────────────────────────────────────┘
                                          │  src/lib/api.ts  (typed fetch, CORS)
                          ┌───────────────▼─────────────────────────────────────────────────────┐
                          │                        MESH GATEWAY  (:8000, NPCI-style switch)      │
                          │   /mesh/route  /mesh/health  /mesh/receipts  /mesh/verify            │
                          │   POST /mesh/query  (central API fan-out, app-side)                  │
                          │   stores signed exchange RECEIPTS in a hash-chained SQLite ledger     │
                          └───┬────────────────┬─────────────────────┬──────────────────────────┘
                              │ HMAC-signed    │ request envelopes   │
                              │ envelopes      ▼                     ▼
                       ┌──────▼─────┐   ┌──────────────┐      ┌──────────────┐
                       │ DELHI vault │   │ MUMBAI vault │      │ JAIPUR vault │
                       │  :8001      │   │  :8002       │      │  :8003       │
                       │  // data    │   │  // data     │      │  // data     │
                       └─────────────┘   └──────────────┘      └──────────────┘
                     each vault = full FastAPI instance (backend/api) + its own SQLite graph
```

**The mesh property:** a query is *routed* to each vault; the vault answers *locally* against its
own data; only the **answer + HMAC signature + receipt hash** return to the gateway. Case records
never cross district boundaries. Every exchange lands in the gateway's **hash-chained exchange
ledger** — `/mesh/verify` walks it and names the first broken record.

> Demo disclosure: HMAC shared-secrets stand in for **NIC-issued PKI certificates** (the
> production signing layer). The *protocol shape* (envelope → sign → route → receipt → verify)
> is exactly what is being demonstrated; swapping HMAC for NIC certs is a credential-layer change,
> not an architectural one.

---

## 3. Single-node vs mesh

| Mode | Command | Runs |
| --- | --- | --- |
| **Full mesh (demo default)** | `scripts/run_mesh.sh` | gateway `:8000` + Delhi `:8001` + Mumbai `:8002` + Jaipur `:8003` + frontend `:3000` |
| **Single-node dev** | `uvicorn api.main:app` (from `backend/`) | one vault on `:8000` (mesh fan-out reports other districts unreachable, honestly) |

Both share the same code — a vault *is* the FastAPI app; the gateway is a thin routing/signing
layer on top. This is what makes the whole thing testable as a unit and deployable as a mesh.

---

## 4. Component map (backend)

| Component | Path | Stdlib-only? | Responsibility |
| --- | --- | --- | --- |
| Synthesizer | `synthgen/` | ✅ | Seeded(42) synthetic FIR/CDR/FIN + planted anomaly ground truth |
| Hybrid identity resolution | `resolve/` | ✅ | Multi-script name matching, phonetic scoring, clustering, §23 eval |
| IndicXlit adapter | `resolve/indic_xlit.py` | ✅ | AI4Bharat-style Devanagari↔Latin transliteration, honest fallback |
| Temporal knowledge graph | `graph/` | ✅ | 3-layer graph (communication/financial/spatial) + provenance + SHA-256 edge audit hash |
| Anomaly detection | `analytics/detect.py` | ✅ | Circular-flow + burst detectors (P1.0/R1.0 on planted set) |
| Blindspot / corroboration | `analytics/blindspot.py` | ✅ | What the report *cannot* establish → corroboration score |
| Stalking escalation | `analytics/escalation.py` | ✅ | Weekly trajectory + night-call signal → CRITICAL alerts |
| **Mesh** | `mesh/` | ✅ | `gateway.py` (route/HMAC/receipts) · `client.py` (fan-out) · `protocol.py` (envelopes) · `ledger.py` (hash chain) |
| **Warrant gate** | `api/warrants.py` | ✅ | Dual-signed (SP+) scoped/expiring/revocable warrants, four-eyes |
| **Sentinel** | `api/sentinel.py` | ✅ | Graded endpoint levels (MLPS-inspired), boot self-scan (hash-chained), build manifest |
| FastAPI service | `api/main.py` | (fastapi) | 20+ endpoints wiring graph + mesh + review + warrants + ingest |
| Human-review ledger | `api/review_store.py` | ✅ | SHA-256 hash-chained append-only review history |
| Victim shield | `api/query.py` | ✅ | Query masking + evidence redaction for protected parties |

Third-party deps are deliberately isolated to the `api/` layer (fastapi/uvicorn/pydantic/httpx)
and the frontend. The **core intelligence stack is standard-library Python, deterministic, and
air-gapped by construction.**

---

## 5. The three guarantees — where they're enforced

1. **Never lies** — NL query (`/api/query`) is *retrieval-only*: every answer cites the edges that
   support it and **refuses** unknown entities ("Sherlock Holmes → not in the case graph"). There
   is no LLM in the serving path, so hallucination is impossible *by construction*.
2. **Never tampers** — reviews (`/api/reviews/verify`), warrants (`/api/warrants/verify`), and mesh
   exchanges (`/mesh/verify`) are hash-chained SHA-256 logs. Editing a record breaks every link
   after it; verification names the first broken record id.
3. **Never profiles the innocent** — victim-shield: complainants are pseudonymized; unmasking
   requires a **scoped, expiring, dual-signed warrant** (four-eyes, SP+), and the access itself is
   ledgered.

---

## 6. Ethical positioning

| Is | Is not |
| --- | --- |
| Investigative decision-support | Surveillance / real-time monitoring |
| Text/record entity resolution | Facial/voice biometric identification |
| Evidence-grounded, source-traceable analytics | Opaque black-box scoring |
| Analytical anomaly → *investigate* | Prediction of guilt |
| Human-in-the-loop for every consequential output | Autonomous enforcement |
| Case-bounded, data-minimized | National dragnet |

**Anomaly ≠ criminality.** Every flag is a lead for a human investigator, never a verdict.
