// Typed client for the RAKSHAK MVP API (backend/api/main.py).
// Base URL is overridable with VITE_API_URL; defaults to the local FastAPI dev server.

const BASE = (import.meta.env.VITE_API_URL as string | undefined) ?? 'http://localhost:8000'

// ── wire types (mirror backend/api/schemas.py) ──────────────────────────────
export type Decision = 'MATCH' | 'UNCERTAIN' | 'NON_MATCH'
export type LayerName = 'communication' | 'financial' | 'spatial'
export type CreationMethod = 'EXTRACTED' | 'INFERRED'
export type ReviewStatus = 'PENDING' | 'ACCEPTED' | 'REJECTED'
export type NodeType = 'PERSON' | 'PHONE' | 'ACCOUNT' | 'LOCATION' | 'VEHICLE'

export interface FeatureBreakdown {
  identifier: number | null
  name: number
  phonetic: number
  attribute: number | null
}

export interface ResolveResponse {
  decision: Decision
  confidence: number
  calibrated: boolean
  weights: Record<string, number>
  features: FeatureBreakdown
  normalized_a: string
  normalized_b: string
  veto_reason: string | null
  route_to_review: boolean
}

export interface ResolveRequest {
  name_a: string
  name_b: string
  phone_a?: string
  phone_b?: string
  address_a?: string
  address_b?: string
  age_a?: number
  age_b?: number
}

export interface GraphNode {
  id: string
  label: string
  type: NodeType
  layers: LayerName[]
  risk: number | null
  meta: Record<string, unknown>
}

export interface GraphEdge {
  id: string
  source: string
  target: string
  type: string
  layer: LayerName
  creation_method: CreationMethod
  confidence: number
  timestamp: string
  provenance: string
  audit_hash: string
  review_status: ReviewStatus
}

export interface SubgraphResponse {
  root: string
  nodes: GraphNode[]
  edges: GraphEdge[]
  layer_assignments: Partial<Record<LayerName, string[]>>
  stats: { nodes: number; edges: number; inferred: number }
}

export interface SourceDocument {
  doc_id: string
  doc_type: 'FIR' | 'CDR' | 'FIN' | 'ANALYTICS'
  timestamp: string
  snippet: string
  highlight_span: [number, number] | null
  language: 'en' | 'hi' | 'hi-en' | null
}

export interface EvidenceResponse {
  edge_id: string
  claim: string
  confidence: number
  creation_method: CreationMethod
  audit_hash: string
  hash_verified: boolean
  source_documents: SourceDocument[]
  review_status: ReviewStatus
  reviewer_actions: Array<'ACCEPT' | 'REJECT' | 'MODIFY'>
  victim_shield: boolean
}

export interface EntitySummary {
  id: string
  label: string
  type: NodeType
  risk: number | null
  layers: LayerName[]
  meta: Record<string, unknown>
}

export interface ReviewRequest {
  edge_id: string
  decision: 'ACCEPT' | 'REJECT' | 'MODIFY'
  reviewer_id: string
  modifications?: Record<string, unknown> | null
}

export interface AuditRecord {
  id: number
  edge_id: string
  decision: string
  reviewer_id: string
  timestamp: string
  evidence_hash: string
  modifications: Record<string, unknown> | null
  prev_status: ReviewStatus
  prev_hash: string
  chain_hash: string
}

export interface ReviewResponse {
  success: boolean
  edge_id: string
  decision: 'ACCEPT' | 'REJECT' | 'MODIFY'
  review_status: ReviewStatus
  confidence: number
  audit_record: AuditRecord
}

export interface Anomaly {
  id: string
  kind: 'CIRCULAR_FLOW' | 'COMM_BURST' | 'TRANS_BURST'
  entity_id: string
  label: string
  entity_type: string
  severity: number
  z_score: number | null
  reason: string
  participants: string[]
  evidence_record_ids: string[]
}

