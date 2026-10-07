# Q&A Cheat Sheet — Competitors & Research (Grand Finale)

> **How to use:** Part A = competitor landscape (who they are, one-line counter each).
> Part B = research anchors (who did what, in plain words). Part C = drill questions.
> Part D = verify-before-you-quote list.
>
> **Golden rule:** never overclaim. The deck's honesty is the moat — if asked about a
> name you're not sure of, say "aap chahein toh main exact citation verify karke bhej
> doon" instead of guessing.

---

## 0 · Positioning one-liner (say this first, always)

> **"RAKSHAK-NET is the intelligence layer on top of CCTNS — constitutional by design
> (mesh, not a central database), Indic by default (Hindi / English / Hinglish), and
> court-ready (every claim source + hash traceable). A direct competitor that does all
> three together — that product does not exist today."**

Three differentiators, memorise as **M-I-E**: **M**esh (legal) · **I**ndic (usable) ·
**E**vidence-chain (admissible).

---

## Part A — Competitor landscape (4 rings)

### Ring 1 — The status quo: CCTNS itself
- **Kya hai:** government's own system (since 2009) — digitises FIRs at ~17,798 police
  stations; station/district-level search and reports.
- **Kyun kaafi nahi:** siloed per district, no cross-case link analysis, no entity
  resolution across scripts, no cross-state view. It's a *record system*, not an
  *intelligence system*.
- **Counter (say):** *"Hum CCTNS ko replace nahi karte — uske upar intelligence layer
  hain, aur usi CCTNS intranet par deploy hote hain. Zero new national infrastructure."*

### Ring 2 — Government integration rails (adjacent, not analytics)
- **ICJS / ICJS 2.0 (MHA)** — connects e-Courts, e-Prisons, e-Prosecution, CCTNS for
  data exchange between justice pillars. It's *plumbing*, not intelligence.
- **NCRB (Crime in India reports)** — statistics; source of our impact numbers.
- **Inter-state sharing initiatives (e.g. SAMANVAY —⚠️ verify name)** — data-sharing
  portals; still no linking/ER layer.
- **State field apps (UP Police Trinetra-type —⚠️ verify specifics)** — field search /
  verification; not network analysis, not cross-state.
- **Counter:** *"Integration rails bhi humein chahiye — hum unke upar analytics + ER +
  evidence chain laate hain."*

### Ring 3 — Foreign commercial SaaS (the realistic "buy instead of build" question)
| Player | What it is | Our counter |
| --- | --- | --- |
| **Palantir (Gotham)** | US intel analytics — centralises data at scale | Data centralisation legally dead on arrival for Indian policing (State subject); sovereignty/procurement; no Indic ER. |
| **IBM i2 Analyst's Notebook** | Desktop link-analysis tool, manual charts | Manual, licensed, English-first; no automatic Indic ER, no mesh, no hash-ledger. |
| **Cognyte / Babel Street / PenLink-type** | Security analytics / OSINT & web-intel suites | Centralised cloud or vendor-hosted; data-residency and DPDP issues; not FIR-centric. |
| **Quantexa / Senzing-type** | Entity-resolution + network analytics (finance/gov) | Closest capability cousins — but commercial, domain-fit for banking/fraud, no warrant gate, no Indian legal model. |
| **Neo4j / Linkurious** | Graph DB + visualisation (raw tooling) | Tools, not a system — no ER, no evidence chain, nothing compliant out of the box. |

**Counter (one line):** *"Foreign tools assume a centralised data lake. We deliberately
built the opposite — mesh-first, so the legal boundary is the architecture, not a
settings screen."*

### Ring 4 — Surveillance-state model: China's IJOP
- China's Integrated Joint Operations Platform: linking capability **without rights or
  accountability** (Xinjiang deployments).
- **Counter (deck line):** *"China's IJOP had the detection capability — without the
  rights or accountability. We inverted it: same linking power, rights-first —
  warrant-gated, ledgered, district-sovereign."*

### Ring 5 — The SIH floor (other teams)
Typical competitor-team pitches: **centralised DB + LLM chatbot**, **face
recognition**, **heatmap / predictive policing**, **video analytics** (Staqu-type
vendors do the video game — different problem).
- **Counter:** *"Most teams demo a model. We demo a deployable legal system — 142
  tests, live 3-vault mesh, warrant gate, hash-chained ledgers. Our AI is where it's
  safe; our determinism is where failure is irreversible."*

---

## Part B — Research anchors (who did what — plain words)

