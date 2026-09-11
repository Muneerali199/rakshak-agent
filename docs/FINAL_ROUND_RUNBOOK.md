# Final Round — Day-Of Runbook

> Print this. Tape it under the laptop. No improvisation needed.

---

## 0. One command (5 minutes before)

```bash
bash scripts/demo_reset.sh
```

What it does:
- Kills all demo ports (8000, 8010, 8011, 8012, 8013, 3000, 5173)
- Wipes output + output-vaults (all ledgers, sentinel history, vault partitions)
- Regenerates seed-42 benchmark → partitions into 3 vaults
- Boots: gateway :8000, vaults delhi:8001 / mumbai:8002 / jaipur:8003, UI :3000

**Verify after boot** (all should be 200):
```bash
curl -s http://localhost:8000/mesh/health          # → vaults ok, records 0
curl -s http://localhost:8001/api/health           # → delhi vault
curl -s http://localhost:8001/api/security/posture | python3 -m json.tool
```

Posture should show:
- `engine: rules`
- `manifest_check.changed: true` (first boot), `files: 64`
- `ledger: reviews 0, warrants 0, sentinel 3`

---

## 1. Pre-open (browser tabs)

| Tab | URL | Purpose |
|-----|-----|---------|
| A | http://localhost:3000/workbench | Main workbench (live graph) |
| B | http://localhost:3000/scanner | Scanner interactive demo |
| C | http://localhost:3000/report/AC:AC0076617711 | Evidence report (lead anomaly) |
| D | http://localhost:3000/report/CRAMES | Report for live-filed FIR entity |

Keep tab A focused. Switch to B/C/D only when narrating.

---

## 2. Demo flow (5 minutes)

### 2a. Workbench — circular money flow (1 min)

Narrate:
> "The workbench auto-loads the highest-risk anomaly. AC0076617711 shows a circular
> fund flow — money rotates across 3 accounts within 7 days
> (AC0076617711 → AC7710932480 → AC9317461200 → AC0076617711), hawala-style layering.
> Evidence records: FIN-000010/11/12."

Point at:
- Graph centre: AC0076617711 (focus node, red ring = investigating)
- Left sidebar: Escalating contact CRITICAL — `+916112805982` weekly call ramp 1→1→3→5
- Left sidebar: 7 suspicious activity leads (cycles detected, bursts)
- Left sidebar: Blindspots — "50 partially corroborated · No communication layer evidence"
- Status bar: ⛁ delhi vault, 10 nodes · 10 edges, live

### 2b. Identity resolution — cross-script (30 sec)

Left sidebar → Identity Resolution. Already filled:
- Name A: `Mohammad Arif`
- Name B: `मोहम्मद आरिफ़`

Click **Resolve** → `MATCH 100%`, name 1.00, phonetic 1.00.
Add: `uncalibrated — treat as a lead, not a verdict`

> "Indian-tuned phonetic matching + IndicXlit Devanagari transliteration
> resolve cross-script name variants deterministically."

### 2c. File a FIR (1 min)

Click **＋ File FIR** → modal opens. Click **load sample** or paste:

```
रात 9:30 बजे रमेश ने सुनीता देवी को फोन किया और धमकी दी।
₹50,000 ट्रांसफर मांगे। पुराना केस भी दर्ज है।
Sunita ko Kal mein bhi call aya tha.
```

Fill:
- District: `Delhi`
- Police station: `PS Karol Bagh`
- Complainant: `Sunita Devi`
- Accused: `Ramesh Kumar`

Click **Ingest into case graph** → `✓ merged · 116 nodes · 250 edges`
Point at: `Victim-shield applied`, `No cross-case collisions`

### 2d. Report page (30 sec)

Open tab C (`/report/AC:AC0076617711`):
- Hash-verified 2/2, Ledger intact
- Corroboration 50/100
- Blindspots list
- Anomaly context: circular flow
- Evidence chain rows: each carries ✔ hash + source doc id

> "Every evidence row carries a recomputable SHA-256 hash.
> Tampering with any row breaks the hash chain — independently verifiable."

### 2e. Scanner (1 min)

Open tab B (`/scanner`). Click **Scan with RakshakAI**.

- Engine: `rules` (deterministic, primary)
- Findings: 4 — CWE-89 SQLi (CRITICAL ×2), CWE-78 OS injection (CRITICAL), CWE-798 hardcoded credential (HIGH)
- HITL disclaimer visible

> "The platform scans its own code before every deploy.
> Deterministic rules are the gate; the 14B model is advisory, never blocking."

If 14B endpoint available (`RAKSHAK_AI_URL` set): toggle `--model` to show advisory findings appearing alongside rules findings.

### 2f. CLI gate (1 min) — run from terminal

```bash
cd backend

# PASS — baseline clean
python3 scripts/scan_repo.py . --baseline scan_baseline.json
# → gate: PASS (0 new findings)

# Plant a SQLi
echo 'x = f"SELECT * FROM t WHERE id={uid}"' > /tmp/_sqli_test.py

# FAIL
python3 scripts/scan_repo.py /tmp/_sqli_test.py --baseline scan_baseline.json
# → gate: FAIL (1 new CRITICAL)

# Restore
rm /tmp/_sqli_test.py
```

### 2g. Ask-box (30 sec)

Back to tab A. Type in ask box: `contact Aniil Singh`

Expected: "CDR records show Aniil Singh in contact with: +916586518506, …" with 10 citations.
Backup line: `any suspicious activity` → "7 analytical anomalies on file. Top: …"

