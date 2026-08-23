"""Tests for the entity-resolution pipeline (paper §9, §23).

Focus: (1) the normalization/transliteration/phonetic primitives collapse the
noise synthgen injects, (2) deterministic identifiers resolve exactly, (3) the
end-to-end resolver meets the §23 targets on the synthetic benchmark, (4)
reproducibility, and (5) the evaluator's own arithmetic is correct.

Run either way (no dependencies needed for the first one):
    python3 tests/test_resolve.py     # standalone runner
    pytest -q                         # if pytest is installed
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path

# make `resolve` and `synthgen` importable whether run standalone or under pytest
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from synthgen import GenConfig, generate            # noqa: E402
from resolve import evaluate, load_benchmark, resolve  # noqa: E402
from resolve.evaluate import _bcubed, _prf, _truth_label  # noqa: E402
from resolve.io import deterministic_key             # noqa: E402
from resolve.normalize import normalize_name, normalize_key, transliterate  # noqa: E402
from resolve.phonetic import phonetic_key            # noqa: E402
from resolve.similarity import jaro_winkler, levenshtein_ratio  # noqa: E402


# --------------------------------------------------------------------------- #
# unit: normalization / transliteration / phonetics
# --------------------------------------------------------------------------- #
def test_transliteration_deletes_final_schwa():
    assert transliterate("मोहम्मद").startswith("mohammad")
    assert "das" in normalize_key("दास")          # not "daasa"
    assert transliterate("Ram Prasad") == "Ram Prasad"   # latin passes through


def test_normalize_collapses_variants():
    # Each group is one real person written many ways. The design does NOT require
    # an identical normalized key (residual spelling drift is absorbed by fuzzy
    # scoring, §9) — it requires the scorer to MATCH every variant to the base.
    from resolve.features import PersonRef, score_pair
    groups = [
        ["Suresh Das", "सुरेश दास", "Sureshh Daas", "SURESH das"],
        ["Mohammad Arif", "Mohd Aarif", "Md Arif", "मोहम्मद आरिफ"],
        ["Neha Sharma", "Ms. NEHA Shharma", "नेहा शर्मा"],
    ]
    for g in groups:
        base = PersonRef.build("base", g[0])
        for variant in g[1:]:
            res = score_pair(base, PersonRef.build("v", variant))
            assert res.decision == "MATCH", f"{g[0]!r} vs {variant!r} → {res}"


def test_normalize_is_order_invariant():
    assert normalize_name("Ram Prasad") == normalize_name("Prasad Ram")


def test_honorifics_are_stripped():
    assert normalize_name("Sh. Ram Kumar") == normalize_name("Ram Kumar")
    assert normalize_name("Smt. Priya Verma") == normalize_name("Priya Verma")


def test_phonetic_matches_soundalikes():
    assert phonetic_key("Sharma") == phonetic_key("Sarma")
    assert phonetic_key("Verma") == phonetic_key("Varma")


def test_deterministic_key_normalizes_identifiers():
    assert deterministic_key("PHONE", "+91-98765-43210") == "9876543210"
    assert deterministic_key("PHONE", "+919876543210") == "9876543210"
    assert deterministic_key("VEHICLE", "UP78 GC 4978") == "UP78GC4978"
    assert deterministic_key("ACCOUNT", "AC 123 456") == "AC123456"


def test_similarity_bounds():
    assert levenshtein_ratio("abc", "abc") == 1.0
    assert 0.0 <= jaro_winkler("Singh", "Singhh") <= 1.0
    assert jaro_winkler("Khan", "Khan") == 1.0


def test_single_shared_token_does_not_bridge():
    # Regression: sharing ONE name token must NOT be a match, else transitive
    # closure chains unrelated people into one giant cluster (weakest-link rule).
    from resolve.features import PersonRef, score_pair
    for x, y in [("Sana Singh", "Sana Sheikh"),
                 ("Ramesh Kumar", "Ramesh Pandey"),
                 ("Anil Gupta", "Sunil Gupta")]:
        res = score_pair(PersonRef.build("a", x), PersonRef.build("b", y))
        assert res.decision != "MATCH", f"{x!r} vs {y!r} wrongly matched → {res}"


# --------------------------------------------------------------------------- #
# unit: evaluator arithmetic on a hand-built example
# --------------------------------------------------------------------------- #
def test_prf_math():
    r = _prf(tp=3, fp=1, fn=1)
    assert r["precision"] == 0.75 and r["recall"] == 0.75 and r["f1"] == 0.75


def test_bcubed_perfect_when_clusters_match():
    truth = {"a": "E1", "b": "E1", "c": "E2"}
    pred = {"a": "C1", "b": "C1", "c": "C2"}
    r = _bcubed(truth, pred, {"a", "b", "c"})
    assert r["precision"] == 1.0 and r["recall"] == 1.0 and r["f1"] == 1.0


def test_evaluator_detects_a_forced_false_merge():
    # truth: two singletons; pred: merged → precision must drop, recall stays 1
    truth = {"clusters": {"E1": ["a"], "E2": ["b"]},
             "entities": {"E1": {"type": "PERSON"}, "E2": {"type": "PERSON"}},
             "false_match_pairs": [["E1", "E2"]]}
    pred = {"clusters": {"C1": ["a", "b"]}}
    rep = evaluate(pred, truth)
    assert rep["pairwise"]["fp"] == 1
    assert rep["false_match_traps"]["merged"] == 1


# --------------------------------------------------------------------------- #
# end-to-end on the synthetic benchmark
# --------------------------------------------------------------------------- #
def _run(seed: int, tmp: Path) -> dict:
    generate(GenConfig(seed=seed), tmp)
    bench = load_benchmark(tmp)
    pred = resolve(bench)
    gt = json.loads((tmp / "ground_truth.json").read_text(encoding="utf-8"))
    return evaluate(pred, gt)


def test_meets_section23_targets():
    with tempfile.TemporaryDirectory() as t:
        rep = _run(42, Path(t))
        assert rep["pairwise"]["precision"] > 0.85, rep["pairwise"]
        assert rep["pairwise"]["recall"] > 0.80, rep["pairwise"]
        assert rep["false_merge_rate"] < 0.01, rep["false_merge_rate"]
        assert rep["false_split_rate"] < 0.05, rep["false_split_rate"]
        assert all(rep["targets"].values()), rep["targets"]


def test_deterministic_identifiers_are_perfect():
    with tempfile.TemporaryDirectory() as t:
        rep = _run(7, Path(t))
        for etype in ("PHONE", "ACCOUNT", "VEHICLE", "LOCATION"):
            if etype in rep["by_type"]:
                assert rep["by_type"][etype]["f1"] == 1.0, (etype, rep["by_type"][etype])


def test_resolution_is_reproducible():
    with tempfile.TemporaryDirectory() as t:
        d = Path(t)
        generate(GenConfig(seed=13), d)
        bench = load_benchmark(d)
        a, b = resolve(bench)["clusters"], resolve(bench)["clusters"]
        # same input → identical cluster contents (order-independent)
        norm = lambda c: sorted(sorted(v) for v in c.values())
        assert norm(a) == norm(b)


def test_every_scored_mention_is_covered():
    with tempfile.TemporaryDirectory() as t:
        d = Path(t)
        generate(GenConfig(seed=21), d)
        bench = load_benchmark(d)
        pred = resolve(bench)
        gt = json.loads((d / "ground_truth.json").read_text(encoding="utf-8"))
        # every truth mention (non-AMOUNT) must land in exactly one predicted cluster
        placed = [m for ms in pred["clusters"].values() for m in ms]
        assert len(placed) == len(set(placed)), "a mention appears in >1 cluster"
        truth_mids = set(_truth_label(gt))
        assert truth_mids <= set(placed), "some truth mention was never resolved"


def test_scales_without_giant_bridge_cluster():
    # LARGE preset stresses blocking + transitive closure. Precision must hold and
    # no single cluster may swallow a large fraction of all person mentions
    # (the single-token-bridge failure mode).
    from synthgen import LARGE
    with tempfile.TemporaryDirectory() as t:
        d = Path(t)
        generate(LARGE, d)
        bench = load_benchmark(d)
        pred = resolve(bench)
        gt = json.loads((d / "ground_truth.json").read_text(encoding="utf-8"))
        rep = evaluate(pred, gt)
        assert rep["pairwise"]["precision"] > 0.85, rep["pairwise"]
        assert rep["false_merge_rate"] < 0.01, rep["false_merge_rate"]
        n_person = pred["stats"]["person_mentions"]
        biggest = max(len(v) for v in pred["clusters"].values())
        assert biggest < 0.25 * n_person, f"giant cluster: {biggest} of {n_person} person mentions"


if __name__ == "__main__":
    import traceback

    tests = {k: v for k, v in sorted(globals().items())
             if k.startswith("test_") and callable(v)}
    passed = 0
    for name, fn in tests.items():
        try:
            fn()
            print(f"  ok    {name}")
            passed += 1
        except Exception:
            print(f"  FAIL  {name}")
            traceback.print_exc()
    print(f"\n{passed}/{len(tests)} passed")
    raise SystemExit(0 if passed == len(tests) else 1)
