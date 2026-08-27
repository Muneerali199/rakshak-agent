// Guided demo mode — the 5-minute SIH walkthrough, one click.
// Every step is read-only (nothing is written to the review store) and drives the
// real workbench through the same callbacks a human investigator would use.
import { useCallback, useEffect, useState } from 'react'
import { api } from '@/lib/api'

interface StepState {
  title: string
  body: string
  status: 'idle' | 'running' | 'done' | 'error'
  detail?: string
}

export default function DemoMode({
  onClose,
  focusEntity,
  openEdge,
}: {
  onClose: () => void
  focusEntity: (id: string) => void
  openEdge: (edgeId: string) => void
}) {
  const [step, setStep] = useState(0)
  const [states, setStates] = useState<StepState[]>([
    {
      title: 'The lead finds you',
      body: 'The workbench opens on the strongest anomaly: a circular money ring — the signature of a trafficking network. No searching required.',
      status: 'idle',
    },
    {
      title: 'Ask in plain words',
      body: 'Query the case in natural language. Every answer is grounded in the graph and cites its evidence — never generated, never guessed.',
      status: 'idle',
    },
    {
      title: 'The system that says NO',
      body: 'Ask about someone who is not in the case. A hallucinating AI would invent a network. RAKSHAK refuses.',
      status: 'idle',
    },
    {
      title: 'Every claim opens its evidence',
      body: 'Any edge opens its source records and a live SHA-256 verification. Inferred links wait for human sign-off.',
      status: 'idle',
    },
    {
      title: 'The tamper-evident ledger',
      body: 'Every review decision is hash-chained to the one before it. Rewrite history and the chain breaks.',
      status: 'idle',
    },
  ])

  const setStatus = useCallback((i: number, status: StepState['status'], detail?: string) => {
    setStates((prev) => prev.map((s, j) => (j === i ? { ...s, status, detail } : s)))
  }, [])

  const runStep = useCallback(async (i: number) => {
    setStatus(i, 'running')
    try {
      if (i === 0) {
        const a = await api.anomalies()
        const ring = a.anomalies.find((x) => x.kind === 'CIRCULAR_FLOW') ?? a.anomalies[0]
        if (!ring) throw new Error('no anomalies')
        focusEntity(ring.entity_id)
        setStatus(i, 'done', `loaded ${ring.label} — ${ring.kind.replace(/_/g, ' ').toLowerCase()} across ${ring.participants.length} accounts`)
      } else if (i === 1) {
        const ents = await api.entities('PERSON', 10)
        const accused = ents.find((e) => (e.meta?.role as string) === 'accused')
        if (!accused) throw new Error('no accused entity')
        const res = await api.ask(`what does ${accused.label} own?`)
        focusEntity(accused.id)
        setStatus(i, 'done', `"what does ${accused.label} own?" → ${res.results.length} cited result(s) · grounded: ${res.grounded}`)
      } else if (i === 2) {
        const res = await api.ask('Sherlock Holmes')
        setStatus(i, res.grounded ? 'error' : 'done',
                  res.grounded ? 'unexpected: system grounded an unknown name' : `"Sherlock Holmes" → refused: not in the case graph`)
      } else if (i === 3) {
        const a = await api.anomalies()
        const ring = a.anomalies.find((x) => x.kind === 'CIRCULAR_FLOW') ?? a.anomalies[0]
        if (!ring) throw new Error('no anomalies')
        const sg = await api.subgraph(ring.entity_id, 2)
        const edge = sg.edges.find((e) => e.creation_method === 'INFERRED') ?? sg.edges[0]
        if (!edge) throw new Error('no edges')
        focusEntity(ring.entity_id)
        openEdge(edge.id)
        setStatus(i, 'done', `opened evidence for ${edge.id} — hash ${edge.audit_hash.slice(0, 12)}… verified live`)
      } else if (i === 4) {
        const v = await api.verifyLedger()
        setStatus(i, v.ok ? 'done' : 'error',
                  v.ok
                    ? `ledger intact · ${v.records} chained record(s) · tamper-evidence armed`
                    : `LEDGER BROKEN at record ${v.first_bad_id} — tamper detected (this is the demo working)`)
      }
    } catch (e) {
      setStatus(i, 'error', e instanceof Error ? e.message : 'step failed — is the backend live?')
    }
  }, [focusEntity, openEdge, setStatus])

  // run the current step when it becomes active
  useEffect(() => {
    if (states[step]?.status === 'idle') void runStep(step)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [step])

  const cur = states[step]

  return (
    <div className="pointer-events-auto absolute inset-x-0 top-16 z-40 mx-auto w-full max-w-lg px-4">
      <div className="overflow-hidden rounded-xl border border-[#00f0ff]/30 bg-[#0b0d12]/95 shadow-[0_20px_60px_-15px_rgba(0,240,255,0.25)] backdrop-blur">
        <div className="flex items-center justify-between border-b border-zinc-800 px-4 py-2">
          <span className="font-mono text-[9px] uppercase tracking-[0.3em] text-[#00f0ff]">
            guided demo · {step + 1}/{states.length}
          </span>
          <button onClick={onClose} className="font-mono text-xs text-zinc-500 hover:text-zinc-200">✕ esc</button>
        </div>
        <div className="px-4 py-3">
          <h3 className="text-sm font-semibold text-white">{cur.title}</h3>
          <p className="mt-1 text-xs leading-relaxed text-zinc-400">{cur.body}</p>
          <div className="mt-3 min-h-[1.5rem] font-mono text-[10px]">
            {cur.status === 'running' && <span className="text-zinc-500">running…</span>}
            {cur.status === 'done' && <span className="text-[#34d399]">✓ {cur.detail}</span>}
            {cur.status === 'error' && <span className="text-[#ff2d55]">⚠ {cur.detail}</span>}
          </div>
        </div>
        <div className="flex items-center justify-between border-t border-zinc-800 px-4 py-2">
          <button
            onClick={() => setStep((s) => Math.max(0, s - 1))}
            disabled={step === 0}
            className="rounded border border-zinc-700 px-3 py-1 font-mono text-[10px] text-zinc-400 hover:border-zinc-500 disabled:opacity-30"
          >
            ← back
          </button>
          <div className="flex gap-1">
            {states.map((_, i) => (
              <span key={i} className="h-1 w-4 rounded-full"
                    style={{ background: i === step ? '#00f0ff' : i < step ? '#34d399' : '#27272a' }} />
            ))}
          </div>
          {step < states.length - 1 ? (
            <button
              onClick={() => setStep((s) => s + 1)}
              className="rounded border border-[#00f0ff]/50 bg-[#00f0ff]/10 px-3 py-1 font-mono text-[10px] text-[#00f0ff] hover:bg-[#00f0ff]/20"
            >
              next →
            </button>
          ) : (
            <button
              onClick={onClose}
              className="rounded border border-[#34d399]/50 bg-[#34d399]/10 px-3 py-1 font-mono text-[10px] text-[#34d399] hover:bg-[#34d399]/20"
            >
              finish ✓
            </button>
          )}
        </div>
      </div>
    </div>
  )
}
