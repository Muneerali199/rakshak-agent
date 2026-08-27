import { useEffect, useState } from 'react'
import {
  FileText, Shield, Fingerprint, CheckCircle2, AlertTriangle,
  ThumbsUp, ThumbsDown, Pencil, Link2, Loader2, Phone,
} from 'lucide-react'
import {
  api, ApiError,
  type EvidenceResponse, type ReviewStatus,
} from '@/lib/api'

const REVIEWER_ID = 'workbench-officer'

function Snippet({ text, span }: { text: string; span: [number, number] | null }) {
  if (!span) return <span className="text-slate-300">{text}</span>
  const [s, e] = span
  return (
    <span className="text-slate-300">
      {text.slice(0, s)}
      <mark className="rounded bg-cyan-400/15 px-0.5 text-cyan-300">{text.slice(s, e)}</mark>
      {text.slice(e)}
    </span>
  )
}

type Mode = 'idle' | 'modifying'

const MOCK_EVIDENCE: EvidenceResponse = {
  edge_id: 'E-MOCK',
  claim: 'मोहम्मद आरिफ़ (C00143) CONTACTED +9198xxxxxxxx (PH:8329...)',
  confidence: 0.94,
  creation_method: 'INFERRED',
  audit_hash: 'a3f7c2d9e8b1f4a6c5d3e7b9f2a1c8d4e6b3a5f7d9c1e8b4a2f6d3c7e9b1a5f2',
  hash_verified: true,
  source_documents: [
    {
      doc_id: 'FIR-2026-0007',
      doc_type: 'FIR',
      timestamp: '2026-03-16',
      snippet: 'मोहम्मद आरिफ़ ने शामिला को फोन किया और धमकी दी कि यदि पुलिस में शिकायत की तो परिणाम भुगतेंगे...',
      highlight_span: [0, 15],
      language: 'hi',
    },
    {
      doc_id: 'CDR-2026-0142',
      doc_type: 'CDR',
      timestamp: '2026-03-16T18:42:11',
      snippet: 'caller +9198xxxxxxxx → receiver +9172xxxxxxxx, 142s, tower Mumbai-Andheri',
      highlight_span: null,
      language: null,
    },
  ],
  review_status: 'PENDING',
  reviewer_actions: ['ACCEPT', 'REJECT', 'MODIFY'],
  victim_shield: false,
}

