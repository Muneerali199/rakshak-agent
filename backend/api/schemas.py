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
    type: Literal["PERSON", "PHONE", "ACCOUNT", "LOCATION", "VEHICLE"]
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
