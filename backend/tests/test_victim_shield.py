"""Victim-shield tests (Women Safety Division policy layer).

A resolved PERSON named as a *complainant* in an FIR (and never as an accused) is a
protected party: the NL query refuses to network-analyze them, path queries through
them are masked, and evidence panels redact their identity. Accused persons get full
analysis. These tests pin that boundary.

    python3 tests/test_victim_shield.py   # standalone
    pytest -q tests/test_victim_shield.py
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
    def __init__(self):
        self.bench = Path(tempfile.mkdtemp()) / "bench"
        apimod.BENCH_DIR = self.bench
        self.c = TestClient(apimod.app).__enter__()

    def __enter__(self):
        return self

    def close(self):
        self.c.__exit__(None, None, None)

    def __exit__(self, *exc):
        self.close()
        return False


def _roles(state_graph) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {"victim": [], "accused": [], "mentioned": []}
    for n in state_graph.nodes.values():
        if n.type == "PERSON":
            out.setdefault(n.meta.get("role", "mentioned"), []).append(n.id)
    return out


def test_roles_tagged_from_fir_fields():
    with _Client() as t:
        g = apimod.STATE["graph"]
        roles = _roles(g)
        assert len(roles["victim"]) > 0, "expected ≥1 complainant-only cluster tagged victim"
        assert len(roles["accused"]) > 0, "expected ≥1 accused cluster"
        # every role value is one of the three
        for n in g.nodes.values():
            if n.type == "PERSON":
                assert n.meta.get("role") in ("victim", "accused", "mentioned")
        print(f"  roles: {len(roles['victim'])} victims, {len(roles['accused'])} accused, "
              f"{len(roles['mentioned'])} mentioned")


def test_query_victim_is_masked_with_no_results():
    with _Client() as t:
        g = apimod.STATE["graph"]
        victim = next(n for n in g.nodes.values()
                      if n.type == "PERSON" and n.meta.get("role") == "victim")
        r = t.c.get("/api/query", params={"q": f"who did {victim.label} contact?"}).json()
        assert r["grounded"] is True
        assert "protected party" in r["answer"]
        assert "pseudonymized" in r["answer"]
        assert r["results"] == [] and r["citations"] == []


def test_query_accused_is_normal():
    with _Client() as t:
        g = apimod.STATE["graph"]
        accused = next(n for n in g.nodes.values()
                       if n.type == "PERSON" and n.meta.get("role") == "accused")
        r = t.c.get("/api/query", params={"q": f"where was {accused.label} seen?"}).json()
        assert "protected party" not in r["answer"]


def test_path_query_through_victim_is_masked():
    with _Client() as t:
        g = apimod.STATE["graph"]
        victim = next(n for n in g.nodes.values()
                      if n.type == "PERSON" and n.meta.get("role") == "victim")
        accused = next(n for n in g.nodes.values()
                       if n.type == "PERSON" and n.meta.get("role") == "accused")
        r = t.c.get("/api/query",
                    params={"q": f"how are {victim.label} and {accused.label} connected?"}).json()
        assert "protected party" in r["answer"]
        assert r["results"] == [] and r["citations"] == []


def test_evidence_redacts_victim_identity():
    with _Client() as t:
        g = apimod.STATE["graph"]
        victims = {n.id: n.label for n in g.nodes.values()
                   if n.type == "PERSON" and n.meta.get("role") == "victim"}
        # find an edge touching a victim
        edge = next(e for e in g.edges.values()
                    if e.source in victims or e.target in victims)
        r = t.c.get(f"/api/evidence/{edge.id}").json()
        assert r["victim_shield"] is True
        assert "[PROTECTED VICTIM]" in r["claim"]
        vic_label = victims[edge.source if edge.source in victims else edge.target]
        assert vic_label not in r["claim"]
        for doc in r["source_documents"]:
            assert vic_label not in doc["snippet"]


def test_evidence_accused_only_edge_unchanged():
    with _Client() as t:
        g = apimod.STATE["graph"]
        victims = {n.id for n in g.nodes.values()
                   if n.type == "PERSON" and n.meta.get("role") == "victim"}
        edge = next(e for e in g.edges.values()
                    if e.source not in victims and e.target not in victims)
        r = t.c.get(f"/api/evidence/{edge.id}").json()
        assert r["victim_shield"] is False
        assert "[PROTECTED VICTIM]" not in r["claim"]


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
