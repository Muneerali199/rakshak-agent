import { useEffect, useState } from 'react'
import { api, LAYER_COLOR, type EvidenceResponse, type ReviewStatus } from '@/lib/api'

// Renders a source snippet, highlighting the matched character span (NER provenance).
function Snippet({ text, span }: { text: string; span: [number, number] | null }) {
  if (!span) return <span className="text-zinc-300">{text}</span>
  const [s, e] = span
  return (
    <span className="text-zinc-300">
      {text.slice(0, s)}
      <mark className="rounded bg-amber-400/20 px-0.5 text-amber-200">{text.slice(s, e)}</mark>
      {text.slice(e)}
    </span>
  )
}

export default function EvidencePanel({
  edgeId, layerColorHint,
}: { edgeId: string | null; layerColorHint?: string }) {
  const [ev, setEv] = useState<EvidenceResponse | null>(null)
  const [status, setStatus] = useState<ReviewStatus | null>(null)
  const [loading, setLoading] = useState(false)
  const [copied, setCopied] = useState(false)

  useEffect(() => {
    if (!edgeId) { setEv(null); return }
    setLoading(true)
    api.evidence(edgeId)
      .then((d) => { setEv(d); setStatus(d.review_status) })
      .catch(() => setEv(null))
      .finally(() => setLoading(false))
  }, [edgeId])

  if (!edgeId) {
    return (
      <aside className="flex h-full w-[400px] shrink-0 items-center justify-center border-l border-zinc-800 bg-[#08090c] p-6">
        <p className="text-center font-mono text-xs text-zinc-600">
          Click an edge in the graph<br />to inspect its evidence.
        </p>
      </aside>
    )
  }

  const accent = layerColorHint ?? (ev ? LAYER_COLOR[/* fallback */ 'communication'] : '#00f0ff')
  const inferred = ev?.creation_method === 'INFERRED'

  return (
    <aside className="flex h-full w-[400px] shrink-0 flex-col overflow-y-auto border-l border-zinc-800 bg-[#08090c]">
      <div className="border-b border-zinc-800 p-4">
        <h2 className="font-mono text-[10px] uppercase tracking-[0.3em] text-zinc-500">Evidence</h2>
        {loading && <p className="mt-3 font-mono text-xs text-zinc-500">loading…</p>}
        {ev && (
          <>
            <p className="mt-2 text-sm leading-snug text-zinc-100">{ev.claim}</p>
            <div className="mt-2 flex items-center gap-2">
              <span className="rounded px-1.5 py-0.5 font-mono text-[9px]"
                    style={{ color: accent, border: `1px solid ${accent}55` }}>
                {inferred ? 'Inferred' : 'Observed'}
              </span>
              <span className="font-mono text-[10px] text-zinc-400">
                confidence {(ev.confidence * 100).toFixed(0)}%
              </span>
            </div>
          </>
        )}
      </div>

      {ev && (
        <>
          {/* Provenance / SHA-256 */}
          <div className="border-b border-zinc-800 p-4">
            <h3 className="mb-2 font-mono text-[9px] uppercase tracking-[0.25em] text-zinc-500">Provenance</h3>
            <div className="rounded-md border border-zinc-800 bg-[#0b0d12] p-2.5">
              <div className="mb-1 flex items-center justify-between">
                <span className="font-mono text-[9px] text-zinc-500">audit hash · SHA-256</span>
                {ev.hash_verified
                  ? <span className="font-mono text-[9px] text-[#34d399]">✓ verified</span>
                  : <span className="font-mono text-[9px] text-[#ff2d55]">⚠ TAMPERED</span>}
              </div>
              <button
                onClick={() => { navigator.clipboard?.writeText(ev.audit_hash); setCopied(true); setTimeout(() => setCopied(false), 1200) }}
                title={ev.audit_hash}
                className="w-full truncate text-left font-mono text-[10px] text-zinc-300 hover:text-[#00f0ff]"
              >
                {ev.audit_hash.slice(0, 10)}…{ev.audit_hash.slice(-8)} {copied ? '· copied' : '· copy'}
              </button>
            </div>
          </div>

          {/* Source documents */}
          <div className="flex-1 space-y-3 p-4">
            <h3 className="font-mono text-[9px] uppercase tracking-[0.25em] text-zinc-500">
              Source documents · {ev.source_documents.length}
            </h3>
            {ev.source_documents.map((doc, i) => (
              <div key={i} className="rounded-md border border-zinc-800 bg-[#0b0d12] p-2.5">
                <div className="mb-1.5 flex items-center justify-between font-mono text-[9px] text-zinc-500">
                  <span>{doc.doc_type} · {doc.doc_id}</span>
                  <span>{doc.language ?? ''} {doc.timestamp}</span>
                </div>
                <p className="font-mono text-[11px] leading-relaxed">
                  <Snippet text={doc.snippet} span={doc.highlight_span} />
                </p>
              </div>
            ))}
          </div>

          {/* Human-in-the-loop actions (Algorithm 8) */}
          <div className="sticky bottom-0 border-t border-zinc-800 bg-[#08090c] p-4">
            {status && status !== 'PENDING' ? (
              <p className="text-center font-mono text-xs"
                 style={{ color: status === 'ACCEPTED' ? '#34d399' : '#ff2d55' }}>
                {status === 'ACCEPTED' ? '✓ Accepted — promoted to observed' : '✕ Rejected — removed from graph'}
              </p>
            ) : (
              <div className="grid grid-cols-3 gap-2">
                <button onClick={() => setStatus('ACCEPTED')}
                        className="rounded bg-[#34d399]/15 py-2 text-xs font-medium text-[#34d399] hover:bg-[#34d399]/25">✓ Accept</button>
                <button onClick={() => setStatus('REJECTED')}
                        className="rounded bg-[#ff2d55]/15 py-2 text-xs font-medium text-[#ff2d55] hover:bg-[#ff2d55]/25">✕ Reject</button>
                <button className="rounded bg-zinc-700/40 py-2 text-xs font-medium text-zinc-300 hover:bg-zinc-700/60">✎ Modify</button>
              </div>
            )}
            <p className="mt-2 text-center font-mono text-[8px] tracking-wider text-zinc-600">
              decision logged &amp; hashed · human-in-the-loop
            </p>
          </div>
        </>
      )}
    </aside>
  )
}
