"""Anomaly detection tests (paper §14, Algorithm 6).

Focus: (1) the planted circular fund flows are caught (ring-level recall), (2) the
temporal filter kills coincidental random cycles (precision), (3) call bursts are
caught, (4) the API serves anomalies with labels + the benchmark self-evaluation.

    python3 tests/test_analytics.py   # standalone
    pytest -q tests/test_analytics.py
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from analytics import detect_anomalies, evaluate_anomalies   # noqa: E402
from synthgen import GenConfig, generate                     # noqa: E402
from resolve import load_benchmark                           # noqa: E402


def _bench(seed: int):
    with tempfile.TemporaryDirectory() as t:
        generate(GenConfig(seed=seed), Path(t))
        bench = load_benchmark(Path(t))
        gt = json.loads((Path(t) / "ground_truth.json").read_text(encoding="utf-8"))
        return bench, gt["planted_anomalies"]


def test_all_planted_cycles_detected_with_no_false_cycles():
    bench, planted = _bench(42)
    found = detect_anomalies(bench)
    ev = evaluate_anomalies(found, planted)
    cyc = ev["CIRCULAR_FLOW"]
    assert cyc["recall"] == 1.0, f"missed planted rings: {cyc}"
    assert cyc["precision"] == 1.0, f"coincidental cycles leaked through: {cyc}"


def test_all_planted_call_bursts_detected():
    bench, planted = _bench(42)
    found = detect_anomalies(bench)
    ev = evaluate_anomalies(found, planted)
    burst = ev["COMM_BURST"]
    assert burst["recall"] == 1.0, f"missed planted bursts: {burst}"
    assert burst["precision"] == 1.0, f"false burst alarms: {burst}"


def test_anomalies_sorted_by_severity_with_ids():
    bench, _ = _bench(42)
    found = detect_anomalies(bench)
    assert found, "expected anomalies on the seeded benchmark"
    sevs = [a["severity"] for a in found]
    assert sevs == sorted(sevs, reverse=True)
    assert [a["id"] for a in found] == [f"ANOM-{i + 1:03d}" for i in range(len(found))]


def test_cycle_anomalies_carry_evidence_records():
    bench, planted = _bench(42)
    found = [a for a in detect_anomalies(bench) if a["kind"] == "CIRCULAR_FLOW"]
    assert found
    for a in found:
        assert len(a["evidence_record_ids"]) >= 3      # one FIN record per cycle leg
        assert all(r.startswith("FIN-") for r in a["evidence_record_ids"])


def test_api_anomalies_endpoint():
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    import api.main as apimod
    from fastapi.testclient import TestClient

    apimod.BENCH_DIR = Path(tempfile.mkdtemp()) / "bench"
    with TestClient(apimod.app) as c:
        r = c.get("/api/anomalies")
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["anomalies"], "endpoint returned no anomalies"
        a = d["anomalies"][0]
        assert {"id", "kind", "entity_id", "label", "severity", "reason"} <= set(a)
        assert "not a determination of criminality" in d["disclosure"]
        assert d["evaluation"] is not None             # benchmark self-test included
        assert d["evaluation"]["CIRCULAR_FLOW"]["recall"] == 1.0
        # every anomaly entity exists in the graph so the UI can focus it
        for a in d["anomalies"]:
            assert a["label"] != a["entity_id"] or a["entity_type"] == "UNKNOWN"


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