export interface AnomaliesResponse {
  anomalies: Anomaly[]
  total: number
  evaluation: Record<string, {
    planted: number
    detected: number
    true_positives: number
    precision: number | null
    recall: number | null
  }> | null
  disclosure: string
}

export interface ScanFinding {
  cwe: string
  title: string
  severity: 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW'
  line: number
  snippet: string
  reason: string
  remediation: string
}

export interface ScanResponse {
  engine: string
  engine_note: string
  findings: ScanFinding[]
  summary: { total: number; by_severity: Record<string, number>; by_cwe: Record<string, number> }
  scanned_lines: number
  disclosure: string
}

export interface QueryMatch {
  entity_id: string
  label: string
  type: string
  score: number
}

export interface QueryResultRow {
  edge_id: string
  focus_entity_id: string
  claim: string
  confidence: number | null
  provenance: string | null
  timestamp: string | null
}

export interface QueryResponse {
  question: string
  intent: string
  grounded: boolean
  answer: string
  matches: QueryMatch[]
  results: QueryResultRow[]
  citations: string[]
  disclosure: string
}

// ── fetch helpers ───────────────────────────────────────────────────────────
async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`)
  if (!res.ok) throw new ApiError(res.status, `GET ${path} → ${res.status}`)
  return res.json() as Promise<T>
}

export class ApiError extends Error {
  status: number
  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }
}

export const api = {
  base: BASE,
  health: () => get<{ status: string; nodes: number; edges: number }>(`/api/health`),
  entities: (type: NodeType = 'PERSON', limit = 24) =>
    get<EntitySummary[]>(`/api/entities?type=${type}&limit=${limit}`),
  subgraph: (entityId: string, depth = 2, layers?: LayerName[], start?: string, end?: string) => {
    const q = new URLSearchParams({ entity_id: entityId, depth: String(depth) })
    if (layers?.length) q.set('layers', layers.join(','))
    if (start) q.set('start', start)
    if (end) q.set('end', end)
    return get<SubgraphResponse>(`/api/graph/subgraph?${q.toString()}`)
  },
  evidence: (edgeId: string) => get<EvidenceResponse>(`/api/evidence/${edgeId}`),
  anomalies: () => get<AnomaliesResponse>('/api/anomalies'),
  ask: (q: string) => get<QueryResponse>(`/api/query?q=${encodeURIComponent(q)}`),
  scan: async (code: string, filename?: string): Promise<ScanResponse> => {
    const res = await fetch(`${BASE}/api/scan`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ code, filename }),
    })
    if (!res.ok) throw new ApiError(res.status, `POST /api/scan → ${res.status}`)
    return res.json() as Promise<ScanResponse>
  },
  reviews: (edgeId?: string) =>
    get<AuditRecord[]>(`/api/reviews${edgeId ? `?edge_id=${edgeId}` : ''}`),
  verifyLedger: () =>
    get<{ ok: boolean; records: number; first_bad_id: number | null; disclosure: string }>(
      '/api/reviews/verify'),
  review: async (body: ReviewRequest): Promise<ReviewResponse> => {
    const res = await fetch(`${BASE}/api/review`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    })
    if (!res.ok) throw new ApiError(res.status, `POST /api/review → ${res.status}`)
    return res.json() as Promise<ReviewResponse>
  },
  resolve: async (body: ResolveRequest): Promise<ResolveResponse> => {
    const res = await fetch(`${BASE}/api/resolve`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    })
    if (!res.ok) throw new ApiError(res.status, `POST /api/resolve → ${res.status}`)
    return res.json() as Promise<ResolveResponse>
  },
}

// ── shared UI constants ───────────────────────────────────────────────────────
export const LAYER_COLOR: Record<LayerName, string> = {
  communication: '#00f0ff',
  financial: '#34d399',
  spatial: '#f59e0b',
}
export const LAYER_LABEL: Record<LayerName, string> = {
  communication: 'Communication',
  financial: 'Financial',
  spatial: 'Spatial',
}
