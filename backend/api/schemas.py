"""Pydantic v2 schemas for the RAKSHAK MVP API (paper Algorithms 2, 3, 7).

These are the wire contracts for the Investigator Workbench frontend. The web layer
(FastAPI + Pydantic) is intentionally isolated here so the core `synthgen`, `resolve`,
and `graph` packages stay dependency-free / stdlib-only.
"""
from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field


# ─────────────────────────── shared enums ───────────────────────────
class Decision(str, Enum):
    MATCH = "MATCH"
    UNCERTAIN = "UNCERTAIN"       # → routed to human review (Algo 2, line 18)
    REJECT = "NON_MATCH"


# ─────────────────────────── Aadhaar-verified officer login ───────────────────────────
class AuthOtpRequest(BaseModel):
    aadhaar: str = Field(..., min_length=12, max_length=12, pattern=r"^\d{12}$",
                         examples=["700011771177"])


class EvidenceResolveIn(BaseModel):
    text: str = Field(..., min_length=10, max_length=200_000,
                      description="Document text (or PDF-extracted text) to auto-resolve",
                      examples=["Shikayatkarta Sunita Devi … संदिग्ध रमेश कुमार …"])


class ExtractRequest(BaseModel):
    text: str = Field(..., min_length=2, max_length=200_000,
                      description="Narrative text to entity-extract (regex / hybrid / indner)",
                      examples=["रमेश कुमार ने सुनीता देवी को धमकी दी, खाता AC0076617711"])


class PersonResolveRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=120,
                      description="Person name in any script / spelling variant",
                      examples=["Mohammad Arif", "मोहम्मद आरिफ़"])


class HindiTransliterateIn(BaseModel):
    texts: list[str] = Field(..., min_length=1, max_length=512,
                             description="Latin strings to convert to Devanagari")


class HindiTranslateIn(BaseModel):
    terms: list[str] = Field(..., min_length=1, max_length=256,
                             description="Fixed-vocabulary terms to translate to Hindi")


class HindiProfileIn(BaseModel):
    fields: dict | None = Field(None, description="Structured English profile (name/address/…)")
    text: str | None = Field(None, min_length=10, max_length=200_000,
                             description="Or: raw English profile text; entities are extracted first")


class AuthLogin(BaseModel):
    aadhaar: str = Field(..., min_length=12, max_length=12, pattern=r"^\d{12}$",
                         examples=["700011771177"])
    otp: str = Field(..., min_length=6, max_length=6, pattern=r"^\d{6}$", examples=["771177"])
    purpose: str = Field("workbench login", max_length=80,
                         examples=["FIR filing session"])


class Layer(str, Enum):
    COMMUNICATION = "communication"
    FINANCIAL = "financial"
    SPATIAL = "spatial"


class CreationMethod(str, Enum):
    EXTRACTED = "EXTRACTED"       # observed in a source doc → solid edge in UI
    INFERRED = "INFERRED"         # derived by analytics → dashed grey edge


class ReviewStatus(str, Enum):
    PENDING = "PENDING"
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"


# ═══════════════ 1) POST /api/resolve  (Algorithm 2) ═══════════════
class ResolveRequest(BaseModel):
    name_a: str = Field(..., examples=["Mohammad Arif"])
    name_b: str = Field(..., examples=["Mohd Arif"])
    phone_a: str | None = None
    phone_b: str | None = None
    address_a: str | None = None
    address_b: str | None = None
    age_a: int | None = None
    age_b: int | None = None


class FeatureBreakdown(BaseModel):
    """The 4 MVP features actually computed (φ_k). Null = feature not applicable."""
    identifier: float | None = Field(None, description="exact phone/account/vehicle → 1.0 or null")
    name: float = Field(..., ge=0, le=1, description="jaro-winkler + levenshtein + n-gram cosine")
    phonetic: float = Field(..., ge=0, le=1, description="Indian-tuned double-metaphone agreement")
    attribute: float | None = Field(None, ge=0, le=1, description="age + address Jaccard; null if unknown")


class ResolveResponse(BaseModel):
    decision: Decision
    confidence: float = Field(..., ge=0, le=1, description="σ(Σ w_k·φ_k) — Algo 2 line 15")
    calibrated: bool = Field(False, description="false = uniform/prior weights (Criticism 3 disclosure)")
    weights: dict[str, float]
    features: FeatureBreakdown
    normalized_a: str
    normalized_b: str
    veto_reason: str | None = None
    route_to_review: bool


