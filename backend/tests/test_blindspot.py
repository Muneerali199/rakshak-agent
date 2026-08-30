"""Blindspot tests — the system must honestly report what it does not know."""
from __future__ import annotations

import pytest

from analytics import analyze_blindspot
from graph import build_graph
from resolve import load_benchmark, resolve


@pytest.fixture(scope="module")
def graph():
    from pathlib import Path
    bench = load_benchmark(Path(__file__).resolve().parent.parent / "output")
    return build_graph(bench, resolve(bench)["clusters"])


def test_well_connected_entity_scores_high(graph):
    # an entity with multiple evidence layers + multiple sources must outscore a
    # single-layer dangling phone — corroboration reflects real coverage
    def coverage(nid):
        s = analyze_blindspot(graph, nid)["stats"]
        return (len(s["layers_present"]), s["independent_sources"])
    rich = max(graph.nodes, key=coverage)
    out = analyze_blindspot(graph, rich)
    assert out["stats"]["observed"] > 0
    assert len(out["stats"]["layers_present"]) >= 2
    assert out["corroboration_score"] >= 55
    assert out["verdict"]


def test_missing_layer_and_gaps_are_reported(graph):
    # a pure communication-layer phone: no financial/spatial evidence
    phone = next(nid for nid, n in graph.nodes.items() if n.type == "PHONE")
    out = analyze_blindspot(graph, phone)
    assert "financial" in out["stats"]["missing_layers"]
    assert any("financial" in g for g in out["gaps"])
    assert out["corroboration_score"] < 100


def test_unknown_entity_raises(graph):
    with pytest.raises(KeyError):
        analyze_blindspot(graph, "C-NOPE")


def test_blindspot_endpoint(client=None):
    from fastapi.testclient import TestClient
    import api.main as apimod
    with TestClient(apimod.app) as c:
        ents = c.get("/api/entities", params={"type": "PHONE", "limit": 1}).json()
        r = c.get(f"/api/blindspot/{ents[0]['id']}")
        assert r.status_code == 200
        body = r.json()
        assert 0 <= body["corroboration_score"] <= 100
        assert isinstance(body["gaps"], list)
        assert "disclosure" in body
        assert c.get("/api/blindspot/C-NOPE").status_code == 404
