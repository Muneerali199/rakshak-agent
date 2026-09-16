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
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from analytics import analyze_blindspot, detect_anomalies, evaluate_anomalies
from analytics.escalation import detect_escalation
from experiments.experiment_a import run as run_experiment_a
from graph import build_graph
from resolve import load_benchmark, resolve
from resolve.features import PersonRef, WEIGHTS, score_pair
from resolve.io import deterministic_key

from .ingest import ExtractedEntity, extract_entities, find_cross_case_links, merge_into_graph
from .query import DISCLOSURE as QUERY_DISCLOSURE, answer_question
from .review_store import ReviewStore
from .scanner import scan as run_scan
from . import vault_config
from .sentinel import (ENDPOINT_LEVELS, SentinelStore, build_manifest, check_manifest,
                       model_pin, release_manifest_check, scan_own_codebase)
from .warrants import WarrantStore
from mesh import client as mesh_client, protocol as mesh_protocol
from .schemas import (
    AuditRecordSchema, Decision, EscalationAlert, EscalationResponse,
    EvidenceResponse, ExtractedEntityOut, FeatureBreakdown, GraphEdge,
    GraphNode, IngestRequest, IngestResponse, MeshFanout, MeshReceiptOut,
    QueryResponse, ReportResponse,
    ReportRow, ResolveRequest, ResolveResponse, ReviewDecision,
    ReviewRequest, ReviewResponse, ReviewStatus, ScanRequest, ScanResponse,
    SourceDocument, SubgraphResponse, WarrantApproveIn, WarrantOut, WarrantRequestIn,
)

BENCH_DIR = Path(os.getenv("RAKSHAK_BENCH_DIR",
                           str(Path(__file__).resolve().parent.parent / "output")))

# in-memory service state, populated at startup
STATE: dict = {"graph": None, "bench": None, "records": {}, "risk": {}, "reviews": None,
               "anomalies": [], "anomaly_eval": None, "experiment_a": None,
               "escalation": [], "ingest_counter": 0, "warrants": None}


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


def _compute_influence(graph) -> dict:
    """Cross-layer hub score for PERSONs: degree × (1 + 0.25 × (breadth − 1)).

    Degree (distinct neighbours) is the connectivity signal; the layer count is
    breadth — a suspect who touches communication + financial + spatial
    infrastructure is operationally more influential than one who only makes
    calls (§ key-influencers, PS-6). Layers come from the node's assigned layers,
    so the score is deterministic and auditable against the graph, like risk.
    """
    neigh: dict[str, set] = {nid: set() for nid in graph.nodes}
    for e in graph.edges.values():
        neigh[e.source].add(e.target)
        neigh[e.target].add(e.source)
    out: dict[str, float] = {}
    for nid, n in graph.nodes.items():
        if n.type != "PERSON":
            continue
        breadth = max(0, len(n.layers) - 1)
        out[nid] = round(len(neigh.get(nid, set())) * (1 + 0.25 * breadth), 3)
    return out


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
    escalation = detect_escalation(bench, graph)
    STATE.update(bench=bench, graph=graph, records=_index_records(bench),
                 risk=_compute_risk(graph), reviews=store,
                 anomalies=anomalies, anomaly_eval=anomaly_eval,
                 escalation=escalation, ingest_counter=0, experiment_a=None,
                 warrants=WarrantStore(str(BENCH_DIR / "warrants.db")))
    # RakshakAI Sentinel: the platform scans its own code at boot and hash-chains
    # the report — its security posture is itself tamper-evident evidence.
    sentinel = SentinelStore(str(BENCH_DIR / "sentinel.db"))
    scan_report = scan_own_codebase(Path(__file__).resolve().parent.parent)
    scan_report["engine"] = "rules"
    sentinel.log("BOOT_SCAN", scan_report)
    sentinel.log("MODEL_PIN", model_pin())
    # Component integrity: this boot's manifest COMPARED against the previous
    # boot's (from the ledger) — detection, not just display. An optional
    # RAKSHAK_RELEASE_MANIFEST (outside the app tree) pins a trusted reference.
    manifest = build_manifest(Path(__file__).resolve().parent.parent)
    sentinel.log("MANIFEST", check_manifest(manifest, sentinel.latest("MANIFEST")))
    release = release_manifest_check(manifest, os.getenv("RAKSHAK_RELEASE_MANIFEST", ""))
    if release:
        sentinel.log("MANIFEST_RELEASE", release)
    STATE["sentinel"] = sentinel
    STATE["manifest"] = manifest
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
    return {"status": "ok", "nodes": len(g.nodes) if g else 0,
            "edges": len(g.edges) if g else 0,
            "vault": vault_config.vault_id(), "mesh": vault_config.mesh_enabled()}


