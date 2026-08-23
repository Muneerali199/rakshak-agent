"""RAKSHAK MVP API — FastAPI service over the Phase-3 resolver and Phase-4 graph.

Three endpoints back the Investigator Workbench (paper Algorithms 2, 3, 7):

    POST /api/resolve            — Hybrid Identity Resolution (real score_pair)
    GET  /api/graph/subgraph     — layered entity subgraph with provenance
    GET  /api/evidence/{edge_id} — source docs + SHA-256 verification (human-in-the-loop)

The benchmark is generated (seed 42) if absent, resolved, and turned into the 3-layer graph
once at startup, then held in memory. Run it:

    cd app/backend
    pip install -r api/requirements.txt
    uvicorn api.main:app --reload --port 8000
    # docs at http://localhost:8000/docs
"""
from __future__ import annotations

import math
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from graph import build_graph
from resolve import load_benchmark, resolve
from resolve.features import PersonRef, WEIGHTS, score_pair
from resolve.io import deterministic_key

from .schemas import (
    Decision, EvidenceResponse, FeatureBreakdown, GraphEdge, GraphNode,
    ResolveRequest, ResolveResponse, SourceDocument, SubgraphResponse,
)

BENCH_DIR = Path(__file__).resolve().parent.parent / "output"

# in-memory service state, populated at startup
STATE: dict = {"graph": None, "bench": None, "records": {}, "risk": {}}


def _index_records(bench: dict) -> dict:
    idx = {}
    for src in ("fir", "cdr", "fin"):
        for r in bench[src]:
            idx[r["record_id"]] = r
    return idx


def _compute_risk(graph) -> dict:
    """Lightweight z-score anomaly on node degree (MVP z-score detector, §14).

    Risk is only assigned to PERSON/PHONE nodes; LOCATION hubs are naturally
    high-degree and not 'suspicious', so they are left unscored.
    """
    deg: dict[str, int] = {nid: 0 for nid in graph.nodes}
    for e in graph.edges.values():
        deg[e.source] += 1
        deg[e.target] += 1
    scored = [nid for nid, n in graph.nodes.items() if n.type in ("PERSON", "PHONE")]
    if not scored:
        return {}
    vals = [deg[n] for n in scored]
    mean = sum(vals) / len(vals)
    var = sum((v - mean) ** 2 for v in vals) / len(vals)
    std = math.sqrt(var) or 1.0
    return {nid: round(1 / (1 + math.exp(-(deg[nid] - mean) / std)), 3) for nid in scored}


@asynccontextmanager
async def lifespan(app: FastAPI):
    if not (BENCH_DIR / "mentions.jsonl").exists():
        from synthgen import GenConfig, generate
        generate(GenConfig(seed=42), BENCH_DIR)
    bench = load_benchmark(BENCH_DIR)
    graph = build_graph(bench, resolve(bench)["clusters"])
    STATE.update(bench=bench, graph=graph, records=_index_records(bench), risk=_compute_risk(graph))
    yield
    STATE.clear()


app = FastAPI(title="RAKSHAK MVP API", version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173", "*"],
    allow_methods=["*"], allow_headers=["*"],
)

_DECISION = {"MATCH": Decision.MATCH, "UNCERTAIN": Decision.UNCERTAIN, "REJECT": Decision.REJECT}


@app.get("/api/health")
def health() -> dict:
    g = STATE["graph"]
    return {"status": "ok", "nodes": len(g.nodes) if g else 0, "edges": len(g.edges) if g else 0}


@app.post("/api/resolve", response_model=ResolveResponse)
def api_resolve(req: ResolveRequest) -> ResolveResponse:
    # Algorithm 2, lines 1–2: deterministic identifier short-circuit → observed MATCH
    ident = None
    if req.phone_a and req.phone_b:
        ident = 1.0 if deterministic_key("PHONE", req.phone_a) == deterministic_key("PHONE", req.phone_b) else 0.0

    a = PersonRef.build("a", req.name_a, age=req.age_a, address=req.address_a)
    b = PersonRef.build("b", req.name_b, age=req.age_b, address=req.address_b)
    m = score_pair(a, b)

    if ident == 1.0:
        decision, confidence, veto = Decision.MATCH, 1.0, None
    else:
        decision = _DECISION[m.decision]
        confidence = m.score
        veto = "hard attribute conflict on a confident name match" if m.decision == "REJECT" and m.parts.get("name", 0) >= 0.8 else None

    return ResolveResponse(
        decision=decision,
        confidence=confidence,
        calibrated=False,
        weights={("attribute" if k == "attr" else k): v for k, v in WEIGHTS.items()},
        features=FeatureBreakdown(
            identifier=ident,
            name=m.parts["name"],
            phonetic=m.parts["phonetic"],
            attribute=m.parts.get("attr"),
        ),
        normalized_a=" ".join(a.tokens),
        normalized_b=" ".join(b.tokens),
        veto_reason=veto,
        route_to_review=(decision == Decision.UNCERTAIN),
    )


