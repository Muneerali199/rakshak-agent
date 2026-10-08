# Rakshak — Judge Demo Data Sheet (verified live on seed-42)

> Everything below was **captured this session by hitting the running mesh**, not asserted.
> Content is deterministic on `seed 42`: `demo_reset.sh` reproduces the same persons, aliases,
> FIRs, weapons → same answers and curls. **Node ids may shift ±a few on a fresh partition**
> (cluster ordering), so scripts must never pin an id — the check script already ignores ids.
> Last verified: **2026-10-08** · services: gateway **:8000**, Delhi **:8001**, Mumbai **:8002**,
> Jaipur **:8003**, UI **:3000** (Vite, configured in `vite.config.ts`).

---

## 0. Live topology (proof of "it's on, right now")

```bash
curl -s http://localhost:8000/mesh/health   # → vaults: delhi, jaipur, mumbai · ledger ok
curl -s http://localhost:8001/api/health    # → delhi…. nodes/edges
curl -s http://localhost:8002/api/health    # → mumbai
curl -s http://localhost:8003/api/health    # → jaipur
```

Observed today: gateway `{vaults:[delhi,jaipur,mumbai], ledger.ok:true}` ·
Delhi 113 nodes/248 edges · Mumbai 122/301 · Jaipur 136/242.
After the live FIR-ingest beat below, Delhi grew to **119 nodes / 255 edges** on screen.

---

## 1. Demo data sheet (the "cast" judges will see)

| Beat character | Graph id* | Aliases (cross-script) | Where they show up |
| --- | --- | --- | --- |
| Nehaa Kumaar | `C00108` | `Nehaa Kumar` · `नेहा कुमार` | dossier (3 FIRs; roles accused **and** complainant; sec 406/467/379/420/66C IT) |
| Aniil Singh | `C00098` | — | contact query (calls 10 numbers incl. cross-script `Manooj Shaikh`) |
| Sunita Devi (complainant/victim demo) | `C00110` (label `Sunita Das`) | devanagari surface in sample FIR | evidence auto-resolve → 0.531 UNCERTAIN → **route_to_review** |
| Ramesh Kumar (accused demo) | `C00101` (label `RAKESHH Kumar`) | `Ramesh Kumar` | evidence auto-resolve → 0.681 UNCERTAIN → **route_to_review** |
| Stalker / victim phones | `PH:6112805982` → `PH:9527758416` | — | escalation **CRITICAL**, weekly `[1,1,3,5]`, 2 night calls, victim-linked |

Cross-script pair demo: `Mohammad Arif` ≡ `मोहम्मद आरिफ़` → `MATCH 1.00` (normalized both to `arif mohamad`).

Officers (all vaults — from `/api/auth/officers`):

| Officer | Role | aadhaar / otp |
| --- | --- | --- |
| officer.DEL-001 Inspector Aryan Malhotra | IO | 700011771177 / 771177 |
| officer.DEL-003 SP Vikram Rawat | SP (countersign) | 700077417741 / 774174 |
| officer.MUM-001 Inspector Sameer Naik | IO | 700033513351 / 335133 |
| officer.JAI-001 Inspector Kavita Rathore | IO | 700055225522 / 552255 |

\* `Aniil Singh`'s id on the recorded run was `C00098`; `Nehaa Kumaar` recorded as `C00108`
then `C00109` on the fresh partition — labels/aliases are the stable ground truth, not ids.

---

## 2. The exact demo inputs (copy-paste, no improvisation)