# ═══════════════ mesh responder (vault side of the UPI moment) ═══════════════

def _local_hit_summaries(entity_keys: list[str]) -> list[dict]:
    """Privacy-preserving answers: counts + record ids only, never narratives/names."""
    bench = STATE.get("bench") or {}
    from resolve.io import deterministic_key
    summaries: list[dict] = []
    for key in entity_keys:
        kind, _, value = key.partition(":")
        record_ids: list[str] = []
        if kind == "PHONE":
            for r in bench.get("cdr", []):
                if value in (deterministic_key("PHONE", r["caller"]),
                             deterministic_key("PHONE", r["receiver"])):
                    record_ids.append(r["record_id"])
        elif kind == "ACCOUNT":
            for r in bench.get("fin", []):
                if value in (r["sender_account"], r["receiver_account"]):
                    record_ids.append(r["record_id"])
        elif kind == "VEHICLE":
            import re as _re
            for r in bench.get("fir", []):
                nar = _re.sub(r"[^0-9A-Za-z]", "", r.get("narrative", "")).upper()
                if value in nar:
                    record_ids.append(r["record_id"])
        elif kind == "ORGANIZATION":
            for r in bench.get("fir", []):
                if value.lower() in r.get("narrative", "").lower():
                    record_ids.append(r["record_id"])
        if record_ids:
            summaries.append({"entity_key": key, "record_count": len(record_ids),
                              "record_ids": sorted(record_ids)[:10]})
    return summaries


@app.post("/mesh/query")
def mesh_query(body: dict) -> dict:
    """Answer a peer vault's signed query envelope (mesh mode only).

    Verifies the origin signature, searches ONLY this vault's local records, and
    returns a signed receipt with privacy-preserving hit summaries. Case data
    never leaves the vault — only the answer travels.
    """
    if not vault_config.mesh_enabled():
        raise HTTPException(404, "mesh mode not enabled on this instance")
    env = body.get("envelope", {})
    secrets = vault_config.vault_secrets()
    origin = env.get("origin_vault", "")
    if origin not in secrets or origin == vault_config.vault_id():
        raise HTTPException(403, "unknown or self origin vault")
    if not mesh_protocol.verify_envelope(env, secrets[origin]):
        raise HTTPException(403, "envelope signature verification failed")
    summaries = _local_hit_summaries(env.get("entity_keys", []))
    return mesh_protocol.make_receipt(env, vault_config.vault_id(), len(summaries),
                                      summaries, vault_config.my_secret())


# test hook: ingest fan-out transport is injectable (no sockets in tests)
MESH_TRANSPORT = None


def _mesh_fanout_for_entities(entities: list[ExtractedEntity]) -> MeshFanout | None:
    """Fire the mesh: ask peer vaults about extracted identifiers, collect receipts."""
    if not vault_config.mesh_enabled():
        return None
    keys = sorted({f"{e.kind}:{e.normalized}" for e in entities
                   if e.kind in ("PHONE", "ACCOUNT", "VEHICLE", "ORGANIZATION")})
    if not keys:
        return None
    res = mesh_client.fanout_entity_lookup(
        vault_config.vault_id(), keys, vault_config.gateway_url(),
        vault_config.vault_secrets(), transport=MESH_TRANSPORT)
    return MeshFanout(request_id=res["request_id"],
                      receipts=[MeshReceiptOut(**r) for r in res["receipts"]],
                      all_verified=res["all_verified"], error=res["error"])


