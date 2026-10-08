// Typed client for the RAKSHAK MVP API (backend/api/main.py).
// Base URL is overridable with VITE_API_URL; defaults to the local FastAPI dev server.
import { token, type AuthResult } from './auth'

const BASE = (import.meta.env.VITE_API_URL as string | undefined) ?? 'http://localhost:8000'

// ── wire types (mirror backend/api/schemas.py) ──────────────────────────────
export type Decision = 'MATCH' | 'UNCERTAIN' | 'NON_MATCH'
export type LayerName = 'communication' | 'financial' | 'spatial'
export type CreationMethod = 'EXTRACTED' | 'INFERRED'
export type ReviewStatus = 'PENDING' | 'ACCEPTED' | 'REJECTED'
export type NodeType = 'PERSON' | 'PHONE' | 'ACCOUNT' | 'LOCATION' | 'VEHICLE' | 'ORGANIZATION'

export interface FeatureBreakdown {
  identifier: number | null
  name: number
  phonetic: number
  attribute: number | null
}

export interface ResolveResponse {
  decision: 'MATCH' | 'UNCERTAIN' | 'REJECT'
  confidence: number
  calibrated: boolean
  weights: Record<string, number>
  features: FeatureBreakdown
  normalized_a: string
  normalized_b: string
  veto_reason: string | null
  route_to_review: boolean
}

export interface EvidenceRow {
  surface: string
  normalized: string
  span: [number, number]
  match: { id: string; label: string } | null
  decision: 'MATCH' | 'UNCERTAIN' | 'REJECT' | 'NEW'
  confidence: number
  basis: { name: number; phonetic: number }
  veto: string | null
  route_to_review: boolean
}
export interface EvidenceResolve {
  engine: string
  count: number
  candidate_count: number
  rows: EvidenceRow[]
  weights: Record<string, number>
  disclosure: string
}

export interface OcrResult {
  filename?: string
  preview: string
  n_chars: number
  text: string
  lang: string
  engine: string
  version?: string
  disclosure: string
  extract?: ExtractResponse['entities']
}

export interface ExtractResponse {
  entities: { kind: string; surface: string; normalized: string; span: [number, number] }[]
  engine: string
  model: string
  disclosure: string
  agreements?: { kind: string; surface: string }[]
  disagreements?: { surface: string; regex: string; model: string; resolved: string }[]
  regex_entities?: { kind: string; surface: string }[]
  model_entities?: { kind: string; surface: string }[]
}

export interface PersonDossierFir {
  record_id: string
  role: string
  district?: string
  section?: string[]
  age?: number
  address?: string
  police_station?: string
  date?: string
}
export interface PersonDossier {
  found: boolean
  query: string
  name?: string
  id?: string
  match_confidence?: number
  aliases?: string[]
  roles?: string[]
  victim_shielded?: boolean
  district?: string
  firs?: PersonDossierFir[]
  fir_count?: number
  identifiers?: { phones: string[]; accounts: string[]; vehicles: string[] }
  hindi?: {
    name: string
    roles: string[]
    aliases: string[]
    identifiers: { phones: string[]; accounts: string[]; vehicles: string[] }
  }
  engine: string
  disclosure: string
}

export interface HindiProfileItem {
  field: string
  label: string
  original: string
  hindi: string
}
export interface HindiProfileResponse {
  items: HindiProfileItem[]
  paragraph: string
  engine: string
  disclosure: string
}
export interface HindiBulkResponse {
  hindi: string[]
  engine: string
  disclosure: string
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
  warrant_id?: string | null      // set when protected data was lawfully unmasked
}

