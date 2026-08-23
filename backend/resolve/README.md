# RAKSHAK backend — hybrid entity resolution

Phase 3 of the [roadmap](../README.md#roadmap): a deterministic, **dependency-free**
entity-resolution engine that links the noisy, multilingual mentions produced by
[`synthgen`](../README.md) back to their real-world entities, then scores itself against
the ground truth using the proposal's evaluation metrics (paper §9, §23).

It consumes only the **records** (`fir/cdr/fin.jsonl`); `mentions.jsonl`'s `true_id` is the
answer key and is read exclusively by the evaluator. **No real people or data are involved.**

## Run it

Requires Python 3.9+ (standard library only — nothing to install). Generate a benchmark first:

```bash
cd app/backend
python -m synthgen --seed 42 --out output        # Phase 2: make the data
python -m resolve  --in  output                   # Phase 3: resolve + evaluate
python -m resolve  --in  output --verbose         # + per-entity-type breakdown
python -m resolve  --in  output --out pred.json   # also dump predicted clusters
```

Run the tests (no dependencies — plain standard library):

```bash
python3 tests/test_resolve.py        # → "16/16 passed"
# or, if you have pytest installed:  pytest -q
```

## Results (paper §23)

Scored against the synthetic ground truth. All §23 targets are met on both the default
(50 people) and `large` (400 people) presets:

| Metric | Target | Default (seed 42) | Large (seed 3) |
| --- | --- | --- | --- |
| Pairwise Precision | > 0.85 | **0.998** | **0.946** |
| Pairwise Recall | > 0.80 | **0.999** | **0.999** |
| B-cubed F1 | — | 0.997 | 0.976 |
| False-Merge Rate | < 0.01 | **0.00002** | **0.00007** |
| False-Split Rate | < 0.05 | **0.0007** | **0.0006** |

Per-type: **PHONE / ACCOUNT / VEHICLE / LOCATION resolve at F1 = 1.0** (deterministic
identifiers); **PERSON** F1 ≈ 0.97, carrying all the difficulty (Devanagari, honorifics,
case, typos, name-order swaps, romanization variants).

> Numbers are reproducible: fixed seed + stdlib-only + no wall-clock in the pipeline. Regenerate
> with the commands above. Per the proposal's disclaimer, these are results **on the synthetic
> benchmark** — a real-data pilot is future work.

## How it works (paper §9)

For a candidate mention pair `(a, b)`, the aggregate score is a convex combination of
normalized similarity features (§8.3):  `s(a,b) = Σ wₖ·φₖ(a,b)`, `Σ wₖ = 1`. The decision is
**MATCH** if `s ≥ θ_high`, **REJECT** if `s ≤ θ_low`, else **UNCERTAIN** → routed to a
human-review queue (§9.3). Transitive closure over MATCH edges (union-find) yields clusters.

This MVP implements **4 of the 8** proposed features (§26); transliteration is applied as a
normalization step that feeds the name/phonetic features:

| Feature (§9.2) | Module | Notes |
| --- | --- | --- |
| **Identifier** — exact match on phone/account/vehicle/location | `io.deterministic_key` | E.164 digits, plate/account normalization. High-confidence certain merge. |
| **Name** — Levenshtein + Jaro-Winkler + char-n-gram cosine | `similarity.py` | Order-invariant token matching with a **weakest-link** rule (below). |
| **Phonetic** — Metaphone/Soundex tuned for Indian phonology | `phonetic.py` | Collapses `ph↔f`, `v↔w`, aspirates, doubled letters. |
| **Attribute** — age gap + address Jaccard | `features.phi_attr` | The disambiguator: splits same-name-different-person traps. |
| Transliteration (Devanagari→Latin, with schwa deletion) | `normalize.py` | Feeds name+phonetic so `मोहम्मद` compares to `Mohammad`. |

Deferred to Phase 4 (they need the temporal graph): **temporal** interval overlap,
**context** TF-IDF on co-occurring entities, and **graph-neighborhood** Jaccard.

### The weakest-link rule (why names don't chain)

A person match requires **every** name token to align, not just the average. Without this,
"Sana Singh" ~ "Sana Sheikh" ~ "Salman Sheikh" … bridge on a single shared token and
transitive closure collapses hundreds of unrelated people into one cluster. `token_set_ratio`
therefore blends the mean pair score with the **minimum** pair score. (Regression-tested in
`test_single_shared_token_does_not_bridge` and `test_scales_without_giant_bridge_cluster`.)

### Attribute disambiguation

Narrative person mentions inherit `age` / `address` from the structured complainant/accused
block of the *same FIR* whose name they best match — a lightweight, within-record form of the
proposal's co-occurring-context idea. When two confident name matches carry **conflicting**
attributes (disjoint addresses, or an age gap beyond the ±3 conflict noise), the merge is
vetoed — this is what separates the deliberate false-match traps. The residual merges (two
different "Ramesh Kumar"s whose mentions carry no distinguishing attributes) are exactly the
§24 ablation-A4 case — *false positives on common names without graph context* — and close in
Phase 4.

## Output

`python -m resolve` prints resolver stats (mention/cluster counts, MATCH/UNCERTAIN/REJECT
decision tallies, human-review-queue size) and the full §23 evaluation report. `--out`
writes the predicted clusters as `{cluster_id: [mention_id, …]}`, the same shape as
`ground_truth.json → clusters`, so downstream phases can consume resolved entities directly.

## Layout

```
backend/
  resolve/
    __init__.py     public API: load_benchmark, resolve, evaluate, ...
    __main__.py     CLI (python -m resolve)
    normalize.py    NFKC + honorific strip + abbreviation expand + Devanagari→Latin (schwa deletion)
    phonetic.py     Indian-tuned Metaphone/Soundex keys (blocking + φ_phonetic)
    similarity.py   Levenshtein, Jaro-Winkler, n-gram cosine, weakest-link token matching
    features.py     PersonRef + φ_name/φ_phonetic/φ_attr + §8.3 aggregate score & decision
    io.py           benchmark loader, deterministic identifier keys, attribute inheritance
    cluster.py      phonetic blocking + union-find (deterministic + probabilistic paths)
    evaluate.py     §23 metrics: pairwise & B-cubed P/R/F1, false-merge/split rate, per-type
  tests/test_resolve.py
```

## How this feeds the next phases

- **Phase 4 (Temporal Graph):** resolved clusters become entity **nodes**; CDR/FIN/FIR edges
  attach to them. The graph then supplies the deferred temporal/context/graph-neighborhood
  features, which feed back to split the remaining common-name merges.
- **Phase 5 (Anomaly):** anomaly detection runs over the resolved, typed graph.
