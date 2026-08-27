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
import json
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from analytics import detect_anomalies, evaluate_anomalies
from experiments.experiment_a import run as run_experiment_a
from graph import build_graph
from resolve import load_benchmark, resolve
from resolve.features import PersonRef, WEIGHTS, score_pair
from resolve.io import deterministic_key

from .query import DISCLOSURE as QUERY_DISCLOSURE, answer_question
from .review_store import ReviewStore
from .scanner import scan as run_scan
from .schemas import (
    AuditRecordSchema, Decision, EvidenceResponse, FeatureBreakdown, GraphEdge,
    GraphNode, QueryResponse, ResolveRequest, ResolveResponse, ReviewDecision,
    ReviewRequest, ReviewResponse, ReviewStatus, ScanRequest, ScanResponse,
    SourceDocument, SubgraphResponse,
)

BENCH_DIR = Path(__file__).resolve().parent.parent / "output"

# in-memory service state, populated at startup
STATE: dict = {"graph": None, "bench": None, "records": {}, "risk": {}, "reviews": None,
               "anomalies": [], "anomaly_eval": None, "experiment_a": None}


def _apply_decision(edge, decision: str, modifications: dict | None) -> None:
    """Overlay a review decision onto an edge (Algorithm 8, lines 3–7).

    ACCEPT/REJECT set the status directly; MODIFY additionally applies the
    reviewed confidence so the corrected value is what the UI renders.
    """
    edge.review_status = "ACCEPTED" if decision in ("ACCEPT", "MODIFY") else "REJECTED"
    if decision == "MODIFY" and modifications and "confidence" in modifications:
        try:
            edge.confidence = round(float(modifications["confidence"]), 3)
            # confidence changed ⇒ the canonical payload changed ⇒ re-hash (Algorithm 3, line 8)
            edge.with_hash()
        except (TypeError, ValueError):
            pass


def _overlay_reviews(graph, store: ReviewStore) -> int:
    """Replay persisted review decisions onto a freshly built graph at startup."""
    applied = 0
    for edge_id, rec in store.latest_reviews().items():
        e = graph.edges.get(edge_id)
        if e is not None:
            _apply_decision(e, rec["decision"], rec["modifications"])
            applied += 1
    return applied


def _index_records(bench: dict) -> dict:
    idx = {}
    for src in ("fir", "cdr", "fin"):
        for r in bench[src]:
            idx[r["record_id"]] = r
    return idx


def _compute_risk(graph) -> dict:
    """Lightweight z-score anomaly on distinct-neighbor degree (MVP z-score detector, §14).

    Degree counts distinct neighbours (not edges) so repeated calls or duplicate
    inference cannot inflate a node's risk (#8). Risk is only assigned to
    PERSON/PHONE nodes; LOCATION hubs are naturally high-degree and not
    'suspicious', so they are left unscored.
    """
    neigh: dict[str, set] = {nid: set() for nid in graph.nodes}
    for e in graph.edges.values():
        neigh[e.source].add(e.target)
        neigh[e.target].add(e.source)
    scored = [nid for nid, n in graph.nodes.items() if n.type in ("PERSON", "PHONE")]
    if not scored:
        return {}
    vals = [len(neigh[n]) for n in scored]
    mean = sum(vals) / len(vals)
    var = sum((v - mean) ** 2 for v in vals) / len(vals)
    std = math.sqrt(var) or 1.0
    return {nid: round(1 / (1 + math.exp(-(len(neigh[nid]) - mean) / std)), 3) for nid in scored}


@asynccontextmanager
async def lifespan(app: FastAPI):
    if not (BENCH_DIR / "mentions.jsonl").exists():
        from synthgen import GenConfig, generate
        generate(GenConfig(seed=42), BENCH_DIR)
    bench = load_benchmark(BENCH_DIR)
    graph = build_graph(bench, resolve(bench)["clusters"])
    store = ReviewStore(BENCH_DIR / "reviews.db")
    _overlay_reviews(graph, store)
    anomalies = detect_anomalies(bench)
    gt_path = BENCH_DIR / "ground_truth.json"
    anomaly_eval = None
    if gt_path.exists():
        planted = json.loads(gt_path.read_text(encoding="utf-8")).get("planted_anomalies", [])
        anomaly_eval = evaluate_anomalies(anomalies, planted)
    STATE.update(bench=bench, graph=graph, records=_index_records(bench),
                 risk=_compute_risk(graph), reviews=store,
                 anomalies=anomalies, anomaly_eval=anomaly_eval)
    yield
    STATE.clear()