### 2.1 The "File FIR" Hindi sample (matches the UI *load sample* button)
```
दिनांक 2026-10-08 को शिकायतकर्ता Sunita Devi ने बताया कि Ramesh Kumar ने उसे +91-8044997278 से धमकी भरा कॉल किया। संदिग्ध का वाहन UP78 GC 4978 देखा गया। पैसे खाता AC7234309805 में ट्रांसफर हुए। धारा 354D लगाई गई। संदिग्ध का संबंध Desi Traders Pvt Ltd कंपनी से बताया गया और वह करोल बाग मार्केट में रुका हुआ देखा गया।
```
Ingesting it (officer session) yields — **verified output**:
```
record_id FIR-LIVE-0001 · 8 entities with char spans
  ORGANIZATION Desi Traders Pvt Ltd [230-250] · LOCATION करोल बाग मार्केट [276-292]
  PHONE 8044997278 [77-91] · ACCOUNT AC7234309805 [163-175] · VEHICLE UP78GC4978 [130-142]
  IPC 354D [194-203] · PERSON Sunita Devi [33-44] · PERSON Ramesh Kumar [57-69]
victim_shield_applied: True
cross_case_links: PHONE 8044997278 also in 4 records (Kanpur, New Delhi) ·
                 ACCT AC7234309805 also in 2 records (financial-layer)
mesh receipts: Mumbai → PHONE:8044997278 (2 CDR) + VEHICLE:UP78GC4978 (1 FIR) · Jaipur → …
graph_stats: nodes 113→119 · edges 248→255
```
Judge line: *"Entities highlighted inline with character spans — zero LLM. The victim is
auto-shielded. And the moment the FIR lands, Mumbai and Jaipur answer with signed receipts."*

### 2.2 Cross-script resolve — the MATCH that exact-match would miss
```bash
curl -s -X POST http://localhost:8001/api/resolve -H 'Content-Type: application/json' \
  -d '{"name_a":"Mohammad Arif","name_b":"मोहम्मद आरिफ़"}'
```
→ `{decision:"MATCH", confidence:1.0, features:{name:1.0, phonetic:1.0},
     normalized_a:"arif mohamad", normalized_b:"arif mohamad"}`

### 2.3 The veto — same name, different person, system declines
```bash
curl -s -X POST http://localhost:8001/api/resolve -H 'Content-Type: application/json' \
  -d '{"name_a":"Mohammad Arif","name_b":"Mohammad Arif","address_a":"Karol Bagh, Delhi","address_b":"Byculla, Mumbai","age_a":34,"age_b":61}'
```
→ `{decision:"NON_MATCH", confidence:0.75, veto_reason:"hard attribute conflict on a confident name match"}`

### 2.4 Person dossier (officer session)
```bash
# login (token reused below)
TOK=$(curl -s -X POST http://localhost:8001/api/auth/login -H 'Content-Type: application/json' \
  -d '{"aadhaar":"700011771177","otp":"771177","purpose":"demo"}' | python3 -c 'import sys,json;print(json.load(sys.stdin)["token"])')
curl -s -H "Authorization: Bearer $TOK" -X POST http://localhost:8001/api/resolve/person \
  -H 'Content-Type: application/json' -d '{"name":"Nehaa Kumaar"}'
```
→ `found:true · id C00108 · match_confidence 1.0 · aliases [Nehaa Kumaar, Nehaa Kumar, नेहा कुमार] ·
   roles [accused, complainant] · fire_count 3 · phones … · accounts [AC2104709521] ·
   vehicle [UP32 KL 2886] · engine builtin-rule-romanizer`

### 2.5 Evidence auto-resolve — the honest review gate
```bash
curl -s -H "Authorization: Bearer $TOK" -X POST http://localhost:8001/api/resolve/evidence \
  -H 'Content-Type: application/json' \
  -d '{"text":"शिकायतकर्ता Sunita Devi ने बताया कि Ramesh Kumar ने उसे +91-8044997278 से धमकी भरा कॉल किया।"}'
```
→ on a **fresh boot** (before the live ingest demo): `count:2, candidate_count:20`
```
 Ramesh Kumar → RAKESHH Kumar (C00101)  0.681  UNCERTAIN → route_to_review
 Sunita Devi → Sunita Das (C00110)      0.531  UNCERTAIN → route_to_review
```
→ **after** the §2.1 FIR-ingest beat (names now on file in this district): the same text returns
`Ramesh Kumar → MATCH 1.0` and `Sunita Devi → MATCH 1.0`, both `route_to_review:false` (auto-linked).
Judge line: *"Names already on the case file resolve clean; borderline matches (e.g. the two
above, whose spellings differ across districts) are held for a human AC / REJECT / MODIFY —
every decision is hash-chained."*

