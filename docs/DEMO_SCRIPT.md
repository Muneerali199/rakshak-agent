# RAKSHAK-NET — The 5-Minute SIH Demo Script (Mesh Edition)

_Rehearse 20 times. Everything below is verified live on seed 42._
_Run: `app/scripts/run_mesh.sh` → gateway :8000, vaults :8001-03, UI :3000._

---

## The pitch in one breath

> "UPI ne banks ko centralize nahi kiya — interoperable banaya. Account Aggregator
> ne data share karwaya — bina store kiye. RAKSHAK-NET wahi cheez police districts
> ke liye hai: **data apne district mein rehta hai, signed queries travel karti
> hain, aur har protected access ek dual-signed warrant ke peeche hota hai.**"

---

## Minute 0–1 · The legal trap (spoken)

"Policing India mein STATE subject hai — Seventh Schedule. Ek central national
crime database **legally possible hi nahi**. Isliye baaki solutions demo ke baad
deploy nahi ho sakte. Humne wo architecture banaya jo actually deploy ho sakta
hai — kyunki India ne ise do baar prove kiya hai: UPI aur Account Aggregator."

## Minute 1–2 · THE UPI MOMENT — FIR in, mesh out

- **＋ File FIR** → **load sample** → **Ingest into case graph**
- Watch three things land:
  1. Entities highlighted **inline in the FIR text** (auditable, zero LLM)
  2. Cross-case linkage alerts
  3. **DISTRICT VAULT MESH**: *"Query travelled, data didn't — each vault signed
     its answer. All receipts verified ✓"* — Mumbai vault: phone in 3 records;
     Jaipur vault: account in 11 records — **with signed receipts**
- Say: *"Ye receipt NPCI switch ki tarah hai — gateway ne sirf query route ki,
  case data kabhi district chhod ke nahi gaya. Aur har exchange hash-chained
  ledger mein hai."*

## Minute 2–3 · Escalation — next FIR se PEHLE

- Left rail, red panel: **Escalating contact** → CRITICAL row
- `1 → 1 → 3 → 5 calls/wk` sparkline + **2 night** + *"receiver is a complainant
  on record · shielded"*
- Say: *"System ne curve dekhi, file nahi. Intervention ka window — assault se pehle."*

## Minute 3–4 · THE WARRANT GATE — constitutional AI, live

- Click a **shielded** entity (purple 🛡) → click its edge → evidence panel:
  *"[PROTECTED VICTIM]…"*
- Click **🔏 request access** → modal:
  1. IO requests (id, rank, reason) → **Request warrant**
  2. Senior officer countersigns (different person, SP+) → **Countersign & unmask**
- Identity reveals + banner: *"Unmasked under warrant W-XXXX — dual-signed,
  scoped, expiring, hash-chained."*
- Say: *"China ke IJOP mein bhi superior approval tha — par proof nahi. Humne
  DEPA ka consent artifact police ke liye banaya: scoped, revocable, aur har
  access ledger pe. Victim ka data access karna ek legal action hai, click nahi."*
- Bonus: try self-approval → *"self-approval is not permitted"* (four-eyes, in code)

## Minute 4–5 · The court artifact + the honesty layer

- **⎙ report** → the evidence chain, now with:
  - **Jurisdiction chain** — signed mesh exchanges behind cross-district links
  - **Protected-data access log** — the warrant events (who asked, who signed)
  - **Blindspots — what this report cannot establish** (corroboration score)
- Say: *"Baaki AI apna confidence dikhate hain. Hum apni kami dikhate hain.
  Court ke liye dono chahiye."*

## The trust proofs (30 sec, Q&A backup)

1. **Never lies**: query `Sherlock Holmes` → "not in the case graph"
2. **Never tampers**: `/api/reviews/verify` + `/api/warrants/verify` + `/mesh/verify` → all `ok:true`
3. **Audits itself**: `/api/security/posture` → boot self-scan (hash-chained),
   code manifest, graded endpoint levels — *"system jo khud audit karta hai"*

## Closing line

> "China surveil kar sakta hai. Estonia share kar sakta hai. Sirf India —
> UPI aur DEPA ke desh — dono kar sakta hai, constitutionally. Ye hai wo system."

---

## Fallbacks

| If it breaks | Do this |
|---|---|
| Mesh vault down | Receipts card shows `unreachable` honestly; single-node story continues. Screenshots: `mesh-fir-live.png`, `warrant-gate-live.png` |
| "Real data?" | "Schema mirrors CCTNS FIR/CDR/FIN. Synthetic benchmark is deliberate — it's what lets us measure precision honestly (full-bench: cycles P100/R100, bursts P100/R100)." |
| "Per-vault eval varies?" | "Smaller districts see noisier statistics — exactly why corroboration scores and human review exist." |
| "HMAC isn't PKI" | "Demo secrets stand in for NIC-issued certificates — the protocol shape is what's being demonstrated." |
| "Critical vulns in your own scan?!" | "Two flags — both in the scanner's own rule table and a docstring example. Every alert is a lead for a human, never a verdict — same philosophy as the crime side." |
| "LLM kyun nahi?" | "Serving path mein LLM jaan-boojhke nahi — police software hallucinate nahi kar sakta. IndicXlit (AI4Bharat) adapter integrated for transliteration; demo offline." |