> "The ask-box is NOT a chatbot. It answers only from the case graph
> with evidence citations — no hallucination, no free-form generation.
> If the question can't be answered from grounded data, it refuses.
> Try free-form questions live and watch it refuse rather than invent."

---

## 3. Judge Q&A — 5 core answers (rehearse verbatim)

**Q1: "Where is the AI in this?"**
> "Three layers. (1) The rules engine is deterministic — 6 CWE classes, no neural,
> failsafe on boot. (2) The 14B advisory auditor classifies CWE types, never blocking.
> (3) IndicXlit transliterates 21 Indic languages offline — 11M params, ~274 MB,
> runs on district hardware. The resolution engine is deliberately deterministic
> because identity merges are irreversible — we prioritise explainability over accuracy."

**Q2: "F1 0.9935 — isn't that too good? What's the trick?"**
> "Honest answer: we generated the benchmark ourselves with planted ground truth.
> That number tells you the pipeline recovers what it planted — not that it works
> on real data. A real-data pilot is Phase 5. The numbers we're proud of are
> the false-merge rate: 6 in 100,000. Target was <0.01."

**Q3: "Same-name people — don't they merge?"**
> "That's exactly the hard case. We have a weakest-link rule: every name token must
> match — 'Sana Singh' doesn't bridge to 'Salman Sheikh'. We also carry a
> DISAMBIGUATOR flag that splits matches where the victim has different age or
> address. These are human-verified + hash-chained."

**Q4: "Can this hallucinate?"**
> "The scanner rules engine and the resolution engine are deterministic — zero
> hallucination by design. The ask-box is schema-grounded, not a chatbot. The 14B
> advisory auditor is the only generative component, and it never gates any action —
> a wrong classification surfaces as advisory, not a finding. The HITL posture is
> always disclosure-annotated."

**Q5: "Is this legal under DPDP/Puttaswamy?"**
> "We modelled the warrant flow on India's DEPA/Account Aggregator consent
> architecture. Protected-party access requires a scoped, expiring warrant:
> IO requests → SP countersigns (four-eyes principle) → hash-chained audit trail.
> Local processing only; no data leaves the district data centre. Synthetic data
> only for prototype — real-data pilot requires DPA/District Magistrate approval."

---

## 4. DL-judge killer question (if asked)

**Q: "Why a rules engine at all if you have a 14B model?"**

> "Fair strike. Identity merges are irreversible — once two people are linked,
> untangling them in court is expensive. Explainability beats accuracy here.
> The rules engine makes deterministic, auditable decisions. The 14B model
> catches things rules miss — new CWE classes, edge cases — as advisory.
> This is a deliberate architectural split: deterministic where failure is costly,
> neural where failure is cheap and recoverable."

**Follow-ups:**
- *Drift over time?* → Rules are fixed; only the advisory endpoint can update.
- *Class imbalance?* → Negative mining in training, precision-recall trade-off disclosed.
- *Why not a transformer for resolution?* → IndicXlit handles the language part;
  the resolve pipeline is intentionally simpler and auditable.

---

## 5. Contingency cards

| Issue | Fix |
|-------|-----|
| `demo_reset.sh` boots but health returns empty | Wait 5s, re-curl. If still empty: `bash scripts/stop_demo.sh && bash scripts/demo_reset.sh` |
| Gateway returns `vaults: []` | Vault processes died. Check `backend/output/logs/vault-delhi.log` for import errors |
| Frontend shows `refused` on ask-box | Normal — ask-box only answers grounded graph questions, not free-form ranking |
| UI not loading | `VITE_API_URL=http://localhost:8001 npm run dev` from `app/` root |
| CLI gate shows FAIL on reset code | Run `python3 scripts/scan_repo.py . --write-baseline scan_baseline.json` to re-baseline after any code change |
| Judge asks "show me the 14B model running" | Narrator: "The 14B endpoint is not configured for this demo; the rules engine is the primary gate. The model is advisory and non-blocking." Do NOT improvise a model call. |
| Manifest shows `changed: true` | Expected after code edits. First boot always shows `changed: true`. After second boot with no code changes, it returns `changed: false`. |
| Ask-box refuses your question | Expected. Reframed: "Notice it refused — it won't hallucinate an answer. This is by design." |

---

## 6. Key numbers to remember (say only if asked)

| Metric | Value | Source |
|--------|-------|--------|
| Hybrid resolution F1 | 0.9935 | Experiment A, synthetic 50-person |
| PERSON F1 | 0.9276 | Experiment A, synthetic 50-person |
| False-merge rate | 6e-05 (target <0.01) | Experiment A |
| Cycles P / R | 100% / 100% | Seed-42 planted |
| Bursts P / R | P 0% / R — (delhi, no bursts planted) | Honest |
| Scanner findings (self-scan) | 11 known, 2 CRITICAL | scan_baseline.json |
| 14B model | Qwen2.5-Coder-14B + LoRA, temp 0 | HuggingFace card |
| IndicXlit | 11M params, ~274 MB, 21 Indic languages | Web verified |
| Review records post-demo | hash-chained, `ok: true` | /api/reviews/verify |
| Warrant records post-demo | hash-chained, `ok: true` | /api/warrants/verify |

---

## 7. 30-second recovery line

> "This prototype uses synthetic data to prove the pipeline works honestly.
> The numbers are on the synthetic benchmark — a real-data pilot is Phase 5.
> We're showing what the architecture can do, not claiming it's production-ready."

---

*Last verified: 2026-09-11. Mesh: gateway :8000, vaults :8001-8003, UI :3000.*
*Fresh demo: `bash scripts/demo_reset.sh` — one command, everything comes back clean.*
