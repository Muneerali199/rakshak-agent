# RAKSHAK backend — synthetic benchmark generator

Phase 2 of the [roadmap](../README.md#roadmap): a deterministic, **dependency-free** generator that
produces synthetic **FIR / CDR / FIN** records with the real-world noise the proposal calls for
(paper §21) — plus complete **ground truth** for evaluation.

Since official law-enforcement data isn't public (and shouldn't be used), this is the substrate every
downstream phase is built and measured against: entity resolution, the temporal knowledge graph, and
anomaly detection. **No real people or data are involved.**

## Run it

Requires Python 3.9+ (standard library only — nothing to install).

```bash
cd app/backend
python -m synthgen --seed 42 --out output          # default size (~460 records)
python -m synthgen --preset large --out output_lg  # ~8k records
python -m synthgen --seed 42 --fir 100 --cdr 1000 --fin 300 --out custom
```

Run the tests (no dependencies — plain standard library):

```bash
cd app/backend
python3 tests/test_synthgen.py        # → "7/7 passed"
# or, if you have pytest installed:  pytest -q
```

## What noise it reproduces (paper §21.1)

| Noise type | How it shows up |
| --- | --- |
| Transliteration variation | `Mohammad` / `मोहम्मद` / `Mohd` / `Muhammad` for one person |
| Spelling drift | char swap/drop/double + `ph↔f`, `aa↔a`, `v↔w` substitutions |
| Duplicate entities | the same person recurs across records under different surface forms |
| **False matches** | two *different* people with an identical name (hard negatives) |
| Missing data | age / address dropped at `missing_rate` |
| Conflicting data | reported age differs from the true age across sources |
| Evolving identifiers | a person switches phone number mid-timeline |
| Noisy addresses | `H.No` / `Rd` / `gali` abbreviations, dropped house numbers |
| Money notation | `₹1,50,000` / `1.5 lakh` / `Rs. 150000` / `INR 150000` |
| Irrelevant entities | people who appear once, disconnected (background noise) |

## Output files

| File | Contents |
| --- | --- |
| `fir.jsonl` | First Information Reports — structured fields + a multilingual `narrative` (en / hi / hi-en) |
| `cdr.jsonl` | Call Detail Records — caller/receiver numbers (respecting evolving phones), timestamp, tower |
| `fin.jsonl` | Financial transfers — accounts, banks, noisy `amount_raw`, timestamp (includes circular flows) |
| `mentions.jsonl` | **Ground truth for entity resolution:** one row per entity occurrence, with its true id |
| `ground_truth.json` | Canonical entities, mention clusters, false-match pairs, evolving identifiers |
| `manifest.json` | Seed, full config, counts, and a SHA-256 per file (tamper-evident, à la the paper's audit hash) |

### The ground-truth convention

Input records are deliberately **noisy and unlabeled** — a pipeline ingests only `*.jsonl` records.
The *answers* live separately:

- **`mentions.jsonl`** — every place an entity is referenced becomes a row:
  ```json
  {"mention_id": "FIR-m00007", "source": "FIR", "record_id": "FIR-2026-0001",
   "field": "narrative", "entity_type": "PERSON", "surface": "Mohd Arif",
   "true_id": "P0003", "span": [24, 33], "normalized": null}
  ```
  `span` gives exact character offsets into the narrative (so it doubles as an **NER** benchmark);
  `normalized` carries the canonical value for `AMOUNT` mentions.

- **`ground_truth.json → clusters`** maps `true_id → [mention_id, …]`. Entity resolution is scored by
  comparing predicted mention clusters against these (Precision / Recall / F1, False Merge / Split
  rate — paper §23). `false_match_pairs` are the traps a naive name-matcher will wrongly merge.

`true_id`s encode ownership: `P0003` (person) owns `P0003-PH1` (phone), `P0003-AC1` (account),
`P0003-V1` (vehicle) — so graph-construction ground truth is derivable directly.

## How this feeds the next phases

- **Phase 3 (Entity Resolution):** ✅ implemented — see [`resolve/`](resolve/README.md). Consumes
  `*.jsonl`, predicts clusters, scores against `clusters` (all §23 targets met).
- **Phase 4 (Temporal Graph):** 🌱 seeded — see [`graph/`](graph/build.py). CDR→`CONTACTED`,
  FIN→`TRANSFERRED_TO`, FIR→`LOCATED_AT` (3 MVP layers), plus inferred `ASSOCIATE_OF` / `USES`;
  resolved entities become nodes; every edge carries provenance + a SHA-256 audit hash (Algorithm 3).
- **Phase 5 (Anomaly):** the injected circular fund flows and call bursts are the positives to detect.

## API layer (serves the Investigator Workbench)

The [`api/`](api/main.py) package exposes the resolver + graph over HTTP (FastAPI). This is the only
part with third-party deps; the core packages stay stdlib-only.

```bash
cd app/backend
pip install -r api/requirements.txt
uvicorn api.main:app --reload --port 8000     # OpenAPI docs at http://localhost:8000/docs
```

| Endpoint | Backed by |
| --- | --- |
| `POST /api/resolve` | `resolve.features.score_pair` (real — the 4-feature breakdown) |
| `GET /api/graph/subgraph` | `graph.build_graph` neighborhood, layer-filterable |
| `GET /api/evidence/{edge_id}` | source-doc snippet + live SHA-256 verification |
| `GET /api/entities`, `/api/health` | UI convenience (risk-ranked list; liveness) |

## Layout

```
backend/
  synthgen/         Phase 2 — synthetic benchmark generator
    __init__.py     public API: GenConfig, LARGE, build_world, generate
    __main__.py     CLI (python -m synthgen)
    config.py       GenConfig knobs + LARGE preset
    pools.py        curated Hindi/English names (+ Devanagari), places, banks, IPC, RTO series
    variants.py     surface-form noise (transliteration, typos, honorifics, money notation)
    entities.py     ground-truth world: Person/Phone/Account/Vehicle/Location + build_world
    records.py      FIR / CDR / FIN synthesis with per-mention ground truth
    generate.py     orchestration + file writing + manifest
  resolve/          Phase 3 — hybrid entity resolution + §23 evaluation (see resolve/README.md)
  graph/            Phase 4 seed — 3-layer temporal graph with provenance + SHA-256 (Algorithm 3)
  api/              FastAPI service (POST /api/resolve, GET /api/graph/subgraph, /api/evidence)
  tests/
    test_synthgen.py  test_resolve.py  test_graph.py  test_api.py
  conftest.py
  requirements.txt
```

