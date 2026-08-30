"""Stalking-escalation detector tests (analytics/escalation.py + GET /api/escalation).

The benchmark plants STALKING_ESCALATION ground truth: stalker→complainant call
trajectories that rise week over week with night-time calls. These tests verify the
detector finds them, flags the victim-linked one CRITICAL, and does not fire on the
flat background noise of the random CDR stream.

    python3 tests/test_escalation.py   # standalone
    pytest -q tests/test_escalation.py
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient      # noqa: E402

import api.main as apimod                      # noqa: E402
from analytics.escalation import detect_escalation          # noqa: E402
from resolve.io import deterministic_key                     # noqa: E402


def _phone_key(number: str) -> str:
    return "PH:" + deterministic_key("PHONE", number)


class _Client:
    def __init__(self):
        self.bench = Path(tempfile.mkdtemp()) / "bench"
        apimod.BENCH_DIR = self.bench
        self.c = TestClient(apimod.app).__enter__()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.c.__exit__(None, None, None)
        return False


def test_planted_escalations_detected():
    with _Client() as t:
        bench = apimod.STATE["bench"]
        graph = apimod.STATE["graph"]
        alerts = detect_escalation(bench, graph)
        gt = json.loads((t.bench / "ground_truth.json").read_text())
        planted = [a for a in gt["planted_anomalies"] if a["kind"] == "STALKING_ESCALATION"]
        assert planted, "benchmark should plant escalation scenarios"
        hit = {a["caller_label"] for a in alerts} & {p["caller"] for p in planted}
        assert len(hit) >= 2, f"expected ≥2 planted escalations detected, got {hit}"
        # precision: no random noise pair should fire
        planted_callers = {p["caller"] for p in planted}
        fp = [a for a in alerts if a["caller_label"] not in planted_callers]
        assert not fp, f"false positives: {fp}"


def test_victim_linked_alert_is_critical():
    with _Client() as t:
        alerts = detect_escalation(apimod.STATE["bench"], apimod.STATE["graph"])
        crit = [a for a in alerts if a["severity"] == "CRITICAL"]
        assert crit, "expected ≥1 CRITICAL victim-linked escalation"
        assert all(a["victim_linked"] for a in crit)
        assert all("protected party" in a["reason"] for a in crit)
        # shield contract: the alert exposes phone numbers, never the victim's name
        victim_names = {n.label for n in apimod.STATE["graph"].nodes.values()
                        if n.type == "PERSON" and n.meta.get("role") == "victim"}
        for a in crit:
            assert not any(vn in a["reason"] for vn in victim_names)


def test_flat_pattern_not_flagged():
    # uniform call volume across weeks must never alert
    bench = {"cdr": [
        {"record_id": f"CDR-t{i}", "caller": "+918888888888", "receiver": "+917777777777",
         "timestamp": f"2026-01-{5 + i * 7:02d}T14:00:00", "duration_sec": 30,
         "tower": "X, Mumbai", "source": "CDR"}
        for i in range(6)
    ]}
    assert detect_escalation(bench) == []


def test_escalation_endpoint_shape():
    with _Client() as t:
        r = t.c.get("/api/escalation")
        assert r.status_code == 200
        d = r.json()
        assert d["total"] >= 2 and len(d["alerts"]) >= 2
        a = d["alerts"][0]
        for key in ("id", "caller", "receiver", "victim_linked", "weekly_counts",
                    "night_calls", "score", "severity", "reason", "evidence_record_ids"):
            assert key in a, f"missing {key}"
        assert "§14.2" in d["disclosure"]


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
