# RAKSHAK-NET · Judge demo script

> **Deployment principle to lead with (30 seconds):** *"Police" is a State subject —
> a central crime database is constitutionally off the table. So RAKSHAK-NET is not a
> database, it's a protocol — the **UPI of criminal intelligence**. Districts keep their
> FIRs; only signed **receipts** cross the gateway (the NPCI-style switch), and every
> protected-data access sits behind a dual-signed **warrant artifact** (the DEPA consent model).*

## What is running right now

| Service | URL | Purpose |
| --- | --- | --- |
| Investigator Workbench | http://localhost:3000 | **this is what you screen-share** |
| Single-node API (:8000) | http://localhost:8000/docs | OpenAPI explorer (single vault demo) |
| Mesh gateway :8010 | http://localhost:8010/mesh/health | switches on receipts, never case data |
| Delhi / Mumbai / Jaipur vaults | :8011 :8012 :8013 | district vaults answering locally |
| Automated suite | `cd app/backend && python3 -m pytest -q` | 139 / 139 |

---

## 2-minute "wow" flow

1. **Landing → Workbench** — *"click a node, drag the graph."*
2. **Query rail** — type:
   `how are Abdool Guptaa and Suneeta Daas connected`
   → *"2-step connection … every step cites its evidence."*
   **Say:** `retrieval-only — no LLM in the serving path, so it cannot hallucinate. It
   either cites a source edge or refuses. Watch:` type `is Zzark Zulu linked to anyone`
   → **refuses** instead of inventing.
3. **Evidence panel** — click an edge → `hash_verified: true`.
   **Say:** `every edge carries a SHA-256 audit hash, re-verified live; editing the
   ledger breaks every link after it.`
4. **File FIR (demo star)** — paste the Hindi FIR →
   entities extracted **with character spans** (deterministic regex NER, no LLM) →
   graph grows in real time → **cross-district collision alert** appears.
5. **Warrant gate** — open protected/victim data → request warrant → `PENDING` →
   SP+ approve → `APPROVED` → access ledgered.
6. **Report** — open `/report/{id}` → court-ready, hash-verified evidence chain.

## 5-minute flow (add the mesh — the pitch, not just the demo)

1. (Mesh tab / via API) inject an FIR into **Delhi** referencing
   `+91-8044997278`, `AC7234309805`, `UP78GC4978`:
   - Mumbai answers: **PHONE 2 CDRs, VEHICLE 1 FIR**
   - Jaipur answers: **ACCOUNT 6 FINs, PHONE 5 CDRs**
   - `all_verified: True` — every receipt signature checked.
   **Say:** `Delhi asked, it never sent the FIR — Mumbai and Jaipur answered with
   signed receipts containing record ids only. The switch's ledger stores exchanges,
   never case data — hash-chained, `/mesh/verify` names the first broken record.`
2. **Receipts ledger** → show latest exchange → `entity_keys` + hit summaries, no
   case content. **This is the UPI moment:** *money stays in the bank, messages travel.*
3. **Anomalies + Escalation + Blindspot panels** — circular money flows (P/R 1.000),
   stalking CRITICAL signals, honest blindspot gaps. **Say:** *an anomaly is a lead to
   investigate, never a verdict — human-in-the-loop for every consequential output.*
4. **RakshakAI security** — two beats:
   - **CLI + CI gate** (the product): run `python backend/scripts/scan_repo.py backend/api
     backend/mesh backend/scripts --baseline backend/scripts/scan_baseline.json` live →
     `gate: PASS, local-only, nothing leaves this machine`. Then plant a vulnerable file
     (`db.execute(f"SELECT …{id}")`) → rerun → **`gate: FAIL`** names file, line, CWE.
     **Say:** *"Paste-per-file was the demo; the product is a CLI and a CI gate — the
     deterministic rules fail the build on new CRITICALs; the 14B model is opt-in and
     advisory; SARIF output plugs into GitHub code scanning."*
   - **Sentinel** → `/api/security/posture` — graded endpoint levels, boot self-scan
     hash-chained, and `manifest_check`: this boot's SHA-256 source manifest **compared
     against the previous boot's** — tamper with a file on the server and the next boot
     reports `changed: true`.

## The three guarantees (practice saying these)

| Guarantee | Demo proof |
| --- | --- |
| **Never lies** | fabrication query → refusal; every answer cites edges |
| **Never forgets, never tampers** | evidence `hash_verified`, `/api/reviews/verify`, `/api/warrants/verify`, `/mesh/verify` |
| **Never profiles the innocent** | victim-shield masking + dual-signed warrant for unmasking |

## News you can use (data-integrity checks)

```bash
curl -s http://localhost:8000/api/health                    # graph size
curl -s http://localhost:8000/api/reviews/verify            # review chain
curl -s http://localhost:8000/api/warrants/verify           # warrant chain
curl -s http://localhost:8010/mesh/verify                   # exchange chain
```

## Likely judge questions — rehearsed answers

| Question | Answer |
| --- | --- |
| *Is a central database even legal?* | Police is a State subject (§7L Entry 2) — so the Centre can't own FIRs. We don't centralize: receipts only, matching UPI & DEPA (the government's own DPI). |
| *Why not just use NCRB/CCTNS?* | Those aggregate **statistics** states voluntarily report. We enable live, signed, ledgered *interoperability* on top of state-owned data. |
| *Where's the AI? Hallucination risk?* | No LLM in the serving path — retrieval-only with citations; unknown entities are refused by construction. RakshakAI (14B) reviews the platform's **own code**; it's not in the investigation loop. |
| *How does your security model protect the code?* | Deterministic rules gate CI (fail on NEW CRITICAL against a baseline), the 14B is opt-in/advisory, and Sentinel compares each boot's source manifest against the previous boot's — tamper-evident, not tamper-proof. Not a runtime defense, and we don't claim complete coverage. |
| *Is this real data?* | No — a deterministic, seeded **synthetic benchmark** (FIR/CDR/FIN in Hindi/English/Hinglish) with planted ground truth; no real people. |
| *Anomaly = guilt?* | No — a flagged lead for an investigator; decision-support only, six explicit "what it is not" bounds. |
| *Extensibility to 3M villages?* | Vault-per-district mounts on MeghRaj/CCTNS networks; gateway is a thin registering switch (Sahamati-style registry with NIC issuable identities). |
| *Why Python + stdlib core?* | Deterministic, air-gappable, no foreign-cloud dependency — runs fully offline on NIC MeghRaj. |

## Security claims cheat sheet (RakshakAI)

**Say these:** "detects selected CWE patterns before deployment" · "runs locally or in CI —
source stays on your machine by default" · "SARIF findings for code-scanning workflows" ·
"records the analysis engine and model identity" · "checks deployed source integrity against
a trusted manifest at boot" · "tamper-evident audit records" · "secure-by-design, not a
runtime firewall."

**Never say these:** "prevents attacks" · "finds all vulnerabilities" · "protects production
at runtime" · "tamper-proof" · "zero hallucinations" (as an absolute) · "air-gapped" when a
remote model endpoint is configured · "catches zero-days."

## Test it yourself (automated)

```bash
cd app/backend && python3 -m pytest -q          # 139 passed
```

Manual browser checklist: `/:3000` landing → `/workbench` graph + time-travel slider →
query rail → evidence panel → File FIR → warrant modal → `/report/{id}` → `/scanner`.