# ═══════════ 2) GET /api/graph/subgraph  (Algorithm 3 edges) ═══════════
class GraphNode(BaseModel):
    id: str
    label: str
    type: Literal["PERSON", "PHONE", "ACCOUNT", "LOCATION", "VEHICLE", "ORGANIZATION"]
    layers: list[Layer]
    risk: float | None = Field(None, ge=0, le=1)
    meta: dict = {}


class GraphEdge(BaseModel):
    id: str
    source: str
    target: str
    type: str
    layer: Layer
    creation_method: CreationMethod
    confidence: float = Field(..., ge=0, le=1)
    timestamp: str
    provenance: str
    audit_hash: str
    review_status: ReviewStatus


class SubgraphResponse(BaseModel):
    root: str
    nodes: list[GraphNode]
    edges: list[GraphEdge]
    layer_assignments: dict[Layer, list[str]]
    stats: dict


# ═══════════════ 3) GET /api/evidence/{edge_id}  (Algorithm 7) ═══════════════
class SourceDocument(BaseModel):
    doc_id: str
    doc_type: Literal["FIR", "CDR", "FIN", "ANALYTICS"]
    timestamp: str
    snippet: str
    highlight_span: tuple[int, int] | None = None
    language: Literal["en", "hi", "hi-en"] | None = None


class EvidenceResponse(BaseModel):
    edge_id: str
    claim: str
    confidence: float = Field(..., ge=0, le=1)
    creation_method: CreationMethod
    audit_hash: str
    hash_verified: bool
    source_documents: list[SourceDocument]
    review_status: ReviewStatus
    reviewer_actions: list[Literal["ACCEPT", "REJECT", "MODIFY"]]
    victim_shield: bool = False
    warrant_id: str | None = None       # set when protected data was lawfully unmasked


# ═══════════════ warrant gate (DEPA consent artifacts) ═══════════════
class WarrantRequestIn(BaseModel):
    scope: str                          # e.g. "edge:E-..." — DEPA artifacts are scoped
    requester_id: str
    requester_role: str
    reason: str


class WarrantApproveIn(BaseModel):
    approver_id: str
    approver_role: str                  # must be SP rank or above, ≠ requester


class WarrantOut(BaseModel):
    ok: bool
    warrant_id: str | None = None
    status: str | None = None
    scope: str | None = None
    expires_at: str | None = None
    error: str | None = None


# ═══════════════ 4) POST /api/review  (Algorithm 8) ═══════════════
class ReviewDecision(str, Enum):
    ACCEPT = "ACCEPT"
    REJECT = "REJECT"
    MODIFY = "MODIFY"


class ReviewRequest(BaseModel):
    edge_id: str
    decision: ReviewDecision
    reviewer_id: str
    modifications: dict | None = None


class AuditRecordSchema(BaseModel):
    id: int
    edge_id: str
    decision: str
    reviewer_id: str
    timestamp: str
    evidence_hash: str
    modifications: dict | None = None
    prev_status: str
    prev_hash: str = ""
    chain_hash: str = ""


class ReviewResponse(BaseModel):
    success: bool
    edge_id: str
    decision: ReviewDecision
    review_status: ReviewStatus
    confidence: float
    audit_record: AuditRecordSchema


# ═══════════════ 5) POST /api/scan  (RakshakAI, paper §18) ═══════════════
class ScanRequest(BaseModel):
    code: str = Field(..., max_length=60_000, examples=['@app.get("/citizen/{id}")\ndef get_citizen(id):\n    return db.execute(f"SELECT * FROM citizens WHERE id={id}")'])
    filename: str | None = Field(None, examples=["api/routes.py"])


class ScanFinding(BaseModel):
    cwe: str
    title: str
    severity: Literal["CRITICAL", "HIGH", "MEDIUM", "LOW"]
    line: int
    snippet: str
    reason: str
    remediation: str


class ScanResponse(BaseModel):
    engine: str
    engine_note: str
    findings: list[ScanFinding]
    summary: dict
    scanned_lines: int
    disclosure: str


# ═══════════════ 6) GET /api/query  (Algorithm 7, §16) ═══════════════
class QueryMatch(BaseModel):
    entity_id: str
    label: str
    type: str
    score: float


