import { useRef, useState } from 'react'
import { api, type QueryResponse } from '@/lib/api'

// Grounded NL query bar (paper §16): answers come only from the case graph and
// cite their evidence. Clicking a result focuses the entity and opens the evidence.
export default function QueryBar({
  onResult,
}: {
  onResult: (focusEntityId: string, edgeId?: string) => void
}) {
  const [q, setQ] = useState('')
  const [res, setRes] = useState<QueryResponse | null>(null)
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState<string | null>(null)
  const boxRef = useRef<HTMLDivElement>(null)

  async function ask(question?: string) {
    const query = (question ?? q).trim()
    if (!query) return
    setBusy(true)
    setErr(null)
    try {
      setRes(await api.ask(query))
    } catch {
      setErr('Query failed — is the backend running on :8000?')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div ref={boxRef} className="relative z-20 shrink-0 border-b border-zinc-800 bg-[#08090c] px-4 py-2">
      <div className="flex items-center gap-2">
        <span className="font-mono text-[10px] text-zinc-600">⌕ ask</span>
        <input
          value={q}
          onChange={(e) => setQ(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && ask()}
          placeholder='who did Aneel Sharmaa contact? · how are X and Y connected? · any suspicious activity?'
          className="min-w-0 flex-1 rounded-md border border-zinc-800 bg-[#0b0d12] px-3 py-1.5 font-mono text-xs text-zinc-100 outline-none placeholder:text-zinc-600 focus:border-[#00f0ff]/50"
        />
        <button onClick={() => ask()} disabled={busy || !q.trim()}
                className="shrink-0 rounded-md bg-[#00f0ff]/10 px-3 py-1.5 font-mono text-xs text-[#00f0ff] hover:bg-[#00f0ff]/20 disabled:opacity-50">
          {busy ? '…' : 'Ask'}
        </button>
      </div>

      {err && <p className="mt-1.5 font-mono text-[10px] text-[#ff2d55]">{err}</p>}

      {res && (
        <div className="absolute inset-x-4 top-full z-30 mt-1 max-h-[60vh] overflow-y-auto rounded-lg border border-zinc-700 bg-[#0b0d12] p-3 shadow-2xl">
          <div className="flex items-start justify-between gap-3">
            <p className="text-xs leading-relaxed text-zinc-200">{res.answer}</p>
            <div className="flex shrink-0 items-center gap-2">
              <span className="rounded px-1.5 py-0.5 font-mono text-[8px] uppercase"
                    style={res.grounded
                      ? { color: '#34d399', border: '1px solid #34d39955' }
                      : { color: '#f59e0b', border: '1px solid #f59e0b55' }}>
                {res.grounded ? 'grounded' : 'refused'}
              </span>
              <button onClick={() => setRes(null)} className="font-mono text-[10px] text-zinc-500 hover:text-zinc-200">✕</button>
            </div>
          </div>

          {res.results.length > 0 && (
            <ul className="mt-2 space-y-1 border-t border-zinc-800 pt-2">
              {res.results.map((r) => (
                <li key={r.edge_id}>
                  <button onClick={() => onResult(r.focus_entity_id, r.edge_id)}
                          className="flex w-full items-center justify-between gap-3 rounded px-2 py-1.5 text-left hover:bg-white/[0.04]">
                    <span className="min-w-0 truncate font-mono text-[10px] text-zinc-300">{r.claim}</span>
                    <span className="shrink-0 font-mono text-[9px] text-zinc-600">
                      {r.provenance?.split(':').pop()} {r.confidence != null && `· ${r.confidence.toFixed(2)}`}
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          )}

          <p className="mt-2 border-t border-zinc-800 pt-1.5 font-mono text-[8px] text-zinc-600">
            {res.citations.length > 0 && `${res.citations.length} evidence citation(s) · `}
            {res.disclosure}
          </p>
        </div>
      )}
    </div>
  )
}
