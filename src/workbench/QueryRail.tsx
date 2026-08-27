import { useEffect, useState } from 'react'
import {
  ShieldAlert, ChevronDown, ChevronRight, Layers, Sliders,
  User, Search, Zap, AlertTriangle,
} from 'lucide-react'
import {
  api, LAYER_COLOR, LAYER_LABEL, type AnomaliesResponse, type Anomaly,
  type EntitySummary, type LayerName, type ResolveResponse,
} from '@/lib/api'

const ALL_LAYERS: LayerName[] = ['communication', 'financial', 'spatial']

const KIND_STYLE: Record<Anomaly['kind'], { color: string; label: string }> = {
  CIRCULAR_FLOW: { color: '#ef4444', label: 'Money cycle' },
  COMM_BURST: { color: '#fbbf24', label: 'Call burst' },
  TRANS_BURST: { color: '#fbbf24', label: 'Transfer burst' },
}

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
    <aside className="flex h-full w-80 shrink-0 flex-col gap-4 overflow-y-auto border-r border-white/5 bg-[#0a0f1c] p-3">
      <AnomalyPanel onPick={onPick} />
      <ResolveTester />

      {/* Entities by Risk */}
      <div className="rounded-lg border border-white/5 bg-white/[0.02] p-3 backdrop-blur-md">
        <div className="mb-2.5 flex items-center gap-1.5">
          <User size={12} className="text-cyan-400" />
          <h3 className="font-mono text-[10px] uppercase tracking-[0.25em] text-slate-400">
            Entities · by risk
          </h3>
        </div>
        <ul className="space-y-1">
          {entities.map((e) => {
            const riskPct = e.risk != null ? Math.round(e.risk * 100) : null
            const isActive = e.id === activeId
            const isVictim = (e.meta?.role as string) === 'victim'
            return (
              <li key={e.id}>
                <button
                  onClick={() => onPick(e.id)}
                  className={[
                    'group flex w-full items-center gap-2.5 rounded-md border px-2.5 py-2 text-left transition-all duration-150',
                    isActive
                      ? 'border-cyan-400/40 bg-cyan-400/10'
                      : 'border-transparent hover:border-slate-700/50 hover:bg-slate-800/40',
                  ].join(' ')}
                >
                  {/* Name */}
                  <div className="min-w-0 flex-1">
                    <span
                      className={`block truncate text-xs font-medium ${
                        isActive ? 'text-cyan-300' : 'text-slate-200'
                      }`}
                      title={e.label}
                    >
                      {e.label}
                    </span>
                    <span className="font-mono text-[8px] uppercase tracking-wider text-slate-600">
                      {e.type.toLowerCase()}
                      {isVictim && <span className="text-purple-400"> · shielded</span>}
                    </span>
                  </div>

                  {/* Risk score + mini bar */}
                  {riskPct != null && (
                    <div className="flex shrink-0 items-center gap-1.5">
                      <div className="h-1 w-12 overflow-hidden rounded-full bg-slate-800">
                        <div
                          className="h-full rounded-full transition-all duration-300"
                          style={{
                            width: `${riskPct}%`,
                            background: riskPct > 60
                              ? 'linear-gradient(90deg, #ef4444, #dc2626)'
                              : riskPct > 30
                                ? 'linear-gradient(90deg, #fbbf24, #f59e0b)'
                                : 'linear-gradient(90deg, #38bdf8, #0ea5e9)',
                          }}
                        />
                      </div>
                      <span
                        className={`w-7 text-right font-mono text-[9px] ${
                          riskPct > 60 ? 'text-red-400' : riskPct > 30 ? 'text-amber-400' : 'text-slate-400'
                        }`}
                      >
                        {riskPct}
                      </span>
                    </div>
                  )}
                </button>
              </li>
            )
          })}
          {entities.length === 0 && (
            <li className="flex items-center gap-1.5 px-2 py-2 font-mono text-[10px] text-slate-600">
              <Search size={10} /> loading entities…
            </li>
          )}
        </ul>
      </div>

      {/* Layer filters */}
      <div className="rounded-lg border border-white/5 bg-white/[0.02] p-3 backdrop-blur-md">
        <div className="mb-2.5 flex items-center gap-1.5">
          <Layers size={12} className="text-cyan-400" />
          <h3 className="font-mono text-[10px] uppercase tracking-[0.25em] text-slate-400">Layers</h3>
        </div>
        <div className="space-y-2">
          {ALL_LAYERS.map((l) => (
            <label
              key={l}
              className="flex cursor-pointer items-center gap-2 text-xs text-slate-300 transition-colors hover:text-slate-100"
            >
              <input
                type="checkbox"
                checked={layers.includes(l)}
                onChange={() =>
                  setLayers(layers.includes(l) ? layers.filter((x) => x !== l) : [...layers, l])
                }
                className="h-3 w-3 rounded accent-cyan-400"
              />
              <span
                className="h-2 w-2 rounded-full"
                style={{ background: LAYER_COLOR[l], boxShadow: `0 0 4px ${LAYER_COLOR[l]}80` }}
              />
              {LAYER_LABEL[l]}
            </label>
          ))}
        </div>
      </div>

      {/* Confidence floor */}
      <div className="rounded-lg border border-white/5 bg-white/[0.02] p-3 backdrop-blur-md">
        <div className="mb-2.5 flex items-center gap-1.5">
          <Sliders size={12} className="text-cyan-400" />
          <span className="font-mono text-[10px] uppercase tracking-[0.25em] text-slate-400">
            Confidence floor · {minConf.toFixed(2)}
          </span>
        </div>
        <input
          type="range" min={0} max={1} step={0.05} value={minConf}
          onChange={(e) => setMinConf(Number(e.target.value))}
          className="w-full accent-cyan-400"
        />
        <label className="mt-2.5 flex cursor-pointer items-center gap-2 text-xs text-slate-300">
          <input
            type="checkbox" checked={showInferred}
            onChange={(e) => setShowInferred(e.target.checked)}
            className="h-3 w-3 rounded accent-slate-500"
          />
          Show inferred edges <span className="text-slate-600">(dashed)</span>
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

  const color = res?.decision === 'MATCH' ? '#34d399' : res?.decision === 'UNCERTAIN' ? '#fbbf24' : '#ef4444'

  return (
    <div className="rounded-lg border border-white/5 bg-white/[0.02] p-3 backdrop-blur-md">
      <div className="mb-2.5 flex items-center gap-1.5">
        <Zap size={12} className="text-cyan-400" />
        <h3 className="font-mono text-[10px] uppercase tracking-[0.25em] text-slate-400">
          Identity Resolution
        </h3>
      </div>
      <input
        value={a} onChange={(e) => setA(e.target.value)}
        className="mb-1.5 w-full rounded-md border border-slate-700/50 bg-slate-900/60 px-2.5 py-1.5 text-xs text-slate-100 outline-none transition-colors placeholder:text-slate-600 focus:border-cyan-400/40"
        placeholder="Name A (English)"
      />
      <input
        value={b} onChange={(e) => setB(e.target.value)}
        className="mb-2.5 w-full rounded-md border border-slate-700/50 bg-slate-900/60 px-2.5 py-1.5 text-xs text-slate-100 outline-none transition-colors placeholder:text-slate-600 focus:border-cyan-400/40"
        placeholder="Name B (Hindi/Devanagari)"
      />
      <button
        onClick={run} disabled={busy}
        className="w-full rounded-md bg-cyan-500/15 py-1.5 text-xs font-medium text-cyan-400 transition-colors hover:bg-cyan-500/25 disabled:opacity-50"
      >
        {busy ? 'Resolving…' : 'Resolve'}
      </button>
      {err && <p className="mt-2 flex items-center gap-1 text-[10px] text-red-400"><AlertTriangle size={9} /> {err}</p>}
      {res && (
        <div className="mt-3 space-y-2">
          <div className="flex items-center justify-between">
            <span className="font-mono text-sm font-bold" style={{ color }}>{res.decision}</span>
            <span className="font-mono text-xs text-slate-300">{(res.confidence * 100).toFixed(0)}%</span>
          </div>
          {(['name', 'phonetic', 'attribute', 'identifier'] as const).map((k) => {
            const v = res.features[k]
            if (v == null) return null
            return (
              <div key={k} className="flex items-center gap-2">
                <span className="w-16 font-mono text-[9px] uppercase text-slate-500">{k}</span>
                <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-slate-800">
                  <div
                    className="h-full rounded-full bg-gradient-to-r from-cyan-500 to-cyan-400 transition-all duration-300"
                    style={{ width: `${v * 100}%` }}
                  />
                </div>
                <span className="w-8 text-right font-mono text-[9px] text-slate-400">{v.toFixed(2)}</span>
              </div>
            )
          })}
          {!res.calibrated && (
            <p className="flex items-center gap-1 font-mono text-[9px] text-amber-400">
              <AlertTriangle size={9} /> uncalibrated — treat as a lead, not a verdict
            </p>
          )}
        </div>
      )}
    </div>
  )
}