export interface EntitySummary {
  id: string
  label: string
  type: NodeType
  risk: number | null
  influence: number | null
  fir_count: number
  repeat_offender: boolean
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

// ── live FIR ingestion ──────────────────────────────────────────────────────
export interface IngestRequest {
  narrative: string
  district: string
  police_station: string
  date: string
  complainant_name?: string
  accused_names?: string[]
}

export interface ExtractedEntityOut {
  kind: string
  surface: string
  normalized: string
  span: [number, number]
  node_id: string
}

export interface CrossCaseLink {
  entity_kind: string
  entity_surface: string
  entity_key: string
  linked_records: Array<{ record_id: string; source: string; district: string }>
  cross_district: string[]
  alert: string
}

export interface MeshReceiptOut {
  responder_vault: string
  hits: number
  hit_summaries: Array<{ entity_key: string; record_count: number; record_ids: string[] }>
  timestamp: string
  verified: boolean
  error?: string | null
}

export interface MeshFanout {
  request_id: string
  receipts: MeshReceiptOut[]
  all_verified: boolean
  error?: string | null
}

export interface IngestResponse {
  record_id: string
  entities: ExtractedEntityOut[]
  cross_case_links: CrossCaseLink[]
  new_edges: Array<{ edge_id: string; type: string; source: string; target: string }>
  victim_shield_applied: boolean
  graph_stats: { nodes: number; edges: number }
  mesh?: MeshFanout | null
  disclosure: string
}

// ── stalking escalation ─────────────────────────────────────────────────────
export interface EscalationAlert {
  id: string
  caller: string
  caller_label: string
  receiver: string
  receiver_label: string
  victim_linked: boolean
  weekly_counts: number[]
  night_calls: number
  score: number
  severity: 'CRITICAL' | 'HIGH' | 'MEDIUM'
  reason: string
  evidence_record_ids: string[]
}

export interface EscalationResponse {
  alerts: EscalationAlert[]
  total: number
  disclosure: string
}

// ── evidence chain report ───────────────────────────────────────────────────
export interface ReportRow {
  edge_id: string
  claim: string
  layer: string
  creation_method: CreationMethod
  confidence: number
  timestamp: string
  provenance: string
  audit_hash: string
  hash_verified: boolean
  review_status: ReviewStatus
}

export interface ReportResponse {
  entity_id: string
  label: string
  type: string
  role: string | null
  generated_at: string
  rows: ReportRow[]
  anomalies: Anomaly[]
  review_history: AuditRecord[]
  ledger: { ok: boolean; records: number; first_bad_id: number | null }
  victim_shield: boolean
  blindspot?: BlindspotResponse | null
  warrant_events?: WarrantEvent[]
  mesh_exchanges?: MeshExchange[]
  disclosure: string
}

export interface WarrantEvent {
  id: number
  warrant_id: string
  event: 'REQUEST' | 'APPROVE' | 'USE' | 'REVOKE' | 'DENY'
  scope: string
  requester_id: string
  requester_role: string
  approver_id: string | null
  approver_role: string | null
  timestamp: string
  chain_hash: string
}

export interface MeshExchange {
  exchange_id: number
  request_id: string
  origin_vault: string
  timestamp: string
  chain_hash: string
  receipts: Array<{ responder_vault: string; hits: number }>
}

// ── blindspot (honest AI: what the system does NOT know) ────────────────────
export interface BlindspotResponse {
  entity_id: string
  label: string
  corroboration_score: number
  stats: {
    edges: number
    observed: number
    inferred: number
    layers_present: string[]
    missing_layers: string[]
    independent_sources: number
    max_gap_days: number
  }
  gaps: string[]
  verdict: string
  disclosure: string
}

// ── fetch helpers ───────────────────────────────────────────────────────────
// Write endpoints are bound to the Aadhaar-verified officer session, so every
// request carries the bearer token when one is present; public reads ignore it.
function authHeaders(extra?: Record<string, string>): Record<string, string> {
  const t = token()
  return { ...(t ? { Authorization: `Bearer ${t}` } : {}), ...(extra ?? {}) }
}

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`, { headers: authHeaders() })
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
  health: () => get<{ status: string; nodes: number; edges: number; vault?: string | null; mesh?: boolean }>(`/api/health`),
  entities: (type: NodeType = 'PERSON', limit = 24) =>
    get<EntitySummary[]>(`/api/entities?type=${type}&limit=${limit}`),
  subgraph: (entityId: string, depth = 2, layers?: LayerName[], start?: string, end?: string) => {
    const q = new URLSearchParams({ entity_id: entityId, depth: String(depth) })
    if (layers?.length) q.set('layers', layers.join(','))
    if (start) q.set('start', start)
    if (end) q.set('end', end)
    return get<SubgraphResponse>(`/api/graph/subgraph?${q.toString()}`)
  },
  evidence: (edgeId: string, warrantId?: string) =>
    get<EvidenceResponse>(`/api/evidence/${edgeId}${warrantId ? `?warrant_id=${encodeURIComponent(warrantId)}` : ''}`),
  anomalies: () => get<AnomaliesResponse>('/api/anomalies'),
  ask: (q: string, lang: 'en' | 'hi' = 'en') =>
    get<QueryResponse>(`/api/query?q=${encodeURIComponent(q)}&lang=${lang}`),
  escalation: () => get<EscalationResponse>('/api/escalation'),
  report: (entityId: string) => get<ReportResponse>(`/api/report/${encodeURIComponent(entityId)}`),
  blindspot: (entityId: string) => get<BlindspotResponse>(`/api/blindspot/${encodeURIComponent(entityId)}`),
  ingestFir: async (body: IngestRequest): Promise<IngestResponse> => {
    const res = await fetch(`${BASE}/api/ingest/fir`, {
      method: 'POST',
      headers: authHeaders({ 'Content-Type': 'application/json' }),
      body: JSON.stringify(body),
    })
    if (!res.ok) throw new ApiError(res.status, `POST /api/ingest/fir → ${res.status}`)
    return res.json() as Promise<IngestResponse>
  },
  scan: async (code: string, filename?: string): Promise<ScanResponse> => {
    const res = await fetch(`${BASE}/api/scan`, {
      method: 'POST',
      headers: authHeaders({ 'Content-Type': 'application/json' }),
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
      headers: authHeaders({ 'Content-Type': 'application/json' }),
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
  // ── evidence auto-resolution: full documents, not two names ──────────────
  resolveEvidence: async (text: string): Promise<EvidenceResolve> => {
    const res = await fetch(`${BASE}/api/resolve/evidence`, {
      method: 'POST',
      headers: authHeaders({ 'Content-Type': 'application/json' }),
      body: JSON.stringify({ text }),
    })
    if (!res.ok) throw new ApiError(res.status, `POST /api/resolve/evidence → ${res.status}`)
    return res.json() as Promise<EvidenceResolve>
  },
  resolveEvidencePdf: async (file: File): Promise<EvidenceResolve> => {
    const fd = new FormData()
    fd.append('file', file)
    const res = await fetch(`${BASE}/api/resolve/evidence/pdf`, {
      method: 'POST',
      headers: authHeaders(),
      body: fd,
    })
    const detail = await res.json().catch(() => null)
    if (!res.ok) throw new ApiError(res.status, detail?.detail ?? `evidence pdf → ${res.status}`)
    return detail as EvidenceResolve
  },
  // ── OCR: offline Hindi+English text extraction from a scanned FIR ─────────
  ocrExtract: async (file: File, auto = true): Promise<OcrResult> => {
    const fd = new FormData()
    fd.append('file', file)
    const res = await fetch(`${BASE}/api/ocr/extract?auto=${auto}`, {
      method: 'POST',
      headers: authHeaders(),
      body: fd,
    })
    const detail = (await res.json().catch(() => null)) as
      | (OcrResult & { detail?: string })
      | null
    if (!res.ok) throw new ApiError(res.status, detail?.detail ?? `ocr → ${res.status}`)
    return detail as OcrResult
  },
  // ── pluggable entity extractor (regex / hybrid / indner) ──────────────────
  ingestExtract: async (text: string, engine = 'hybrid'): Promise<ExtractResponse> => {
    const res = await fetch(`${BASE}/api/ingest/extract?engine=${engine}`, {
      method: 'POST',
      headers: authHeaders({ 'Content-Type': 'application/json' }),
      body: JSON.stringify({ text }),
    })
    const detail = (await res.json().catch(() => null)) as
      | (ExtractResponse & { detail?: string })
      | null
    if (!res.ok) throw new ApiError(res.status, detail?.detail ?? `extract → ${res.status}`)
    return detail as ExtractResponse
  },
  // ── deterministic person dossier ───────────────────────────────────────────
  resolvePerson: async (name: string, lang: 'en' | 'hi' = 'en'): Promise<PersonDossier> => {
    const res = await fetch(`${BASE}/api/resolve/person?lang=${lang}`, {
      method: 'POST',
      headers: authHeaders({ 'Content-Type': 'application/json' }),
      body: JSON.stringify({ name }),
    })
    const detail = (await res.json().catch(() => null)) as
      | (PersonDossier & { detail?: string })
      | null
    if (!res.ok) throw new ApiError(res.status, detail?.detail ?? `person dossier → ${res.status}`)
    return detail as PersonDossier
  },
  // ── offline English→Hindi demo layer ─────────────────────────────────────
  hindiTransliterate: async (texts: string[]): Promise<HindiBulkResponse> => {
    const res = await fetch(`${BASE}/api/hindi/transliterate`, {
      method: 'POST',
      headers: authHeaders({ 'Content-Type': 'application/json' }),
      body: JSON.stringify({ texts }),
    })
    const detail = (await res.json().catch(() => null)) as
      | (HindiBulkResponse & { detail?: string })
      | null
    if (!res.ok) throw new ApiError(res.status, detail?.detail ?? `hindi/transliterate → ${res.status}`)
    return detail as HindiBulkResponse
  },
  hindiTranslate: async (terms: string[]): Promise<HindiBulkResponse> => {
    const res = await fetch(`${BASE}/api/hindi/translate`, {
      method: 'POST',
      headers: authHeaders({ 'Content-Type': 'application/json' }),
      body: JSON.stringify({ terms }),
    })
    const detail = (await res.json().catch(() => null)) as
      | (HindiBulkResponse & { detail?: string })
      | null
    if (!res.ok) throw new ApiError(res.status, detail?.detail ?? `hindi/translate → ${res.status}`)
    return detail as HindiBulkResponse
  },
  hindiProfile: async (body: { fields?: Record<string, string>; text?: string }): Promise<HindiProfileResponse> => {
    const res = await fetch(`${BASE}/api/hindi/profile`, {
      method: 'POST',
      headers: authHeaders({ 'Content-Type': 'application/json' }),
      body: JSON.stringify(body),
    })
    const detail = (await res.json().catch(() => null)) as
      | (HindiProfileResponse & { detail?: string })
      | null
    if (!res.ok) throw new ApiError(res.status, detail?.detail ?? `hindi/profile → ${res.status}`)
    return detail as HindiProfileResponse
  },
  // ── DigiLocker e-KYC officer auth ─────────────────────────────────────────
  requestOtp: async (aadhaar: string): Promise<AuthOtpResult> => {
    const res = await fetch(`${BASE}/api/auth/request-otp`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ aadhaar }),
    })
    const body = (await res.json().catch(() => null)) as AuthOtpResult | null
    if (!res.ok || !body || body.ok === false) {
      throw new ApiError(res.status, body?.error ?? `request-otp → ${res.status}`)
    }
    return body
  },
  login: async (aadhaar: string, otp: string, purpose: string): Promise<AuthResult> => {
    const res = await fetch(`${BASE}/api/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ aadhaar, otp, purpose }),
    })
    const body = (await res.json()) as AuthResult & { ok?: boolean; error?: string }
    if (!res.ok || body.ok === false) {
      throw new ApiError(res.status, body.error ?? `login → ${res.status}`)
    }
    return body
  },
  authOfficers: async () => (await get<{ officers: AuthOfficer[] }>('/api/auth/officers')).officers,
  authStatus: () => get<AuthStatus>('/api/auth/status'),
  logout: async (): Promise<void> => {
    await fetch(`${BASE}/api/auth/logout`, { method: 'POST', headers: authHeaders() })
  },
  // ── warrant gate (DEPA consent artifacts — scoped, dual-signed, ledgered) ──
  requestWarrant: async (body: WarrantRequestIn): Promise<WarrantOut> => {
    const res = await fetch(`${BASE}/api/warrants`, {
      method: 'POST',
      headers: authHeaders({ 'Content-Type': 'application/json' }),
      body: JSON.stringify(body),
    })
    if (!res.ok) throw new ApiError(res.status, `POST /api/warrants → ${res.status}`)
    return res.json() as Promise<WarrantOut>
  },
  // countersigning as another officer (SP): approve with an explicit bearer token
  // so the four-eyes moment runs under THAT officer's verified session.
  approveWarrant: async (warrantId: string, body: WarrantApproveIn, bearerOverride?: string): Promise<WarrantOut> => {
    const res = await fetch(`${BASE}/api/warrants/${warrantId}/approve`, {
      method: 'POST',
      headers: bearerOverride
        ? { 'Content-Type': 'application/json', Authorization: `Bearer ${bearerOverride}` }
        : authHeaders({ 'Content-Type': 'application/json' }),
      body: JSON.stringify(body),
    })
    if (!res.ok) {
      const detail = await res.json().catch(() => null)
      throw new ApiError(res.status, detail?.detail ?? `approve → ${res.status}`)
    }
    return res.json() as Promise<WarrantOut>
  },
}

export interface AuthOtpResult {
  ok: boolean
  txn?: string
  bridge?: string
  hint?: string
  masked?: string
  error?: string
}
export interface AuthOfficer {
  id: string
  name: string
  badge: string
  role: 'IO' | 'FORENSIC' | 'SP'
  role_label: string
  vault: string
  district: string
  police_station: string
  aadhaar_masked: string
  demo?: { aadhaar: string; otp: string }
}
export interface AuthStatus {
  bridge: string
  production_adapter: string
  law: string
  session_ttl_seconds: number
  secret_mode: string
  storage: string
  roles: Record<string, string>
  enforcement: Record<string, string>
  ledger: { ok: boolean; records: number; first_bad_id: number | null }
}

export interface WarrantRequestIn {
  scope: string
  requester_id: string
  requester_role: string
  reason: string
}
export interface WarrantApproveIn {
  approver_id: string
  approver_role: string
}
export interface WarrantOut {
  ok: boolean
  warrant_id?: string | null
  status?: string | null
  scope?: string | null
  expires_at?: string | null
  error?: string | null
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