### 2.6 Escalation — see the curve, not the file
```bash
curl -s -H "Authorization: Bearer $TOK" http://localhost:8001/api/escalation
```
→ `CRITICAL +916112805982 → +919527758416 · victim_linked:true · weekly [1,1,3,5] ·
   reason: contact volume 5 in week 2026-W14 is 3.0× the prior weekly average (1.7) with 2 night calls`

### 2.7 Mesh — the UPI moment (receipts, never case data)
```bash
# signed ENTITY_LOOKUP envelope from Delhi: two accounts, answered by Mumbai & Jaipur
curl -s -X POST http://localhost:8000/mesh/route -H 'Content-Type: application/json' -d '{
  "envelope":{"request_id":"demo-1","origin_vault":"delhi","query_type":"ENTITY_LOOKUP",
  "entity_keys":["ACCOUNT:AC7332214188","ACCOUNT:AC8168505423"],"timestamp":"2026-10-08T00:00:00Z",
  "signature":"(signed with demo-delhi)"}}'
```
**Preferred (signed automatically, from the backend):**
```bash
cd backend && .venv/bin/python - <<'PY'
from mesh import protocol, client
env = protocol.make_envelope("delhi","ENTITY_LOOKUP",
       ["ACCOUNT:AC7332214188","ACCOUNT:AC8168505423"],"demo-delhi")
print(client.fanout_entity_lookup("delhi", env["entity_keys"],
       "http://localhost:8000", {"delhi":"demo-delhi","mumbai":"demo-mumbai","jaipur":"demo-jaipur"}))
PY
```
→ `exchange 1 · all_verified True`
```
 mumbai: ACCOUNT:AC7332214188  → 4 FIN records   (FIN-000015, …)
 jaipur: ACCOUNT:AC7332214188  → 2 FIN records
         ACCOUNT:AC8168505423  → 3 FIN records
```
Judge line: *"Delhi asked; Mumbai and Jaipur answered with signed receipts **containing record
IDs only — no narratives, no names**. The switch stores receipts, never case data."*

### 2.8 Grounded query — connect, contact, own, anomaly, refuse
```bash
BASE="http://localhost:8001/api/query"
curl -s --get --data-urlencode 'q=how are Aniil Singh and Nehaa Kumaar connected'  $BASE
curl -s --get --data-urlencode 'q=who does Aniil Singh contact'                    $BASE
curl -s --get --data-urlencode 'q=what does Nehaa Kumaar own'                     $BASE
curl -s --get --data-urlencode 'q=any suspicious activity'                        $BASE
curl -s --get --data-urlencode 'q=is Zzark Zulu linked to anyone'                 $BASE
```
Verified answers:
```
connect  → intent:path · grounded:true · "2-step connection: Aniil Singh → PS Sadar Bazar, Kanpur → …" (cites E00156, E00187)
contact  → "…in contact with +916586518506, …, Manooj Shaikh (PH:7542784980) — 10 call records cited."
own      → "…linked to 6 asset(s) — accounts, vehicles, and the attributed phone. These are inferred attributions."
anomaly  → "7 analytical anomalies on file. Top: 6112805982 (comm burst); 9527758416 (comm burst); AC0076617711 (circular flow)…"
refuse   → intent:unknown · grounded:false · "Ask about the case graph, e.g. …" (refuses instead of inventing)
```

### 2.9 OCR — offline Devanagari, honest about its own errors
`POST /api/ocr/extract?auto=1` (multipart `file`, officer token) on a rendered Hindi FIR returned:
```
engine:tesseract-ocr · version tesseract 5.5.2 · lang hin+eng · n_chars 105
text: "प्राथमिकी: रमेश कुमार ने सुनीता देवी को
       फोन +9-8044997278 से घमकाया। …"      ← see the mis-read digit + म→घ? It reports as-is
extract: PHONE 8044997278 · ACCOUNT AC7234309805 · VEHICLE UP78GC4978  (recovered from context anyway)
```
Judge line: *"Offline, air-gapped Devanagari OCR; notice it tells you exactly how it read the
scan — including the digit it mangled. No external API, no silent correction."*

