"""Experiment A baseline-comparison tests (paper §22, §24).

The claim the deck makes: the hybrid resolver beats exact and fuzzy-only baselines
on the same seed-42 ground truth — and specifically survives the identical-name
false-match twins that the simple baselines merge.

    python3 tests/test_experiment_a.py   # standalone
    pytest -q tests/test_experiment_a.py
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from experiments.experiment_a import run            # noqa: E402
from resolve import load_benchmark                  # noqa: E402
from synthgen import GenConfig, generate            # noqa: E402


def _results():
    tmp = tempfile.mkdtemp()
    generate(GenConfig(seed=42), Path(tmp))
    bench = load_benchmark(Path(tmp))
    gt = json.loads((Path(tmp) / "ground_truth.json").read_text(encoding="utf-8"))
    return run(bench, gt)


def test_hybrid_has_best_f1():
    res = _results()
    f1 = {k: v["pairwise"]["f1"] for k, v in res.items()}
    assert f1["hybrid"] >= f1["exact"], f"exact beats hybrid: {f1}"
    assert f1["hybrid"] >= f1["fuzzy"], f"fuzzy beats hybrid: {f1}"
    assert f1["hybrid"] > 0.95


def test_fuzzy_baseline_merges_more_traps_than_hybrid():
    res = _results()
    traps = {k: v["false_match_traps"]["merged"] for k, v in res.items()}
    # the whole point of the attribute veto: identical names ≠ identical people
    assert traps["fuzzy"] >= traps["hybrid"], f"hybrid merged more twins than fuzzy: {traps}"
    assert traps["hybrid"] < res["hybrid"]["false_match_traps"]["total"], "hybrid fell for every trap"


def test_hybrid_meets_paper_targets():
    res = _results()
    targets = res["hybrid"]["targets"]
    assert all(targets.values()), f"§23 targets missed: {targets}"


def test_api_experiment_endpoint():
    import api.main as apimod
    from fastapi.testclient import TestClient

    apimod.BENCH_DIR = Path(tempfile.mkdtemp()) / "bench"
    with TestClient(apimod.app) as c:
        r = c.get("/api/experiments/a")
        assert r.status_code == 200, r.text
        d = r.json()
        assert {"exact", "fuzzy", "hybrid"} <= set(d["results"])
        assert d["results"]["hybrid"]["pairwise"]["f1"] >= d["results"]["fuzzy"]["pairwise"]["f1"]
        assert "honestly labeled" in d["disclosure"]


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