def _to_node(n, risk: dict) -> GraphNode:
    return GraphNode(id=n.id, label=n.label, type=n.type,
                     layers=sorted(n.layers), risk=risk.get(n.id), meta=n.meta)


def _to_edge(e) -> GraphEdge:
    return GraphEdge(id=e.id, source=e.source, target=e.target, type=e.type, layer=e.layer,
                     creation_method=e.creation_method, confidence=e.confidence,
                     timestamp=e.timestamp or "", provenance=e.provenance,
                     audit_hash=e.audit_hash, review_status=e.review_status)


@app.get("/api/graph/subgraph", response_model=SubgraphResponse)
def api_subgraph(
    entity_id: str = Query(..., description="node id, e.g. a person cluster 'C00001' or 'PH:...'"),
    depth: int = Query(1, ge=1, le=3),
    layers: str | None = Query(None, description="comma-separated: communication,financial,spatial"),
) -> SubgraphResponse:
    g = STATE["graph"]
    layer_set = {s.strip() for s in layers.split(",")} if layers else None
    try:
        sg = g.subgraph(entity_id, depth=depth, layers=layer_set)
    except KeyError:
        raise HTTPException(404, f"entity '{entity_id}' not found")
    risk = STATE["risk"]
    return SubgraphResponse(
        root=sg["root"],
        nodes=[_to_node(n, risk) for n in sg["nodes"]],
        edges=[_to_edge(e) for e in sg["edges"]],
        layer_assignments=sg["layer_assignments"],
        stats=sg["stats"],
    )


@app.get("/api/entities")
def api_entities(type: str = "PERSON", limit: int = 20) -> list[dict]:
    """List entities (default PERSON) ranked by risk — a convenience for the UI/demo."""
    g, risk = STATE["graph"], STATE["risk"]
    ents = [{"id": n.id, "label": n.label, "type": n.type, "risk": risk.get(n.id),
             "layers": sorted(n.layers), "meta": n.meta}
            for n in g.nodes.values() if n.type == type]
    ents.sort(key=lambda e: (e["risk"] is not None, e["risk"] or 0), reverse=True)
    return ents[:limit]


def _evidence_docs(edge) -> list[SourceDocument]:
    """Build source-document snippets for an edge's provenance (Algorithm 7, line 8)."""
    prov = edge.provenance
    rid = prov.split(":", 1)[1] if prov.startswith("co-mention:") else prov
    rec = STATE["records"].get(rid)
    if rec is None:                       # pure analytics provenance
        return [SourceDocument(doc_id=prov, doc_type="ANALYTICS", timestamp=edge.timestamp or "",
                               snippet="Derived by graph analytics (co-mention / inference).")]
    src = rec["source"]
    if src == "CDR":
        snip = f'caller {rec["caller"]} → receiver {rec["receiver"]}, {rec["duration_sec"]}s, tower {rec["tower"]}'
        return [SourceDocument(doc_id=rid, doc_type="CDR", timestamp=rec["timestamp"], snippet=snip)]
    if src == "FIN":
        snip = f'{rec["sender_account"]} ({rec["sender_bank"]}) → {rec["receiver_account"]} ({rec["receiver_bank"]}), {rec["amount_raw"]}'
        return [SourceDocument(doc_id=rid, doc_type="FIN", timestamp=rec["timestamp"], snippet=snip)]
    # FIR — return the narrative with a highlight span for the source node's name if present
    nar = rec.get("narrative", "")
    span = None
    label = STATE["graph"].nodes[edge.source].label
    pos = nar.find(label)
    if pos >= 0:
        span = (pos, pos + len(label))
    return [SourceDocument(doc_id=rid, doc_type="FIR", timestamp=rec["date"],
                           snippet=nar or f'FIR {rid}', highlight_span=span, language=rec.get("language"))]


@app.get("/api/evidence/{edge_id}", response_model=EvidenceResponse)
def api_evidence(edge_id: str) -> EvidenceResponse:
    g = STATE["graph"]
    try:
        e = g.edge(edge_id)
    except KeyError:
        raise HTTPException(404, f"edge '{edge_id}' not found")
    s_label = g.nodes[e.source].label
    t_label = g.nodes[e.target].label
    return EvidenceResponse(
        edge_id=e.id,
        claim=f"{s_label} ({e.source}) {e.type} {t_label} ({e.target})",
        confidence=e.confidence,
        creation_method=e.creation_method,
        audit_hash=e.audit_hash,
        hash_verified=e.verify(),
        source_documents=_evidence_docs(e),
        review_status=e.review_status,
        reviewer_actions=["ACCEPT", "REJECT", "MODIFY"],
    )