class QueryResultRow(BaseModel):
    edge_id: str
    focus_entity_id: str
    claim: str
    confidence: float | None = None
    provenance: str | None = None
    timestamp: str | None = None


class QueryResponse(BaseModel):
    question: str
    intent: str
    grounded: bool
    answer: str
    matches: list[QueryMatch]
    results: list[QueryResultRow]
    citations: list[str]
    disclosure: str


# ═══════════════ 8) POST /api/ingest/fir  (live FIR-to-graph) ═══════════════
class IngestRequest(BaseModel):
    """A raw FIR as an investigator would paste it — free text + minimal structure."""
    narrative: str = Field(..., min_length=20, max_length=20_000,
                           examples=["दिनांक 12/04/2026 को शिकायतकर्ता ने बताया कि संदिग्ध ने +91-9812345678 से धमकी भरा कॉल किया। वाहन DL3C 9423 देखा गया। खाता AC1234567890 में पैसे ट्रांसफर हुए।"])
    district: str = Field(..., examples=["Delhi"])
    police_station: str = Field(..., examples=["PS Karol Bagh"])
    date: str = Field(..., examples=["2026-04-12"])
    complainant_name: str | None = Field(None, examples=["Sunita Devi"])
    accused_names: list[str] = Field(default_factory=list, examples=[["Ramesh Kumar"]])


class ExtractedEntityOut(BaseModel):
    kind: str                     # PERSON | PHONE | ACCOUNT | VEHICLE | IPC
    surface: str                  # as it appears in the narrative
    normalized: str               # graph key form
    span: tuple[int, int]         # character offsets into the narrative
    node_id: str = ""             # graph node id after merge


class CrossCaseLink(BaseModel):
    entity_kind: str
    entity_surface: str
    entity_key: str
    linked_records: list[dict]
    cross_district: list[str]
    alert: str


# ═══════════════ mesh (district vault interoperability) ═══════════════
class MeshReceiptOut(BaseModel):
    """One peer vault's signed answer — counts and record ids only, never case data."""
    responder_vault: str
    hits: int
    hit_summaries: list[dict]
    timestamp: str
    verified: bool = False
    error: str | None = None


class MeshFanout(BaseModel):
    request_id: str
    receipts: list[MeshReceiptOut]
    all_verified: bool
    error: str | None = None


class IngestResponse(BaseModel):
    record_id: str
    entities: list[ExtractedEntityOut]
    cross_case_links: list[CrossCaseLink]
    new_edges: list[dict]
    victim_shield_applied: bool
    graph_stats: dict             # nodes/edges after merge — the "graph grew" proof
    mesh: MeshFanout | None = None  # cross-vault signed receipts (mesh mode only)
    disclosure: str


# ═══════════════ 9) GET /api/escalation  (stalking trajectory, §14) ═══════════════
class EscalationAlert(BaseModel):
    id: str
    caller: str                   # PH:… node id
    caller_label: str
    receiver: str                 # PH:… node id
    receiver_label: str
    victim_linked: bool           # receiver attributed to an FIR complainant
    weekly_counts: list[int]      # oldest → newest call volumes
    night_calls: int              # 23:00–05:00 calls (double-weighted signal)
    score: float
    severity: Literal["CRITICAL", "HIGH", "MEDIUM"]
    reason: str
    evidence_record_ids: list[str]


class EscalationResponse(BaseModel):
    alerts: list[EscalationAlert]
    total: int
    disclosure: str


# ═══════════════ 10) GET /api/report/{entity_id}  (evidence chain) ═══════════════
class ReportRow(BaseModel):
    edge_id: str
    claim: str
    layer: str
    creation_method: CreationMethod
    confidence: float
    timestamp: str
    provenance: str
    audit_hash: str
    hash_verified: bool
    review_status: ReviewStatus


class ReportResponse(BaseModel):
    entity_id: str
    label: str
    type: str
    role: str | None              # accused | victim | mentioned (victim → redacted report)
    generated_at: str
    rows: list[ReportRow]
    anomalies: list[dict]
    review_history: list[dict]
    ledger: dict                  # verify_chain() output — the integrity statement
    victim_shield: bool
    blindspot: dict | None = None        # corroboration profile — what we don't know
    warrant_events: list[dict] = []      # protected-data access log touching this entity
    mesh_exchanges: list[dict] = []      # cross-vault receipts that established links
    disclosure: str