export default function EvidencePanel({
  edgeId, layerColorHint, onReviewed,
}: {
  edgeId: string | null
  layerColorHint?: string
  onReviewed?: (edgeId: string, status: ReviewStatus, confidence: number) => void
}) {
  const [ev, setEv] = useState<EvidenceResponse | null>(null)
  const [status, setStatus] = useState<ReviewStatus | null>(null)
  const [confidence, setConfidence] = useState<number>(1)
  const [loading, setLoading] = useState(false)
  const [copied, setCopied] = useState(false)
  const [busy, setBusy] = useState<'ACCEPT' | 'REJECT' | 'MODIFY' | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [mode, setMode] = useState<Mode>('idle')
  const [newConf, setNewConf] = useState(0.6)
  const [ledger, setLedger] = useState<{ ok: boolean; records: number } | null>(null)

  useEffect(() => {
    if (!edgeId) { setEv(null); setStatus(null); return }
    setLoading(true)
    setError(null)
    setMode('idle')
    api.evidence(edgeId)
      .then((d) => {
        setEv(d)
        setStatus(d.review_status)
        setConfidence(d.confidence)
        setNewConf(d.confidence)
      })
      .catch(() => { setEv(null); setStatus(null) })
      .finally(() => setLoading(false))
  }, [edgeId])

  useEffect(() => {
    if (!edgeId) return
    api.verifyLedger().then(setLedger).catch(() => setLedger(null))
  }, [edgeId])

  async function decide(decision: 'ACCEPT' | 'REJECT' | 'MODIFY', modifications?: Record<string, unknown>) {
    if (!ev || busy) return
    const prevStatus = status
    const prevConf = confidence
    const nextStatus: ReviewStatus = decision === 'REJECT' ? 'REJECTED' : 'ACCEPTED'
    const nextConf = decision === 'MODIFY' ? newConf : prevConf
    setBusy(decision)
    setError(null)
    setStatus(nextStatus)
    setConfidence(nextConf)

    try {
      await api.review({
        edge_id: ev.edge_id,
        decision,
        reviewer_id: REVIEWER_ID,
        modifications: modifications ?? null,
      })
      setMode('idle')
      onReviewed?.(ev.edge_id, nextStatus, nextConf)
    } catch (e) {
      setStatus(prevStatus)
      setConfidence(prevConf)
      setError(e instanceof ApiError && e.status === 422
        ? 'MODIFY needs a confidence between 0 and 1.'
        : `Review failed (${e instanceof ApiError ? e.status : 'network'}). Rolled back.`)
    } finally {
      setBusy(null)
    }
  }

  const accent = layerColorHint ?? '#22d3ee'
  const inferred = ev?.creation_method === 'INFERRED'
  const canModify = Boolean(ev && inferred && status === 'PENDING')
  const confPct = Math.round(confidence * 100)

  if (!edgeId) {
    return (
      <aside className="flex h-full w-[400px] shrink-0 flex-col border-l border-white/5 bg-[#0a0f1c]">
        {/* Mock evidence preview — makes the panel feel alive */}
        <div className="border-b border-white/5 p-4">
          <div className="flex items-center gap-2">
            <FileText size={14} className="text-cyan-400" />
            <h2 className="font-mono text-[10px] uppercase tracking-[0.3em] text-slate-400">Evidence Provenance</h2>
          </div>
          <p className="mt-2 text-sm leading-snug text-slate-300">{MOCK_EVIDENCE.claim}</p>
          <div className="mt-2 flex items-center gap-2">
            <span
              className="rounded px-1.5 py-0.5 font-mono text-[9px]"
              style={{ color: accent, border: `1px solid ${accent}40`, background: `${accent}10` }}
            >
              Inferred · pending
            </span>
            <span className="font-mono text-[10px] text-slate-400">confidence {Math.round(MOCK_EVIDENCE.confidence * 100)}%</span>
          </div>
        </div>

        {/* Source snippet */}
        <div className="flex-1 space-y-3 overflow-y-auto p-4">
          <h3 className="font-mono text-[9px] uppercase tracking-[0.25em] text-slate-500">Source Snippet</h3>
          <div className="rounded-lg border border-slate-700/50 bg-slate-800/50 p-3 backdrop-blur-sm">
            <div className="mb-1.5 flex items-center justify-between font-mono text-[9px] text-slate-500">
              <span className="flex items-center gap-1">
                <FileText size={9} /> FIR · {MOCK_EVIDENCE.source_documents[0].doc_id}
              </span>
              <span>hi · {MOCK_EVIDENCE.source_documents[0].timestamp}</span>
            </div>
            <p className="text-xs leading-relaxed text-slate-300 font-mono">
              <span className="text-cyan-400 font-medium">मोहम्मद आरिफ़</span> ने शामिला को फोन किया और धमकी दी कि यदि पुलिस में शिकायत की तो परिणाम भुगतेंगे...
            </p>
          </div>

          <div className="rounded-lg border border-slate-700/50 bg-slate-800/50 p-3 backdrop-blur-sm">
            <div className="mb-1.5 flex items-center justify-between font-mono text-[9px] text-slate-500">
              <span className="flex items-center gap-1">
                <Phone size={9} className="text-cyan-400" /> CDR · {MOCK_EVIDENCE.source_documents[1].doc_id}
              </span>
              <span>{MOCK_EVIDENCE.source_documents[1].timestamp}</span>
            </div>
            <p className="text-xs leading-relaxed text-slate-300 font-mono">
              {MOCK_EVIDENCE.source_documents[1].snippet}
            </p>
          </div>

          {/* Confidence bar */}
          <div className="space-y-2 pt-2">
            <h3 className="font-mono text-[9px] uppercase tracking-[0.25em] text-slate-500">Confidence</h3>
            <div className="flex items-center gap-3">
              <span className="font-mono text-xs text-slate-300">{confPct}%</span>
              <div className="h-2 flex-1 overflow-hidden rounded-full bg-slate-800">
                <div
                  className="h-full rounded-full bg-gradient-to-r from-emerald-500 to-emerald-400 transition-all duration-300"
                  style={{ width: `${confPct}%` }}
                />
              </div>
            </div>
            <p className="font-mono text-[9px] text-slate-500">
              Method: Transliteration + Phone Match
            </p>
          </div>

          {/* Hash badge */}
          <div className="flex items-center gap-2 pt-1">
            <span className="inline-flex items-center gap-1.5 rounded-full border border-emerald-500/30 bg-emerald-500/10 px-2.5 py-1 font-mono text-[9px] text-emerald-400">
              <Fingerprint size={10} /> SHA-256 Verified ✓
            </span>
            <span className="inline-flex items-center gap-1.5 rounded-full border border-cyan-500/30 bg-cyan-500/10 px-2.5 py-1 font-mono text-[9px] text-cyan-400">
              <Link2 size={10} /> Ledger Chained
            </span>
          </div>

          <p className="pt-3 text-center font-mono text-[9px] leading-relaxed text-slate-600">
            Click any <span className="text-slate-400">edge</span> in the graph to load real evidence.
          </p>
        </div>
      </aside>
    )
  }

  return (
    <aside className="flex h-full w-[400px] shrink-0 flex-col border-l border-white/5 bg-[#0a0f1c]">
      {/* Header */}
      <div className="border-b border-white/5 p-4">
        <div className="flex items-center gap-2">
          <FileText size={14} className="text-cyan-400" />
          <h2 className="font-mono text-[10px] uppercase tracking-[0.3em] text-slate-400">Evidence Provenance</h2>
        </div>
        {loading && (
          <div className="mt-3 flex items-center gap-2 font-mono text-xs text-slate-500">
            <Loader2 size={14} className="animate-spin" /> loading…
          </div>
        )}
        {ev && (
          <>
            {ev.victim_shield && (
              <div className="mt-3 rounded-lg border border-purple-400/30 bg-purple-400/10 px-3 py-2 backdrop-blur-sm">
                <div className="flex items-center gap-1.5">
                  <Shield size={12} className="text-purple-400" />
                  <p className="font-mono text-[9px] uppercase tracking-[0.2em] text-purple-400">
                    Victim-Shield Active
                  </p>
                </div>
                <p className="mt-1 text-[11px] leading-snug text-slate-400">
                  A protected party is pseudonymized under Women Safety Division policy.
                  The system analyzes offender networks — never victims.
                </p>
              </div>
            )}
            <p className="mt-2 text-sm leading-snug text-slate-100">{ev.claim}</p>
            <div className="mt-2 flex flex-wrap items-center gap-2">
              <span
                className="rounded px-1.5 py-0.5 font-mono text-[9px]"
                style={{ color: accent, border: `1px solid ${accent}40`, background: `${accent}10` }}
              >
                {inferred ? (status === 'ACCEPTED' ? 'Inferred · verified' : 'Inferred · pending') : 'Observed'}
              </span>
              <span className="font-mono text-[10px] text-slate-400">
                confidence {confPct}%
              </span>
              {status === 'ACCEPTED' && (
                <span className="flex items-center gap-0.5 font-mono text-[10px] text-emerald-400">
                  <CheckCircle2 size={10} /> reviewed
                </span>
              )}
            </div>
            {ledger && (
              <div
                className="mt-2 flex items-center gap-1.5 font-mono text-[9px]"
                title={`Hash-chained audit ledger · ${ledger.records} record(s)`}
              >
                {ledger.ok ? (
                  <Link2 size={11} className="text-emerald-400" />
                ) : (
                  <AlertTriangle size={11} className="text-red-400" />
                )}
                <span className={ledger.ok ? 'text-emerald-400' : 'text-red-400'}>
                  {ledger.ok ? 'ledger verified' : 'LEDGER BROKEN'}
                </span>
                <span className="text-slate-600">· {ledger.records} chained record(s)</span>
              </div>
            )}
          </>
        )}
      </div>

      {ev && (
        <>
          {/* Provenance / SHA-256 */}
          <div className="border-b border-white/5 p-4">
            <h3 className="mb-2 flex items-center gap-1.5 font-mono text-[9px] uppercase tracking-[0.25em] text-slate-500">
              <Fingerprint size={11} /> Audit Hash · SHA-256
            </h3>
            <div className="rounded-lg border border-slate-700/50 bg-slate-800/40 p-2.5 backdrop-blur-sm">
              <div className="mb-1 flex items-center justify-between">
                <span className="font-mono text-[9px] text-slate-500">integrity</span>
                {ev.hash_verified ? (
                  <span className="flex items-center gap-1 font-mono text-[9px] text-emerald-400">
                    <CheckCircle2 size={10} /> verified
                  </span>
                ) : (
                  <span className="flex items-center gap-1 font-mono text-[9px] text-red-400">
                    <AlertTriangle size={10} /> TAMPERED
                  </span>
                )}
              </div>
              <button
                onClick={() => { navigator.clipboard?.writeText(ev.audit_hash); setCopied(true); setTimeout(() => setCopied(false), 1200) }}
                title={ev.audit_hash}
                className="w-full truncate text-left font-mono text-[10px] text-slate-300 transition-colors hover:text-cyan-400"
              >
                {ev.audit_hash.slice(0, 10)}…{ev.audit_hash.slice(-8)} {copied ? '· copied' : '· copy'}
              </button>
            </div>
          </div>

          {/* Source documents */}
          <div className="flex-1 space-y-3 overflow-y-auto p-4">
            <h3 className="flex items-center gap-1.5 font-mono text-[9px] uppercase tracking-[0.25em] text-slate-500">
              <FileText size={11} /> Source Documents · {ev.source_documents.length}
            </h3>
            {ev.source_documents.map((doc, i) => (
              <div
                key={i}
                className="rounded-lg border border-slate-700/50 bg-slate-800/50 p-3 backdrop-blur-sm"
              >
                <div className="mb-1.5 flex items-center justify-between font-mono text-[9px] text-slate-500">
                  <span className="flex items-center gap-1">
                    <FileText size={9} /> {doc.doc_type} · {doc.doc_id}
                  </span>
                  <span>{doc.language ?? ''} {doc.timestamp}</span>
                </div>
                <p className="text-xs leading-relaxed text-slate-300 font-mono">
                  <Snippet text={doc.snippet} span={doc.highlight_span} />
                </p>
              </div>
            ))}

            {/* Confidence bar */}
            <div className="space-y-2 pt-1">
              <h3 className="font-mono text-[9px] uppercase tracking-[0.25em] text-slate-500">Confidence</h3>
              <div className="flex items-center gap-3">
                <span className="font-mono text-xs text-slate-300">{confPct}%</span>
                <div className="h-2 flex-1 overflow-hidden rounded-full bg-slate-800">
                  <div
                    className="h-full rounded-full bg-gradient-to-r from-emerald-500 to-emerald-400 transition-all duration-300"
                    style={{ width: `${confPct}%` }}
                  />
                </div>
              </div>
            </div>
          </div>

          {/* Human-in-the-loop actions */}
          <div className="sticky bottom-0 border-t border-white/5 bg-[#0a0f1c]/95 p-4 backdrop-blur-md">
            {status && status !== 'PENDING' && mode === 'idle' ? (
              <p
                className="flex items-center justify-center gap-1.5 text-center font-mono text-xs"
                style={{ color: status === 'ACCEPTED' ? '#34d399' : '#ff2d55' }}
              >
                {status === 'ACCEPTED' ? (
                  <><CheckCircle2 size={14} /> Accepted — logged & hashed (Algorithm 8)</>
                ) : (
                  <><AlertTriangle size={14} /> Rejected — ghosted in graph, kept in audit log</>
                )}
              </p>
            ) : mode === 'modifying' ? (
              <div className="space-y-3">
                <div className="flex items-center justify-between font-mono text-[10px] text-slate-400">
                  <span>reviewed confidence</span>
                  <span className="text-cyan-400">{newConf.toFixed(2)}</span>
                </div>
                <input type="range" min={0} max={1} step={0.01} value={newConf}
                       onChange={(e) => setNewConf(Number(e.target.value))}
                       className="w-full accent-cyan-400" />
                <div className="grid grid-cols-2 gap-2">
                  <button disabled={busy !== null} onClick={() => decide('MODIFY', { confidence: newConf })}
                          className="flex items-center justify-center gap-1.5 rounded-lg bg-cyan-500/15 py-2 text-xs font-medium text-cyan-400 transition-colors hover:bg-cyan-500/25 disabled:opacity-50">
                    {busy === 'MODIFY' ? <Loader2 size={12} className="animate-spin" /> : <Pencil size={12} />}
                    {busy === 'MODIFY' ? 'saving…' : 'Save modification'}
                  </button>
                  <button disabled={busy !== null} onClick={() => { setMode('idle'); setNewConf(confidence) }}
                          className="rounded-lg bg-slate-700/40 py-2 text-xs font-medium text-slate-300 transition-colors hover:bg-slate-700/60 disabled:opacity-50">
                    Cancel
                  </button>
                </div>
              </div>
            ) : (
              <div className="grid grid-cols-3 gap-2">
                <button disabled={busy !== null} onClick={() => decide('ACCEPT')}
                        className="flex items-center justify-center gap-1.5 rounded-lg bg-emerald-500/15 py-2 text-xs font-medium text-emerald-400 transition-colors hover:bg-emerald-500/25 disabled:opacity-50">
                  {busy === 'ACCEPT' ? <Loader2 size={12} className="animate-spin" /> : <ThumbsUp size={12} />}
                  {busy === 'ACCEPT' ? '…' : 'Accept'}
                </button>
                <button disabled={busy !== null} onClick={() => decide('REJECT')}
                        className="flex items-center justify-center gap-1.5 rounded-lg bg-red-500/15 py-2 text-xs font-medium text-red-400 transition-colors hover:bg-red-500/25 disabled:opacity-50">
                  {busy === 'REJECT' ? <Loader2 size={12} className="animate-spin" /> : <ThumbsDown size={12} />}
                  {busy === 'REJECT' ? '…' : 'Reject'}
                </button>
                <button disabled={!canModify || busy !== null}
                        onClick={() => { setMode('modifying'); setNewConf(confidence) }}
                        title={canModify ? 'Adjust the confidence of this inferred edge' : 'Modify applies to PENDING inferred edges only'}
                        className="flex items-center justify-center gap-1.5 rounded-lg bg-slate-700/40 py-2 text-xs font-medium text-slate-300 transition-colors hover:bg-slate-700/60 disabled:cursor-not-allowed disabled:opacity-40">
                  <Pencil size={12} /> Modify
                </button>
              </div>
            )}
            {error && <p className="mt-2 flex items-center gap-1 font-mono text-[10px] text-red-400"><AlertTriangle size={10} /> {error}</p>}
            <p className="mt-2 text-center font-mono text-[8px] tracking-wider text-slate-600">
              decision logged &amp; hash-chained · human-in-the-loop
            </p>
          </div>
        </>
      )}
    </aside>
  )
}