_NODE_KIND_PREFIX = {"PH": "PHONE", "AC": "ACCOUNT", "VH": "VEHICLE"}


def _mesh_exchanges_for_entity(g, entity_id: str) -> list[dict]:
    """Jurisdiction chain: gateway-logged exchanges that touched this entity's identifiers.

    Collects the mesh keys for the entity itself and its adjacent identifier nodes,
    then asks the gateway's receipt ledger for matching exchanges. Tolerant by
    design — if the gateway is down, the report simply omits the section.
    """
    if not vault_config.mesh_enabled():
        return []

    def key_of(nid: str) -> str | None:
        prefix, _, value = nid.partition(":")
        kind = _NODE_KIND_PREFIX.get(prefix)
        return f"{kind}:{value}" if kind else None

    keys = {k for k in (key_of(entity_id),) if k}
    for eid in g._adj.get(entity_id, ()):            # noqa: SLF001
        e = g.edges[eid]
        for nid in (e.source, e.target):
            k = key_of(nid)
            if k:
                keys.add(k)
    if not keys:
        return []
    try:
        import httpx
        resp = httpx.get(f"{vault_config.gateway_url()}/mesh/receipts",
                         params={"limit": 50}, timeout=2.0)
        exchanges = resp.json().get("exchanges", [])
    except Exception:                                # noqa: BLE001 — gateway optional
        return []
    return [{"exchange_id": ex["id"], "request_id": ex["request_id"],
             "origin_vault": ex["origin_vault"], "timestamp": ex["timestamp"],
             "chain_hash": ex["chain_hash"],
             "receipts": [{"responder_vault": r["responder_vault"], "hits": r["hits"]}
                          for r in ex["receipts"]]}
            for ex in exchanges if any(k in ex["entity_keys"] for k in keys)][:10]


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
    """List entities (default PERSON) ranked by risk — a convenience for the UI/demo.

    ``influence`` (cross-layer hub score, PERSONs only) rides along so the
    workbench can badge classic network-relay hubs without a second round-trip.
    """
    g, risk = STATE["graph"], STATE["risk"]
    inf = _compute_influence(g)
    ents = [{"id": n.id, "label": n.label, "type": n.type, "risk": risk.get(n.id),
             "influence": inf.get(n.id), "layers": sorted(n.layers), "meta": n.meta}
            for n in g.nodes.values() if n.type == type]
    ents.sort(key=lambda e: ((e["risk"] is not None, e["risk"] or 0), e["influence"] or 0),
              reverse=True)
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
def api_evidence(edge_id: str,
                 warrant_id: str | None = Query(None, description="approved warrant "
                                                 "artifact id — unmasks protected parties")) -> EvidenceResponse:
    g = STATE["graph"]
    try:
        e = g.edge(edge_id)
    except KeyError:
        raise HTTPException(404, f"edge '{edge_id}' not found")
    s_label = g.nodes[e.source].label
    t_label = g.nodes[e.target].label
    # victim-shield: protected parties are pseudonymized even in the evidence panel.
    # Unmasking requires a valid warrant artifact scoped to this exact edge (DEPA).
    shield = _is_victim_node(g, e.source) or _is_victim_node(g, e.target)
    unmasked_by = None
    if shield and warrant_id:
        store = STATE.get("warrants")
        chk = store.check(warrant_id, scope=f"edge:{edge_id}") if store else {"ok": False, "error": "warrant store unavailable"}
        if chk["ok"]:
            shield, unmasked_by = False, warrant_id      # lawful unmasking, ledger-logged
        else:
            raise HTTPException(403, f"warrant invalid: {chk['error']}")
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
        victim_shield=shield or bool(unmasked_by),
        warrant_id=unmasked_by,
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


# ═══════════════ warrant gate (DEPA consent artifacts, four-eyes) ═══════════════

WARRANT_DISCLOSURE = (
    "protected-party access requires a scoped, expiring warrant artifact — "
    "requested by the investigating officer, countersigned by a senior officer "
    "(four-eyes principle), and hash-chained into a tamper-evident ledger. "
    "Modelled on India's DEPA / Account Aggregator consent architecture.")