### The 9 on the deck (say *why* each one, not just its name)
| # | Who / when | What it actually is | Our use — one line |
| --- | --- | --- | --- |
| 1 | **Rossi et al. (2020)** — Twitter + Imperial College | **TGN** — deep learning on *dynamic* graphs (edges change over time) | Why every edge in our graph is **timestamped** — temporal evolution is the research basis; the *model* stays out of the serving path. |
| 2 | **De Domenico et al. (2013)** — multilayer-networks physics group | Mathematical formulation of **multilayer networks** | Why we have **3 layers (communication · financial · spatial)** instead of one flat graph. (3 more planned.) |
| 3 | **Ribeiro et al.** — GNN criminal-network study | **GNNs vs classical algorithms** for criminal community detection | Our *baseline citation* — GNNs are possible; we chose **classical/deterministic** for auditability. |
| 4 | **Christen (2012)** — Peter Christen (book: *Data Matching*) | The canonical **record-linkage / entity-resolution** text (formalises **Fellegi–Sunter** scoring) | Our **4-feature hybrid ER scorer** is formalised from this; also blocking + thresholds. |
| 5 | **Beniwal & Singh (2023)** — COMI-LINGUA | Benchmark dataset for **Hinglish code-mixed NLP** | Baseline for our **Hinglish NER** handling (करोल बाग मार्केट-style mixed text). |
| 6 | **AI4Bharat (IIT Madras) & Bhashini (GoI)** | **IndicXlit** (transliteration, 21 Indic languages) + **IndicNER** | Cross-script names: *Mohd ↔ मोहम्मद*; on this demo box the **builtin-rule-romanizer** runs — disclosed, same switch. |
| 7 | **Ying et al. (2019)** — Stanford (Jure Leskovec group) | **GNNExplainer** — explaining GNN predictions | Conceptual basis for our **Evidence Panel**: show *why* a link exists, not just that it does. |
| 8 | **Yuan et al.** — Human-in-the-Loop AI research | Why humans must stay in the decision loop | Research backing our **mandatory accept/reject review** — every decision hash-chained. |
| 9 | **RakshakAI (2025)** — our own | Qwen2.5-Coder-14B LoRA, published (HF) | Secures **our own platform's code** — off the critical path, never gates demo actions. |

### Classical foundations (if a professor-judge digs deeper)
- **Fellegi–Sunter (1969)** — the original probabilistic record-linkage model → our ER scorer's ancestor.
- **COPLINK (Hsinchun Chen, Univ. of Arizona, ~2003)** — the famous US police data-mining
  system: ER + network analysis, but **centralised**. *"We build the India-first,
  privacy-first successor: same capability, mesh constitution."*
- **Louvain (Blondel et al. 2008) / betweenness centrality (Freeman 1977)** — classical
  community detection & hub measures → our deterministic **★ key-influencer score**
  (distinct neighbours × layer-breadth) is auditable against these classics.

### Legal / policy research (our "law as design" citations)
| Instrument | Why it matters to us |
| --- | --- |
| **Puttaswamy (2017)** — 9-judge privacy judgment | Privacy is fundamental → local processing, warrant gate. |
| **DPDP Act 2023** | Purpose limitation, minimisation → district vaults, no central store. |
| **DEPA / Account Aggregator (RBI)** | Consent-architecture model → our **dual-signed, scoped, expiring warrant**. |
| **BNS / BNSS 2023** (IPC/CrPC replacements) | New criminal codes → stalking = BNS ~78 (was IPC 354D); lawful data requests. |
| **Telegraph Act / IT Act s.69 / IT Rules 2021 / PMLA** | The *legal channels* for CDR / social-media metadata / financial trails (Q9). |

### The impact numbers (source them like a researcher)
| Number (deck) | Source to say |
| --- | --- |
| 58.8 L FIRs (2024) | NCRB, *Crime in India 2024* |
| 17,798 police stations, 100% on CCTNS | PIB, Feb 2026 |
| 1,210/day crimes vs women · 4.48 lakh (2023) | NCRB |
| 29.2% IPC cases pending probe · 93.9% rapes: known to victim | NCRB |
| one stalking FIR every ~55 min | *Derived* from daily count — be ready to show the math |
| BNS ~78 (was IPC 354D) | New criminal code mapping |

---

## Part C — Drill questions (rehearse out loud)

**C1. "CCTNS already exists — what exactly is new?"**
> "CCTNS digitised records; it doesn't *connect* them. We add the intelligence layer
> on the same intranet: cross-script entity resolution, cross-district linking via
> signed mesh queries, and a court-admissible evidence chain. No new infrastructure,
> no central database."

