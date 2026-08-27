"""Human-in-the-loop review persistence tests (paper Algorithm 8).

Exercises POST /api/review end-to-end via TestClient: accept/reject/modify flows,
audit-log append-only integrity, evidence-panel hashing, validation errors, and
overlay replay onto a fresh graph instance (persistence across restarts).

    python3 tests/test_review.py   # standalone
    pytest -q tests/test_review.py
"""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient  # noqa: E402

import api.main as apimod                   # noqa: E402


class _Client:
    """Fresh app + isolated benchmark/review dir per test."""

    def __init__(self):
        self.bench = Path(tempfile.mkdtemp()) / "bench"
        apimod.BENCH_DIR = self.bench
        self.c = TestClient(apimod.app).__enter__()

    def first_inferred_edge(self) -> str:
        ents = self.c.get("/api/entities", params={"type": "PERSON", "limit": 5}).json()
        for ent in ents:
            sg = self.c.get("/api/graph/subgraph",
                            params={"entity_id": ent["id"], "depth": 2}).json()
            for e in sg["edges"]:
                if e["creation_method"] == "INFERRED" and e["review_status"] == "PENDING":
                    return e["id"]
        raise AssertionError("no PENDING INFERRED edge found in seed graph")

    def __enter__(self):
        return self

    def close(self):
        self.c.__exit__(None, None, None)

    def __exit__(self, *exc):
        self.close()
        return False


def _review(client, edge_id, decision, reviewer="inv-007", **extra):
    return client.c.post("/api/review", json={
        "edge_id": edge_id, "decision": decision, "reviewer_id": reviewer, **extra
    })


def _rebuild_graph_with_same_reviews():
    """Simulate a server restart: new graph, same reviews.db — decisions must replay."""
    store = apimod.ReviewStore(apimod.BENCH_DIR / "reviews.db")
    bench = apimod.load_benchmark(apimod.BENCH_DIR)
    from graph import build_graph
    from resolve import resolve as run_resolve
    graph = build_graph(bench, run_resolve(bench)["clusters"])
    applied = apimod._overlay_reviews(graph, store)
    store.close()
    return graph, applied


def test_accept_flips_status_and_logs_audit():
    with _Client() as t:
        eid = t.first_inferred_edge()
        r = _review(t, eid, "ACCEPT")
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["success"] is True and d["decision"] == "ACCEPT"
        assert d["review_status"] == "ACCEPTED"
        rec = d["audit_record"]
        assert len(rec["evidence_hash"]) == 64
        assert rec["prev_status"] == "PENDING"
        # the live graph reflects it immediately
        ev = t.c.get(f"/api/evidence/{eid}").json()
        assert ev["review_status"] == "ACCEPTED"


def test_reject_sets_rejected():
    with _Client() as t:
        eid = t.first_inferred_edge()
        d = _review(t, eid, "REJECT").json()
        assert d["review_status"] == "REJECTED"


def test_modify_updates_confidence_and_rehashes():
    with _Client() as t:
        eid = t.first_inferred_edge()
        before = t.c.get(f"/api/evidence/{eid}").json()["confidence"]
        d = _review(t, eid, "MODIFY", modifications={"confidence": 0.9}).json()
        assert d["review_status"] == "ACCEPTED"
        assert abs(d["confidence"] - 0.9) < 1e-9
        ev = t.c.get(f"/api/evidence/{eid}").json()
        assert abs(ev["confidence"] - 0.9) < 1e-9
        if before != ev["confidence"]:
            assert ev["hash_verified"] is True     # canonical payload changed → re-hashed


def test_modify_without_confidence_is_422():
    with _Client() as t:
        eid = t.first_inferred_edge()
        assert _review(t, eid, "MODIFY").status_code == 422
        bad = _review(t, eid, "MODIFY", modifications={"confidence": 7})
        assert bad.status_code == 422


def test_accept_with_modifications_is_422():
    with _Client() as t:
        eid = t.first_inferred_edge()
        r = _review(t, eid, "ACCEPT", modifications={"confidence": 0.5})
        assert r.status_code == 422


def test_unknown_edge_404_and_bad_decision_422():
    with _Client() as t:
        assert _review(t, "E99999", "ACCEPT").status_code == 404
        assert _review(t, t.first_inferred_edge(), "MAYBE").status_code == 422


def test_audit_log_is_append_only_and_queryable():
    with _Client() as t:
        eid = t.first_inferred_edge()
        h1 = _review(t, eid, "REJECT").json()["audit_record"]["evidence_hash"]
        h2 = _review(t, eid, "ACCEPT").json()["audit_record"]["evidence_hash"]
        assert len(h1) == len(h2) == 64
        log = t.c.get("/api/reviews", params={"edge_id": eid}).json()
        assert [r["decision"] for r in log] == ["ACCEPT", "REJECT"]      # newest first
        assert log[0]["prev_status"] == "REJECTED"                       # chain of custody


def test_reviews_persist_across_restart_via_overlay():
    with _Client() as t:
        eid = t.first_inferred_edge()
        _review(t, eid, "MODIFY", modifications={"confidence": 0.85})

    graph, applied = _rebuild_graph_with_same_reviews()
    e = graph.edge(eid)
    assert applied >= 1
    assert e.review_status == "ACCEPTED"
    assert abs(e.confidence - 0.85) < 1e-9
    assert e.verify() is True                                            # hash tracks the change


def test_ledger_verify_endpoint_reports_ok_and_chain_links():
    with _Client() as t:
        eid = t.first_inferred_edge()
        r1 = _review(t, eid, "REJECT").json()["audit_record"]
        r2 = _review(t, eid, "ACCEPT").json()["audit_record"]
        # chain fields present and linked
        assert len(r1["chain_hash"]) == len(r2["chain_hash"]) == 64
        assert r2["prev_hash"] == r1["chain_hash"]
        # the verify endpoint walks the chain
        v = t.c.get("/api/reviews/verify").json()
        assert v["ok"] is True and v["records"] == 2 and v["first_bad_id"] is None
        assert "tamper" in v["disclosure"]


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
