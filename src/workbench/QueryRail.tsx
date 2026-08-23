import { useState } from 'react'
import { api, LAYER_COLOR, LAYER_LABEL, type EntitySummary, type LayerName, type ResolveResponse } from '@/lib/api'

const ALL_LAYERS: LayerName[] = ['communication', 'financial', 'spatial']

// Left rail: entity search/list (drives the graph), an inline /api/resolve tester
// (the demo's "Mohd Arif" moment), and layer / confidence filters.
export default function QueryRail({
  entities, activeId, onPick, layers, setLayers, minConf, setMinConf, showInferred, setShowInferred,
}: {
  entities: EntitySummary[]
  activeId: string | null
  onPick: (id: string) => void
  layers: LayerName[]
  setLayers: (l: LayerName[]) => void
  minConf: number
  setMinConf: (n: number) => void
  showInferred: boolean
  setShowInferred: (b: boolean) => void
}) {
  return (
    <aside className="flex h-full w-80 shrink-0 flex-col gap-5 overflow-y-auto border-r border-zinc-800 bg-[#08090c] p-4">
      <ResolveTester />

      <div>
        <h3 className="mb-2 font-mono text-[10px] uppercase tracking-[0.25em] text-zinc-500">Entities · by risk</h3>
        <ul className="space-y-1">
          {entities.map((e) => (
            <li key={e.id}>
              <button
                onClick={() => onPick(e.id)}
                className={[
                  'flex w-full items-center justify-between rounded-md border px-2.5 py-1.5 text-left transition-colors',
                  e.id === activeId ? 'border-[#00f0ff]/50 bg-[#00f0ff]/5' : 'border-transparent hover:border-zinc-700 hover:bg-white/[0.03]',
                ].join(' ')}
              >
                <span className="min-w-0 truncate text-xs text-zinc-200">{e.label}</span>
                {e.risk != null && (
                  <span className="ml-2 shrink-0 font-mono text-[9px]"
                        style={{ color: e.risk > 0.6 ? '#ff2d55' : '#8b93a7' }}>
                    {e.risk.toFixed(2)}
                  </span>
                )}
              </button>
            </li>
          ))}
          {entities.length === 0 && <li className="font-mono text-[10px] text-zinc-600">loading…</li>}
        </ul>
      </div>

      <div className="space-y-3 border-t border-zinc-800 pt-4">
        <h3 className="font-mono text-[10px] uppercase tracking-[0.25em] text-zinc-500">Layers</h3>
        {ALL_LAYERS.map((l) => (
          <label key={l} className="flex cursor-pointer items-center gap-2 text-xs text-zinc-300">
            <input
              type="checkbox"
              checked={layers.includes(l)}
              onChange={() =>
                setLayers(layers.includes(l) ? layers.filter((x) => x !== l) : [...layers, l])
              }
              className="accent-[#00f0ff]"
            />
            <span className="h-2 w-2 rounded-full" style={{ background: LAYER_COLOR[l] }} />
            {LAYER_LABEL[l]}
          </label>
        ))}
      </div>

      <div className="space-y-3 border-t border-zinc-800 pt-4">
        <label className="block text-xs text-zinc-300">
          <span className="font-mono text-[10px] uppercase tracking-[0.25em] text-zinc-500">
            Confidence floor · {minConf.toFixed(2)}
          </span>
          <input type="range" min={0} max={1} step={0.05} value={minConf}
                 onChange={(e) => setMinConf(Number(e.target.value))}
                 className="mt-2 w-full accent-[#00f0ff]" />
        </label>
        <label className="flex cursor-pointer items-center gap-2 text-xs text-zinc-300">
          <input type="checkbox" checked={showInferred} onChange={(e) => setShowInferred(e.target.checked)}
                 className="accent-[#71717a]" />
          Show inferred edges <span className="text-zinc-500">(dashed)</span>
        </label>
      </div>
    </aside>
  )
}

function ResolveTester() {
  const [a, setA] = useState('Mohammad Arif')
  const [b, setB] = useState('मोहम्मद आरिफ़')
  const [res, setRes] = useState<ResolveResponse | null>(null)
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState<string | null>(null)

  async function run() {
    setBusy(true); setErr(null)
    try { setRes(await api.resolve({ name_a: a, name_b: b })) }
    catch { setErr('API unreachable — is uvicorn running on :8000?') }
    finally { setBusy(false) }
  }

  const color = res?.decision === 'MATCH' ? '#34d399' : res?.decision === 'UNCERTAIN' ? '#f59e0b' : '#ff2d55'

  return (
    <div className="rounded-lg border border-zinc-800 bg-white/[0.02] p-3">
      <h3 className="mb-2 font-mono text-[10px] uppercase tracking-[0.25em] text-zinc-500">Identity Resolution</h3>
      <input value={a} onChange={(e) => setA(e.target.value)}
             className="mb-1.5 w-full rounded border border-zinc-700 bg-[#0b0d12] px-2 py-1 text-xs text-zinc-100 outline-none focus:border-[#00f0ff]/50" />
      <input value={b} onChange={(e) => setB(e.target.value)}
             className="mb-2 w-full rounded border border-zinc-700 bg-[#0b0d12] px-2 py-1 text-xs text-zinc-100 outline-none focus:border-[#00f0ff]/50" />
      <button onClick={run} disabled={busy}
              className="w-full rounded bg-[#00f0ff]/10 py-1.5 text-xs font-medium text-[#00f0ff] hover:bg-[#00f0ff]/20 disabled:opacity-50">
        {busy ? 'Resolving…' : 'Resolve'}
      </button>
      {err && <p className="mt-2 text-[10px] text-[#ff2d55]">{err}</p>}
      {res && (
        <div className="mt-3 space-y-2">
          <div className="flex items-center justify-between">
            <span className="font-mono text-sm font-bold" style={{ color }}>{res.decision}</span>
            <span className="font-mono text-xs text-zinc-300">{(res.confidence * 100).toFixed(0)}%</span>
          </div>
          {(['name', 'phonetic', 'attribute', 'identifier'] as const).map((k) => {
            const v = res.features[k]
            if (v == null) return null
            return (
              <div key={k} className="flex items-center gap-2">
                <span className="w-16 font-mono text-[9px] uppercase text-zinc-500">{k}</span>
                <div className="h-1.5 flex-1 overflow-hidden rounded bg-zinc-800">
                  <div className="h-full rounded" style={{ width: `${v * 100}%`, background: '#00f0ff' }} />
                </div>
                <span className="w-8 text-right font-mono text-[9px] text-zinc-400">{v.toFixed(2)}</span>
              </div>
            )
          })}
          {!res.calibrated && (
            <p className="font-mono text-[9px] text-[#f59e0b]">⚠ uncalibrated — treat as a lead, not a verdict</p>
          )}
        </div>
      )}
    </div>
  )
}
