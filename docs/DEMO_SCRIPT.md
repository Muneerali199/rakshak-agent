# RAKSHAK-NET — The 5-Minute SIH Demo Script

_Rehearse this 20 times. Every step below is verified working on seed 42._
_Open: backend on :8000, frontend on :3000, route `/workbench`._

---

## The pitch in one breath

> "RAKSHAK-NET is India's first evidence-ledger criminal intelligence system.
> It **never lies** — answers come only from case evidence, never from a model's
> imagination. It **never forgets** — every human decision lives in a hash-chained,
> tamper-evident ledger. And it **never profiles the innocent** — victims are
> shielded by architecture, not by policy promises."

---

## Minute 0–1 · The problem (spoken, no screen)

"Ek trafficking victim ka FIR ek district mein hai. Money trail doosre mein. Call
records teesre mein. Aur accused ka naam teeno jagah alag likha hai — Hindi, English,
Hinglish. Aaj inhe jodne ka kaam haath se hota hai — ya hota hi nahi."

## Minute 1–2 · The lead finds you (auto-loaded case)

- Open `/workbench`. **It is already showing the circular money ring** —
  4 accounts, transfers cycling back within 7 days.
- Say: "This is how exploitation money moves. The system surfaced it; no analyst
  searched for it."
- **Time-travel:** drag the time slider at the bottom leftward — watch the ring
  *dissolve* (edges after that date vanish). Drag right — watch it **form again**.
  "In January the ring didn't exist. By March, it closed."

## Minute 2–3 · The query that cannot hallucinate (USP moment #1)

- In the query bar: `what does Aneel Sharmaa own?` (any accused name from the rail)
- Answer arrives **with citations**. Click any cited result → the edge opens in the
  evidence panel → the actual FIR record is shown, name highlighted, hash verified.
- Say: "Every word it says traces to a source document. Not a model's confidence —
  a document."

## Minute 3 · The refusal (USP moment #2 — THE moment)

- Query: `Sherlock Holmes`
- System: **"That entity is not in the case graph, so I cannot answer from evidence."**
- Say: "Har dusra AI is sawaal ka jawab *banaayega*. RAKSHAK mana kar deta hai.
  Police ka software jhooth nahi bol sakta."
- _(Let the room react. This is the screenshot moment.)_

## Minute 3–4 · Victim-shield (USP moment #3)

- Query a complainant's name (e.g. `who did Pandy Sanjay contact?` — pick any
  🛡-marked node in the graph)
- System: **"…is a protected party in this case. Victim data is pseudonymized and
  access-restricted under Women Safety Division policy."**
- Say: "Hum criminal ke network ko analyze karte hain. Victim ko kabhi nahi.
  Ye policy nahi hai — architecture hai. Code mein likha hua hai."

## Minute 4–5 · The ledger (USP moment #4)

- Click any dashed (inferred) edge → evidence panel opens → press **REJECT**.
- Point to the badge: **⛓ ledger verified · N chained records**.
- Say: "Every human decision is hash-chained to the previous one. Koi bhi history
  badalne ki koshish kare — ek byte bhi — chain toot jaati hai aur system bata deta
  hai. Blockchain ka promise, bina blockchain ke. Stdlib Python pe, air-gapped."
- _(If asked to prove it: `curl localhost:8000/api/reviews/verify` shows
  `{ok: true}`; edit a row in `output/reviews.db` and it shows the first broken id.)_

## Bonus (if time) · The adversarial test

- `POST /api/resolve` with a planted false-match twin pair (names nearly identical,
  address conflicts) → system says **UNCERTAIN/NON_MATCH** and routes to review.
- Say: "Criminals naam badalke system ko dhokha dene ki koshish karenge.
  Humne wo attack pehle se benchmark mein daala hai — aur ye usse pakadta hai."

## Bonus (if time) · RakshakAI scanner (30 seconds, side-mention)

- "We even scan our own codebase." → `/scanner`, paste the sample, CWE-89 CRITICAL.
- One line only — do NOT dwell; the workbench is the star.

---

## Fallbacks (murphy-proofing)

| If it breaks | Do this |
|---|---|
| Backend down | Screenshots: `query-live.png`, `scanner-final.png` in repo root |
| Query typo finds nothing | Use the exact names from this script (seed-42 verified) |
| Slider empty | Depth 2 must be selected (demo step 1 sets it) |
| Judge asks "real data?" | "Schema mirrors CCTNS FIR/CDR/FIN formats — integration is mapping, not re-architecture. Synthetic benchmark is disclosed and deliberate: it's what lets us measure precision honestly." |
| Judge asks "LLM kyun nahi?" | "Serving path mein LLM jaan-boojhke nahi hai — LLM hallucinate karta hai, aur police software jhooth nahi bol sakta. Templates deterministic hain." |

---

## The closing line

> "This is not a dashboard. This is a witness stand for the AI age —
> every claim cited, every decision chained, every victim shielded."
