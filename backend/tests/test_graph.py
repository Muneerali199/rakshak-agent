"""Tests for the Phase-4 graph seed (paper §10, Algorithm 3).

Focus: (1) the three layers are built with the right edge types, (2) every edge carries a
verifiable SHA-256 audit hash (tamper-evident), (3) subgraph traversal is correct, and (4)
PERSON nodes are connected into the communication lane via inferred USES edges.

    python3 tests/test_graph.py       # standalone
    pytest -q                         # if pytest is installed
"""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from synthgen import GenConfig, generate            # noqa: E402
from resolve import load_benchmark, resolve          # noqa: E402
from graph import COMMUNICATION, FINANCIAL, SPATIAL, build_graph  # noqa: E402


def _graph(seed: int, tmp: Path):
    generate(GenConfig(seed=seed), tmp)
    bench = load_benchmark(tmp)
    return bench, build_graph(bench, resolve(bench)["clusters"])


def test_three_layers_present():
    with tempfile.TemporaryDirectory() as t:
        _, g = _graph(42, Path(t))
        layers = {e.layer for e in g.edges.values()}
        assert {COMMUNICATION, FINANCIAL, SPATIAL} <= layers
        types = {e.type for e in g.edges.values()}
        assert {"CONTACTED", "TRANSFERRED_TO", "LOCATED_AT"} <= types


def test_every_edge_hash_verifies():
    with tempfile.TemporaryDirectory() as t:
        _, g = _graph(7, Path(t))
        assert g.edges, "graph should have edges"
        assert all(e.audit_hash and e.verify() for e in g.edges.values())


def test_tampering_breaks_the_hash():
    with tempfile.TemporaryDirectory() as t:
        _, g = _graph(7, Path(t))
        e = next(iter(g.edges.values()))
        assert e.verify()
        e.confidence = (e.confidence + 0.5) % 1.0     # mutate a hashed field
        assert not e.verify()


def test_observed_vs_inferred_split():
    with tempfile.TemporaryDirectory() as t:
        _, g = _graph(42, Path(t))
        methods = {e.creation_method for e in g.edges.values()}
        assert methods == {"EXTRACTED", "INFERRED"}
        # CDR/FIN/FIR direct edges are observed; co-mention/USES are inferred
        assert all(e.creation_method == "EXTRACTED"
                   for e in g.edges.values() if e.type in ("CONTACTED", "TRANSFERRED_TO", "LOCATED_AT"))
        assert all(e.creation_method == "INFERRED"
                   for e in g.edges.values() if e.type in ("ASSOCIATE_OF", "USES"))


def test_persons_reach_communication_lane():
    # the inferred USES edge must connect at least one PERSON to a PHONE
    with tempfile.TemporaryDirectory() as t:
        _, g = _graph(42, Path(t))
        uses = [e for e in g.edges.values() if e.type == "USES"]
        assert uses, "expected inferred person→phone USES edges"
        e = uses[0]
        assert g.nodes[e.source].type == "PERSON"
        assert g.nodes[e.target].type == "PHONE"


def test_subgraph_is_bounded_and_consistent():
    with tempfile.TemporaryDirectory() as t:
        _, g = _graph(42, Path(t))
        # a phone node always has ≥1 CONTACTED edge → subgraph non-trivial
        phone = next(n for n in g.nodes.values() if n.type == "PHONE")
        sg = g.subgraph(phone.id, depth=1)
        assert sg["root"] == phone.id
        node_ids = {n.id for n in sg["nodes"]}
        # every edge endpoint is present among the returned nodes
        for e in sg["edges"]:
            assert e.source in node_ids and e.target in node_ids
        assert sg["stats"]["nodes"] == len(sg["nodes"])


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