app = FastAPI(title="RAKSHAK MVP API", version="0.1.0", lifespan=lifespan)

# CORS: locked to an explicit allowlist. In production set ALLOWED_ORIGINS to the
# deployed frontend origin(s) (comma-separated), e.g. "https://rakshak-net.vercel.app".
# ALLOWED_ORIGIN_REGEX optionally covers preview deploys, e.g. r"https://.*\.vercel\.app".
# Defaults to the local Vite dev server only — no wildcard on a police-data API.
# Defaults cover the local Vite dev server on either port (repo vite.config uses 3000,
# the classic CRA/Vite default is 5173) — no wildcard on a police-data API.
_DEFAULT_ORIGINS = [
    "http://localhost:5173", "http://127.0.0.1:5173",
    "http://localhost:3000", "http://127.0.0.1:3000",
]
_ALLOWED_ORIGINS = [o.strip() for o in os.getenv("ALLOWED_ORIGINS", "").split(",") if o.strip()] or _DEFAULT_ORIGINS
app.add_middleware(
    CORSMiddleware,
    allow_origins=_ALLOWED_ORIGINS,
    allow_origin_regex=os.getenv("ALLOWED_ORIGIN_REGEX") or None,
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


def _parse_ts(val: str | None):
    """Accept YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS; return datetime or None."""
    if not val:
        return None
    val = val.strip()
    if not val:
        return None
    try:
        from datetime import datetime
        return datetime.fromisoformat(val)
    except ValueError:
        return None


def _filter_edges_by_time(edges: list, start_ts, end_ts) -> list:
    """Keep edges whose timestamp falls within [start_ts, end_ts].

    Edges with empty/trivial timestamps (inferred co-mention) are always kept.
    """
    out = []
    for e in edges:
        ts = e.timestamp
        if not ts:
            out.append(e)
            continue
        e_ts = _parse_ts(ts)
        if e_ts is None:
            out.append(e)
            continue
        if start_ts is not None and e_ts < start_ts:
            continue
        if end_ts is not None and e_ts > end_ts:
            continue
        out.append(e)
    return out


@app.get("/api/graph/subgraph", response_model=SubgraphResponse)
def api_subgraph(
    entity_id: str = Query(..., description="node id, e.g. a person cluster 'C00001' or 'PH:...'"),
    depth: int = Query(1, ge=1, le=3),
    layers: str | None = Query(None, description="comma-separated: communication,financial,spatial"),
    start: str = Query(None, description="filter edges from this date (ISO: YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS)"),
    end: str = Query(None, description="filter edges until this date (ISO: YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS)"),
) -> SubgraphResponse:
    g = STATE["graph"]
    layer_set = {s.strip() for s in layers.split(",")} if layers else None
    try:
        sg = g.subgraph(entity_id, depth=depth, layers=layer_set)
    except KeyError:
        raise HTTPException(404, f"entity '{entity_id}' not found")
    risk = STATE["risk"]
    filtered_edges = [_to_edge(e) for e in _filter_edges_by_time(sg["edges"], _parse_ts(start), _parse_ts(end))]
    return SubgraphResponse(
        root=sg["root"],
        nodes=[_to_node(n, risk) for n in sg["nodes"]],
        edges=filtered_edges,
        layer_assignments=sg["layer_assignments"],
        stats=dict(sg["stats"], edges=len(filtered_edges)),
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


def _is_victim_node(g, node_id: str) -> bool:
    n = g.nodes.get(node_id)
    return bool(n) and n.type == "PERSON" and n.meta.get("role") == "victim"


@app.get("/api/evidence/{edge_id}", response_model=EvidenceResponse)
def api_evidence(edge_id: str) -> EvidenceResponse:
    g = STATE["graph"]
    try:
        e = g.edge(edge_id)
    except KeyError:
        raise HTTPException(404, f"edge '{edge_id}' not found")
    s_label = g.nodes[e.source].label
    t_label = g.nodes[e.target].label
    # victim-shield: protected parties are pseudonymized even in the evidence panel
    shield = _is_victim_node(g, e.source) or _is_victim_node(g, e.target)
    docs = _evidence_docs(e)
    if shield:
        if _is_victim_node(g, e.source):
            docs = [SourceDocument(**{**d.model_dump(),
                                      "snippet": d.snippet.replace(s_label, "[PROTECTED VICTIM]"),
                                      "highlight_span": None})
                    for d in docs]
            s_label = "[PROTECTED VICTIM]"
        if _is_victim_node(g, e.target):
            docs = [SourceDocument(**{**d.model_dump(),
                                      "snippet": d.snippet.replace(t_label, "[PROTECTED VICTIM]"),
                                      "highlight_span": None})
                    for d in docs]
            t_label = "[PROTECTED VICTIM]"
    return EvidenceResponse(
        edge_id=e.id,
        claim=f"{s_label} ({e.source}) {e.type} {t_label} ({e.target})",
        confidence=e.confidence,
        creation_method=e.creation_method,
        audit_hash=e.audit_hash,
        hash_verified=e.verify(),
        source_documents=docs,
        review_status=e.review_status,
        reviewer_actions=["ACCEPT", "REJECT", "MODIFY"],
        victim_shield=shield,
    )


# ═══════════════ 4) POST /api/review  (Algorithm 8) ═══════════════

def _validate_modifications(decision: ReviewDecision, modifications: dict | None) -> None:
    """MODIFY requires a confidence in [0,1]; other decisions must carry none."""
    if decision == ReviewDecision.MODIFY:
        if not modifications or "confidence" not in modifications:
            raise HTTPException(422, "MODIFY requires modifications: {\"confidence\": <0..1>}")
        conf = modifications["confidence"]
        if not isinstance(conf, (int, float)) or not 0 <= conf <= 1:
            raise HTTPException(422, "modifications.confidence must be a number in [0,1]")
    elif modifications:
        raise HTTPException(422, f"{decision.value} does not accept modifications")


@app.post("/api/review", response_model=ReviewResponse)
def api_review(req: ReviewRequest) -> ReviewResponse:
    g, store = STATE["graph"], STATE.get("reviews")
    if store is None:
        raise HTTPException(503, "review store not initialised")
    try:
        e = g.edge(req.edge_id)
    except KeyError:
        raise HTTPException(404, f"edge '{req.edge_id}' not found")

    _validate_modifications(req.decision, req.modifications)

    # hash exactly what the investigator saw: the full evidence-panel payload
    panel = api_evidence(req.edge_id).model_dump()
    prev_status = e.review_status

    record = store.add_review(
        edge_id=req.edge_id,
        decision=req.decision.value,
        reviewer_id=req.reviewer_id,
        evidence_payload=panel,
        prev_status=prev_status,
        modifications=req.modifications,
    )

    _apply_decision(e, req.decision.value, req.modifications)

    return ReviewResponse(
        success=True,
        edge_id=req.edge_id,
        decision=req.decision,
        review_status=ReviewStatus(e.review_status),
        confidence=e.confidence,
        audit_record=AuditRecordSchema(**record),
    )


@app.get("/api/reviews")
def api_reviews(edge_id: str | None = None, limit: int = 200) -> list[dict]:
    """Append-only audit history (newest first) — Algorithm 8, immutable log inspection."""
    store = STATE.get("reviews")
    if store is None:
        raise HTTPException(503, "review store not initialised")
    return store.all_reviews(edge_id=edge_id, limit=limit)


@app.get("/api/reviews/verify")
def api_reviews_verify() -> dict:
    """Verify the hash-chained evidence ledger (Algorithm 8, tamper-evidence).

    Re-walks every audit record, recomputing each ``chain_hash`` and checking the
    ``prev_hash`` linkage. Any edit, deletion, or reordering of history breaks the
    chain and is reported with the first offending record id.
    """
    store = STATE.get("reviews")
    if store is None:
        raise HTTPException(503, "review store not initialised")
    result = store.verify_chain()
    return {
        **result,
        "disclosure": "hash-chained append-only audit ledger — tampering with any "
                      "historical review decision breaks every link after it",
    }


# ═══════════════ 5) GET /api/anomalies  (Algorithm 6, §14) ═══════════════

@app.get("/api/anomalies")
def api_anomalies(limit: int = 20) -> dict:
    """Analytical anomalies (circular flows, bursts) sorted by severity.

    Every entry is an *investigation lead*, never a claim of criminality (§14.2).
    ``evaluation`` scores the detectors against the generator's planted positives —
    possible only because the benchmark is synthetic, and disclosed as such.
    """
    g = STATE["graph"]
    out = []
    for a in STATE.get("anomalies", [])[:limit]:
        node = g.nodes.get(a["entity_id"]) if g else None
        out.append({
            "id": a["id"],
            "kind": a["kind"],
            "entity_id": a["entity_id"],
            "label": node.label if node else a["entity_id"],
            "entity_type": node.type if node else "UNKNOWN",
            "severity": a["severity"],
            "z_score": a["z_score"],
            "reason": a["reason"],
            "participants": a["participants"],
            "evidence_record_ids": a["evidence_record_ids"],
        })
    return {
        "anomalies": out,
        "total": len(STATE.get("anomalies", [])),
        "evaluation": STATE.get("anomaly_eval"),
        "disclosure": "analytical anomalies on synthetic data — a lead for investigation, "
                      "not a determination of criminality (paper §14.2)",
    }


# ═══════════════ 6) POST /api/scan  (RakshakAI, paper §18) ═══════════════

@app.post("/api/scan", response_model=ScanResponse)
def api_scan(req: ScanRequest) -> ScanResponse:
    """RakshakAI self-security scan: the platform audits its own code (§18).

    Uses the fine-tuned 14B model when RAKSHAK_AI_URL is configured; otherwise a
    deterministic rule engine, with the engine honestly labeled either way.
    """
    return ScanResponse(**run_scan(req.code))


# ═══════════════ 8) GET /api/experiments/a  (paper §22, §24) ═══════════════

@app.get("/api/experiments/a")
def api_experiment_a() -> dict:
    """Experiment A: exact vs fuzzy-only vs hybrid entity resolution on the benchmark.

    Computed once on first request (the baselines are O(n·b) pair loops) and cached.
    """
    if STATE.get("experiment_a") is None:
        gt_path = BENCH_DIR / "ground_truth.json"
        gt = json.loads(gt_path.read_text(encoding="utf-8")) if gt_path.exists() else {}
        STATE["experiment_a"] = run_experiment_a(STATE["bench"], gt)
    res = STATE["experiment_a"]
    return {
        "benchmark": "synthetic seed-42 (FIR/CDR/FIN), scored with §23 pairwise metrics",
        "results": {
            k: {
                "pairwise": v["pairwise"],
                "false_merge_rate": v["false_merge_rate"],
                "false_split_rate": v["false_split_rate"],
                "false_match_traps_merged": v["false_match_traps"],
            } for k, v in res.items()
        },
        "targets": res["hybrid"]["targets"],
        "disclosure": "measured on synthetic data with planted false-match twins — "
                      "preliminary numbers, honestly labeled (paper §26)",
    }


# ═══════════════ 7) GET /api/query  (Algorithm 7, §16) ═══════════════

@app.get("/api/query", response_model=QueryResponse)
def api_query(q: str = Query(..., min_length=2, description="natural-language question"),
              limit: int = Query(10, ge=1, le=50)) -> QueryResponse:
    """Grounded investigation query: answers come only from the case graph (§16.3)."""
    g = STATE["graph"]
    if g is None:
        raise HTTPException(503, "case graph not loaded")
    out = answer_question(q, g, STATE.get("anomalies", []), limit=limit)
    return QueryResponse(disclosure=QUERY_DISCLOSURE, **out)
