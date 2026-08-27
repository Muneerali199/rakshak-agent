"""Grounded NL query tests (paper §16, Algorithm 7).

Focus: the anti-hallucination contract — answers only reference graph entities,
every claim cites edge ids, unknown names are refused (never invented).

    python3 tests/test_query.py   # standalone
    pytest -q tests/test_query.py
"""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api.query import answer_question            # noqa: E402
from graph import build_graph                    # noqa: E402
from resolve import load_benchmark, resolve      # noqa: E402
from synthgen import GenConfig, generate         # noqa: E402


def _setup():
    tmp = tempfile.mkdtemp()
    generate(GenConfig(seed=42), Path(tmp))
    bench = load_benchmark(Path(tmp))
    graph = build_graph(bench, resolve(bench)["clusters"])
    return graph


def _person_with_contacts(graph) -> str:
    for n in graph.nodes.values():
        if n.type == "PERSON" and any(
            graph.edges[e].type == "CONTACTED"
            for e in graph._adj[n.id]                    # noqa: SLF001
            if any(graph.edges[e2].type == "USES" and graph.edges[e2].source == n.id
                   for e2 in graph._adj[graph.edges[e].source if graph.edges[e].target != n.id
                                        else graph.edges[e].target])  # noqa: SLF001
        ):
            return n.id
    # fallback: any person with a USES edge (their phone has CONTACTED partners)
    for n in graph.nodes.values():
        if n.type == "PERSON" and any(graph.edges[e].type == "USES" for e in graph._adj[n.id]):  # noqa: SLF001
            return n.id
    raise AssertionError("no person with phone edges found")


def test_contact_query_returns_cited_results():
    g = _setup()
    pid = _person_with_contacts(g)
    label = g.nodes[pid].label
    r = answer_question(f"who did {label} contact?", g, [])
    assert r["grounded"] is True
    assert r["intent"] == "contact"
    assert r["citations"], "claims without citations"
    assert all(c in g.edges for c in r["citations"])     # citations are real edges
    assert label in r["answer"]


def test_location_and_ownership_queries():
    g = _setup()
    pid = next(n.id for n in g.nodes.values()
               if n.type == "PERSON"
               and any(g.edges[e].type == "LOCATED_AT" for e in g._adj[n.id]))  # noqa: SLF001
    label = g.nodes[pid].label
    loc = answer_question(f"where was {label} seen?", g, [])
    assert loc["intent"] == "location" and loc["grounded"] and loc["citations"]
    own = answer_question(f"what does {label} own?", g, [])
    assert own["intent"] == "owned" and own["grounded"]
    assert all(c in g.edges for c in own["citations"])


def test_path_query_finds_connection_or_honest_none():
    g = _setup()
    persons = [n for n in g.nodes.values() if n.type == "PERSON"]
    a = next(n for n in persons if any(g.edges[e].type == "ASSOCIATE_OF" for e in g._adj[n.id]))  # noqa: SLF001
    b = next(g.edges[e].target for e in g._adj[a.id] if g.edges[e].type == "ASSOCIATE_OF")        # noqa: SLF001
    r = answer_question(f"how are {a.label} and {g.nodes[b].label} connected?", g, [])
    assert r["intent"] == "path" and r["grounded"]
    assert r["citations"], "path must cite its edges"
    # every cited edge exists and the path is contiguous
    for c in r["citations"]:
        assert c in g.edges


def test_unknown_entity_is_refused_not_invented():
    g = _setup()
    r = answer_question("who did Barack Obama contact?", g, [])
    assert r["grounded"] is False
    assert r["results"] == [] and r["citations"] == []
    assert "not in the case graph" in r["answer"]


def test_anomaly_and_help_intents():
    g = _setup()
    anoms = [{"entity_id": "AC:x", "label": "AC123", "kind": "CIRCULAR_FLOW"}]
    r = answer_question("any suspicious activity?", g, anoms)
    assert r["intent"] == "anomaly" and r["grounded"]
    assert "AC123" in r["answer"]
    h = answer_question("help", g, [])
    assert h["intent"] == "help" and "who did" in h["answer"]


def test_api_query_endpoint_roundtrip():
    import api.main as apimod
    from fastapi.testclient import TestClient

    apimod.BENCH_DIR = Path(tempfile.mkdtemp()) / "bench"
    with TestClient(apimod.app) as c:
        r = c.get("/api/query", params={"q": "any suspicious activity?"})
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["grounded"] is True
        assert "cannot invent" in d["disclosure"]
        bad = c.get("/api/query", params={"q": "x"})
        assert bad.status_code == 422                    # min length guard


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