### 2.10 English→Hindi demo layer — offline, no LLM, and honest about it
Two gates on the workbench top bar: **हिंदी ✓** (toggles the whole graph, dossier card and
query answers into Devanagari) and the **Identity → हिंदी profile** panel on the left rail:
paste an English identity/profile and get the complete profile back in Devanagari.

`POST /api/hindi/transliterate` `{"texts":["Nehaa Kumaar","Sunita Devi","Karol Bagh","Delhi"]}`:
```
{"hindi":["नेहा कुमार","सुनिता देवी","करोल बाग़","दिल्ली"],
 "engine":"builtin-hindi-rules-v1", "disclosure":"English→Hindi demo layer: rule-based Devanagari
 transliteration + deterministic translation of the fixed UI vocabulary — offline, no neural model,
 no API. engine = builtin-hindi-rules-v1"}
```
`POST /api/hindi/profile` `{"fields":{name, husband_name, address, phone, account, vehicle, section}}`:
```
नाम: सुनिता देवी | पति का नाम: रमेश कुमार | पता: स-12 गलि, करोल बघ, नेव दिल्ली |
मोबाइल: +91-8044997278 | खाता: AC7234309805 | वाहन: UP78 GC 4978 | धारा: IPC 354D
```
Identifiers (phone / account / vehicle / date / IPC section) pass through verbatim; only labels and
names/addresses are transliterated. Query answers localize too — `GET /api/query?q=…&lang=hi` returns
```
2-चरणीय जुड़ाव: रकेशह कुमार → अनील सिंह → नेहा कुमार। हर चरण साक्ष्य के साथ उद्धृत है।
```
and `POST /api/resolve/person?lang=hi` adds a `hindi` block (name नेहा कुमार, roles आरोपित/
शिकायतकर्ता, aliases in Devanagari). The graph draws node labels and lane headers in Devanagari.
Judge line: *"Flip the toggle; the whole case reads in हिंदी. Everything is rule-based and disclosed —
same engine string on every response, no black box."*

---

## 3. The 30-second trust checks (Q&A backup)

```bash
curl -s http://localhost:8001/api/reviews/verify    # → ok:true
curl -s http://localhost:8001/api/warrants/verify   # → ok:true
curl -s http://localhost:8000/mesh/verify           # → ok:true
curl -s http://localhost:8001/api/security/posture  # graded endpoints · boot scan (40 files, 4 findings reported) · manifest check
curl -s http://localhost:8001/api/hindi/transliterate -H "Authorization: Bearer $TOK" -d '{"texts":["Delhi"]}'  # → दिल्ली, engine builtin-hindi-rules-v1
```
(`bash scripts/demo_data_check.sh` runs all 22 checks end-to-end; the Hindi beats make up four of them.)

## 4. Determinism & honesty notes for judges

- **Same answers every time:** the bench is `seed 42`-deterministic in *content* — persons, aliases,
  FIRs, phones, accounts, anomaly leads reproduce identically, so the answers and curls above hold.
  (Node ids are cluster-order artifacts and can shift ±a few; the check script never pins them.)
- **No real people:** deterministic synthetic FIR/CDR/FIN with planted ground truth (that's what
  makes honest precision claims possible).
- **The Hindi layer is also deterministic & offline:** rule-based Devanagari transliteration plus a
  fixed dictionary for the UI vocabulary — `builtin-hindi-rules-v1`, same output every run, no LLM.
- **Engine labels are literal:** `digilocker-ekyc-sim`, `bhashini-ondevice-sim`,
  `builtin-rule-romanizer`, `tesseract-ocr` — the response payload says which simulated bridge is
  in use; production adapters (API Setu DigiLocker / Bhashini / NIC PKI) are credential-layer swaps.
- **Full suite:** `cd backend && .venv/bin/python -m pytest -q` → **164 passed** (23 modules).