def _warrant_store() -> WarrantStore:
    store = STATE.get("warrants")
    if store is None:
        raise HTTPException(503, "warrant store not initialised")
    return store


@app.post("/api/warrants", response_model=WarrantOut)
def api_warrant_request(req: WarrantRequestIn) -> WarrantOut:
    """Request access to protected data — opens a PENDING warrant artifact."""
    out = _warrant_store().request(req.scope, req.requester_id, req.requester_role, req.reason)
    return WarrantOut(ok=True, warrant_id=out["warrant_id"], status=out["status"],
                      scope=out["scope"], expires_at=out["expires_at"])


@app.post("/api/warrants/{warrant_id}/approve", response_model=WarrantOut)
def api_warrant_approve(warrant_id: str, req: WarrantApproveIn) -> WarrantOut:
    """Senior-officer countersignature — the dual-key moment (requester ≠ approver)."""
    out = _warrant_store().approve(warrant_id, req.approver_id, req.approver_role)
    if not out["ok"]:
        raise HTTPException(403, out["error"])
    return WarrantOut(**out)


@app.post("/api/warrants/{warrant_id}/revoke", response_model=WarrantOut)
def api_warrant_revoke(warrant_id: str, by: str = "system", role: str = "SP") -> WarrantOut:
    out = _warrant_store().revoke(warrant_id, by, role)
    if not out["ok"]:
        raise HTTPException(404, out["error"])
    return WarrantOut(**out)


@app.get("/api/warrants/verify")
def api_warrants_verify() -> dict:
    """Verify the warrant ledger — every request/approval/use is hash-chained."""
    return {**_warrant_store().verify_chain(), "disclosure": WARRANT_DISCLOSURE}


@app.get("/api/warrants")
def api_warrants(limit: int = 100) -> dict:
    """Warrant audit trail (newest first) — who accessed what, who approved, when."""
    return {"events": _warrant_store().all_events(limit=limit),
            "disclosure": WARRANT_DISCLOSURE}


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


# ═══════════════ 9) POST /api/ingest/fir  (live FIR-to-graph) ═══════════════

INGEST_DISCLOSURE = ("live FIR ingestion: deterministic regex NER with source spans — "
                     "no LLM, every extracted entity is auditable against the pasted text; "
                     "cross-case linkage is an analytical alert, not a determination")


@app.post("/api/ingest/fir", response_model=IngestResponse)
def api_ingest_fir(req: IngestRequest) -> IngestResponse:
    """File a new FIR: extract entities, detect cross-case linkage, merge into the graph.

    The demo's opening moment — paste raw narrative text and watch it become
    intelligence: extracted entities carry source spans, existing collisions across
    districts surface as alerts, and the live graph grows.
    """
    g, bench = STATE["graph"], STATE["bench"]
    if g is None or bench is None:
        raise HTTPException(503, "case graph not loaded")

    STATE["ingest_counter"] += 1
    record_id = f"FIR-LIVE-{STATE['ingest_counter']:04d}"
    record = {
        "record_id": record_id,
        "source": "FIR",
        "narrative": req.narrative,
        "date": req.date,
        "district": req.district,
        "police_station": req.police_station,
        "language": "hi-en",
        "accused": [{"name": n} for n in req.accused_names],
        "complainant": {"name": req.complainant_name} if req.complainant_name else {},
        "ipc_sections": [],
    }

    # 1) regex NER with spans — deterministic, auditable
    entities = extract_entities(req.narrative)
    # structured accused names are first-class entities too (dedupe on normalized)
    have = {(e.kind, e.normalized) for e in entities}
    for name in req.accused_names:
        norm = name.strip().title()
        if ("PERSON", norm) in have:
            continue
        pos = req.narrative.find(name)
        entities.append(ExtractedEntity(
            kind="PERSON", surface=name, normalized=norm,
            span=(pos, pos + len(name)) if pos >= 0 else (0, 0)))

    # 2) cross-case linkage against the existing benchmark
    links = find_cross_case_links(entities, bench, req.district)

    # 2b) the UPI moment: ask peer vaults about extracted identifiers (mesh mode)
    mesh = _mesh_fanout_for_entities(entities)

    # 3) merge into the live graph + records index
    new_edges = merge_into_graph(g, bench, record, entities,
                                 req.complainant_name, req.accused_names)
    STATE["records"][record_id] = record
    STATE["risk"] = _compute_risk(g)

    return IngestResponse(
        record_id=record_id,
        entities=[ExtractedEntityOut(kind=e.kind, surface=e.surface,
                                     normalized=e.normalized, span=e.span,
                                     node_id=e.node_id) for e in entities],
        cross_case_links=links,
        new_edges=new_edges,
        victim_shield_applied=bool(req.complainant_name),
        graph_stats={"nodes": len(g.nodes), "edges": len(g.edges)},
        mesh=mesh,
        disclosure=INGEST_DISCLOSURE,
    )


