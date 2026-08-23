"""RAKSHAK temporal knowledge graph — Phase 4 seed (paper §10).

Builds the MVP's three graph layers (Communication / Financial / Spatial) from the
Phase-3 resolved benchmark, with per-edge provenance and SHA-256 audit hashing
(Algorithm 3). Pure standard library.

    from resolve import load_benchmark, resolve
    from graph import build_graph
    bench = load_benchmark("output")
    g = build_graph(bench, resolve(bench)["clusters"])
    sg = g.subgraph("C00001", depth=2)
"""
from __future__ import annotations

from .build import COMMUNICATION, FINANCIAL, SPATIAL, Edge, Graph, Node, build_graph

__all__ = ["build_graph", "Graph", "Node", "Edge", "COMMUNICATION", "FINANCIAL", "SPATIAL"]
__version__ = "0.1.0"