function AnomalyPanel({ onPick }: { onPick: (id: string) => void }) {
  const [data, setData] = useState<AnomaliesResponse | null>(null)
  const [open, setOpen] = useState(true)

  useEffect(() => {
    api.anomalies().then(setData).catch(() => setData(null))
  }, [])

  if (!data || data.anomalies.length === 0) return null
  const evalPct = (v: number | null | undefined) =>
    v != null ? `${(v * 100).toFixed(0)}%` : '—'

  return (
    <div className="rounded-lg border border-red-500/20 bg-red-500/[0.04] p-3 backdrop-blur-md">
      <button
        onClick={() => setOpen(!open)}
        className="mb-1 flex w-full items-center justify-between"
      >
        <div className="flex items-center gap-1.5">
          <ShieldAlert size={12} className="text-red-400" />
          <h3 className="font-mono text-[10px] uppercase tracking-[0.25em] text-red-400">
            Suspicious activity · {data.total}
          </h3>
        </div>
        {open ? <ChevronDown size={12} className="text-slate-500" /> : <ChevronRight size={12} className="text-slate-500" />}
      </button>
      {open && (
        <>
          <ul className="space-y-1.5">
            {data.anomalies.slice(0, 6).map((a) => {
              const style = KIND_STYLE[a.kind]
              return (
                <li key={a.id}>
                  <button
                    onClick={() => onPick(a.entity_id)}
                    title={a.reason}
                    className="w-full rounded-md border border-transparent px-2 py-1.5 text-left transition-all duration-150 hover:border-slate-700/50 hover:bg-slate-800/40"
                  >
                    <div className="flex items-center justify-between gap-2">
                      <span className="min-w-0 truncate text-xs text-slate-200">{a.label}</span>
                      <span
                        className="shrink-0 rounded px-1 py-0.5 font-mono text-[8px] uppercase"
                        style={{ color: style.color, border: `1px solid ${style.color}40`, background: `${style.color}10` }}
                      >
                        {style.label}
                      </span>
                    </div>
                    <div className="mt-1 flex items-center gap-2">
                      <div className="h-1 flex-1 overflow-hidden rounded-full bg-slate-800">
                        <div
                          className="h-full rounded-full transition-all duration-300"
                          style={{
                            width: `${a.severity * 100}%`,
                            background: `linear-gradient(90deg, ${style.color}80, ${style.color})`,
                          }}
                        />
                      </div>
                      <span className="font-mono text-[8px] text-slate-500">
                        {a.z_score != null ? `z ${a.z_score.toFixed(1)}` : 'cycle'}
                      </span>
                    </div>
                  </button>
                </li>
              )
            })}
          </ul>
          {data.evaluation && (
            <p className="mt-2 border-t border-white/5 pt-1.5 font-mono text-[8px] leading-relaxed text-slate-600">
              benchmark self-test · cycles P {evalPct(data.evaluation.CIRCULAR_FLOW?.precision)} / R {evalPct(data.evaluation.CIRCULAR_FLOW?.recall)}
              · bursts P {evalPct(data.evaluation.COMM_BURST?.precision)} / R {evalPct(data.evaluation.COMM_BURST?.recall)}
              <br />analytical lead — not a determination of criminality
            </p>
          )}
        </>
      )}
    </div>
  )
}