# ═══════════════ 10) GET /api/escalation  (stalking trajectory) ═══════════════

ESCALATION_DISCLOSURE = (
    "escalation alerts are analytical leads computed from call-pattern trajectories — "
    "they flag behavior for investigation before violence, never determine guilt; "
    "protected parties (complainants) are referenced only as shielded flags (§14.2)")


@app.get("/api/escalation", response_model=EscalationResponse)
def api_escalation(limit: int = Query(20, ge=1, le=100)) -> EscalationResponse:
    """Stalking-escalation leads: rising caller→receiver contact trajectories.

    The Women Safety case: harassment FIR filed, the accused does not stop — call
    volume climbs, night calls begin. This endpoint surfaces that curve so an
    investigator intervenes *before* the next FIR, not after.
    """
    alerts = [EscalationAlert(**a) for a in STATE.get("escalation", [])[:limit]]
    return EscalationResponse(alerts=alerts, total=len(STATE.get("escalation", [])),
                              disclosure=ESCALATION_DISCLOSURE)


# ═══════════════ 13) GET /api/security/posture  (RakshakAI Sentinel) ═══════════════

@app.get("/api/security/posture")
def api_security_posture() -> dict:
    """The platform's self-audit, on the record: graded endpoint map, the boot
    self-scan (hash-chained), code manifest integrity, model pin, and every
    ledger's verification status. A police system that audits itself — and proves it."""
    sentinel = STATE.get("sentinel")
    latest = sentinel.latest("BOOT_SCAN") if sentinel else None
    pin = sentinel.latest("MODEL_PIN") if sentinel else None
    manifest_check = sentinel.latest("MANIFEST") if sentinel else None
    manifest_release = sentinel.latest("MANIFEST_RELEASE") if sentinel else None
    return {
        "levels": {route: {"level": lvl, "note": note}
                   for route, (lvl, note) in sorted(ENDPOINT_LEVELS.items())},
        "boot_scan": ({"timestamp": latest["timestamp"],
                       "report": json.loads(latest["report"]),
                       "chain_hash": latest["chain_hash"]} if latest else None),
        "model_pin": (json.loads(pin["report"]) if pin else None),
        "manifest": STATE.get("manifest"),
        "manifest_check": (json.loads(manifest_check["report"]) if manifest_check else None),
        "manifest_release": (json.loads(manifest_release["report"]) if manifest_release else None),
        "ledgers": {
            "reviews": STATE["reviews"].verify_chain() if STATE.get("reviews") else None,
            "warrants": STATE["warrants"].verify_chain() if STATE.get("warrants") else None,
            "sentinel": sentinel.verify_chain() if sentinel else None,
        },
        "mesh": {"enabled": vault_config.mesh_enabled(), "vault": vault_config.vault_id()},
        "disclosure": ("self-security posture: graded endpoint levels (MLPS-inspired), "
                       "boot self-scan hash-chained into the sentinel ledger, build "
                       "manifest over all backend sources COMPARED against the previous "
                       "boot (and an optional trusted release manifest); tamper-evident "
                       "audit trail, not tamper-proof storage"),
    }


# ═══════════════ 12) GET /api/blindspot/{entity_id}  (honest AI) ═══════════════