**C2. "Why not just buy Palantir / i2?"**
> "Those tools assume a centralised data lake — legally impossible here because
> policing is a State subject, plus sovereignty and data-residency issues. We built
> mesh-first so the legal boundary is the architecture. Same linking power, deployable
> where centralised tools are not."

**C3. "China's IJOP does this at scale. How are you different?"**
> "IJOP proved the capability without the rights. We inverted it: every unmask is
> warrant-gated — dual-signed, scoped, expiring — every exchange lands in a
> hash-chained ledger, and records never leave the district. Capability same,
> accountability built-in."

**C4. "What research is this based on?"**
> "Four pillars: Christen's record-linkage formalisation for entity resolution;
> multilayer-network theory (De Domenico) for our 3 layers; temporal graph research
> (Rossi) for timestamped edges; and HITL research for mandatory human review. Plus
> Indic NLP from AI4Bharat/Bhashini for transliteration."

**C5. "Which algorithms — any deep learning?"**
> "Deterministic in the serving path, deliberately: hybrid ER scoring, graph
> neighbourhood scoring for the ★ influencer, provenance counting for repeat
> offenders. GNNs and LLMs are cited and one 14B advisory exists, but identity
> merges are irreversible — explainability beats accuracy where failure is costly."

**C6. "Other teams also show graphs — what's actually different?"**
> "Most pitches are a model or a dashboard. Ours is a *deployable legal system*:
> 142 tests passing, live 3-vault mesh, warrant gate, hash-chained ledgers, blindspot
> honesty in every report. You can audit the stack a judge is seeing."

**C7. "What's your moat / defensibility?"**
> "The legal design, not the model: mesh constitution, warrant consent architecture,
> evidence chain — and the Indic ER tuned on code-mixed Hinglish. A big vendor can't
> copy the constitutional stance without redesigning their whole product."

**C8. "Research says temporal/link prediction — do you do that?"**
> "We timestamp every edge — that's the temporal foundation. Link *prediction* stays
> out of the serving path: we show leads with sources, we don't predict guilt.
> Planned, advisory-only, in the roadmap."

**C9. "Entity resolution accuracy — paper benchmark?"**
> "Formalised from Christen's blocking + Fellegi–Sunter-style scoring. Our own
> benchmark is planted-ground-truth (F1 0.9935, false-merge 6/100k) — honest caveat:
> real-data pilot is Phase 5. The metric we care about is **false merges** because
> they're irreversible."

**C10. "If you had to name one competitor product closest to you?"**
> "Quantexa/Senzing-type ER+network analytics — capability cousins for banks. But no
> warrant gate, no Indian legal model, no FIR-centric mesh. And COPLINK proved this
> category two decades ago — centralised. We're its privacy-first successor."

**C11. "How do you verify officers / prevent impersonation? (DigiLocker e-KYC drill)"**
> "Every write to the graph is bound to a DigiLocker e-KYC verified session,
> delivered over API Setu — the officer's Aadhaar + OTP runs through the e-KYC
> channel and a consent artifact is issued. Raw Aadhaar is never stored — masked
> last-4 + an identity token — and the session token expires in 8 hours. Here's
> the part a judge can *test*: the backend reads rank from the signed token. If we
> log in as Inspector Malhotra (IO) and try to countersign a warrant, the API
> returns 403 — rank ≥ 3 required. Self-approval is blocked the same way. Every
> consent, login, denial, and logout lands in a hash-chained auth ledger."
> **Sim creds for the judge** (synthetic): IO `officer.DEL-001` `700011771177`/`771177`;
> SP `officer.DEL-003` — values visible in the UI and from `GET /api/auth/officers`.
> Be explicit that the handshake is simulated offline (`bridge: digilocker-ekyc-sim`)
> and says so; live DigiLocker/API Setu needs an API Setu agency account.

---

## Part D — Verify before quoting (do a 5-min check)

| Item | Why |
| --- | --- |
| **SAMANVAY** (NCRB inter-state sharing) | Confirm exact name/status on PIB before naming it. |
| **UP Police Trinetra** specifics | Confirm what it actually does (field search) before citing. |
| **State app examples** | Use only the one or two you verify. |
| **NCRB / PIB numbers** | Match the deck's citation years exactly (2024 report, Feb 2026 PIB). |
| **Palantir/i2/Cognyte one-liners** | Safe as category statements; don't invent deployments in India. |

> If a judge asks about anything in Part D you haven't verified — pivot:
> *"The category point stands: centralised foreign tools aren't legally deployable for
> Indian policing. I'll verify the specific deployment detail if you'd like a follow-up."*