BLINDSPOT_DISCLOSURE = (
    "blindspot analysis states what the system does NOT know — missing layers, "
    "inferred-only links, single-source corroboration, temporal gaps. Analytical "
    "humility by design: corroboration scores are investigative guidance, never "
    "a determination of guilt or innocence.")


@app.get("/api/blindspot/{entity_id}")
def api_blindspot(entity_id: str) -> dict:
    """The corroboration profile + gaps for one entity — what we don't know."""
    g = STATE["graph"]
    if g is None:
        raise HTTPException(503, "case graph not loaded")
    try:
        out = analyze_blindspot(g, entity_id)
    except KeyError:
        raise HTTPException(404, f"entity '{entity_id}' not found")
    return {**out, "disclosure": BLINDSPOT_DISCLOSURE}


# ═══════════════ 11) GET /api/report/{entity_id}  (evidence chain) ═══════════════

@app.get("/api/report/{entity_id}", response_model=ReportResponse)
def api_report(entity_id: str) -> ReportResponse:
    """Court-ready evidence chain for one entity (Algorithm 7 + Algorithm 8 output).

    Every connection the case graph holds for this entity, grouped into rows carrying
    claim, confidence, timestamp, provenance, live hash verification, and review
    status — plus the anomaly context and the ledger integrity statement. This is the
    document an investigating officer can attach to a charge sheet.
    """
    g = STATE["graph"]
    if g is None:
        raise HTTPException(503, "case graph not loaded")
    node = g.nodes.get(entity_id)
    if node is None:
        raise HTTPException(404, f"entity '{entity_id}' not found")

    shield = _is_victim_node(g, entity_id)
    label = "[PROTECTED VICTIM]" if shield else node.label

    rows: list[ReportRow] = []
    for eid in sorted(g._adj.get(entity_id, ())):        # noqa: SLF001
        e = g.edges[eid]
        s_label = g.nodes[e.source].label
        t_label = g.nodes[e.target].label
        if shield:
            if _is_victim_node(g, e.source):
                s_label = "[PROTECTED VICTIM]"
            if _is_victim_node(g, e.target):
                t_label = "[PROTECTED VICTIM]"
        rows.append(ReportRow(
            edge_id=e.id,
            claim=f"{s_label} ({e.source}) {e.type} {t_label} ({e.target})",
            layer=e.layer, creation_method=e.creation_method,
            confidence=e.confidence, timestamp=e.timestamp or "",
            provenance=e.provenance, audit_hash=e.audit_hash,
            hash_verified=e.verify(), review_status=e.review_status,
        ))

    anomalies = [a for a in STATE.get("anomalies", [])
                 if a["entity_id"] == entity_id or entity_id in a.get("participants", [])]

    store = STATE.get("reviews")
    review_history = store.all_reviews() if store else []
    entity_edge_ids = {r.edge_id for r in rows}
    review_history = [r for r in review_history if r["edge_id"] in entity_edge_ids][:50]
    ledger = store.verify_chain() if store else {"ok": True, "records": 0, "first_bad_id": None}

    # Report 2.0 — corroboration honesty, protected-access log, jurisdiction chain
    try:
        blindspot = analyze_blindspot(g, entity_id)
    except KeyError:
        blindspot = None

    wstore = STATE.get("warrants")
    warrant_events = ([e for e in wstore.all_events()
                       if e["scope"].split(":", 1)[-1] in entity_edge_ids][:50]
                      if wstore else [])

    mesh_exchanges = _mesh_exchanges_for_entity(g, entity_id)

    return ReportResponse(
        entity_id=entity_id,
        label=label,
        type=node.type,
        role=node.meta.get("role"),
        generated_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        rows=rows,
        anomalies=anomalies,
        review_history=review_history,
        ledger=ledger,
        victim_shield=shield,
        blindspot=blindspot,
        warrant_events=warrant_events,
        mesh_exchanges=mesh_exchanges,
        disclosure=("evidence-chain report: every row carries its source record id and a "
                    "recomputable SHA-256 audit hash; review history is hash-chained; "
                    "cross-vault links cite signed mesh receipts; protected-data access "
                    "appears in the warrant log; analytical content is investigative lead, "
                    "not determination of guilt"),
    )
