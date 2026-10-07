import { useEffect, useMemo, useState } from 'react'
import {
  ShieldAlert, ChevronDown, ChevronRight, Layers, Sliders,
  User, Search, Zap, AlertTriangle, TrendingUp, MoonStar, Shield, EyeOff, Star,
  FileText, Upload, Loader2, Fingerprint,
} from 'lucide-react'
import {
  api, LAYER_COLOR, LAYER_LABEL, type AnomaliesResponse, type Anomaly,
  type BlindspotResponse, type EntitySummary, type EscalationResponse,
  type EvidenceResolve, type LayerName, type PersonDossier, type ResolveResponse,
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
  // Top-3 cross-layer hubs (degree × layer-breadth) — badged with a ★ so the
  // network-relay suspect is visible at a glance (PS-6 key influencers).
  const topHubs = useMemo(() => {
    const withInf = entities
      .filter((e) => (e.influence ?? 0) > 0)
      .sort((a, b) => (b.influence ?? 0) - (a.influence ?? 0))
      .slice(0, 3)
      .map((e) => e.id)
    return new Set(withInf)
  }, [entities])

  return (
    <aside className="flex h-full w-80 shrink-0 flex-col gap-4 overflow-y-auto border-r border-white/5 bg-[#0a0f1c] p-3">
      <EscalationPanel onPick={onPick} />
      <AnomalyPanel onPick={onPick} />
      {activeId && <BlindspotPanel entityId={activeId} />}
      <ResolveTester />
      <EvidenceAutoResolve />
      <PersonDossierCard />

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
            const isHub = topHubs.has(e.id)
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
                      {isHub && (
                        <Star
                          size={10}
                          fill="#fbbf24"
                          className="mr-1 inline -translate-y-px text-amber-400"
                        />
                      )}
                      {e.label}
                    </span>
                    <span className="flex items-center gap-1 font-mono text-[8px] uppercase tracking-wider text-slate-600">
                      <span>{e.type.toLowerCase()}</span>
                      {isVictim && <span className="text-purple-400"> · shielded</span>}
                      {e.repeat_offender && (
                        <span className="text-orange-400">
                          · repeat · {e.fir_count} FIRs
                        </span>
                      )}
                      {isHub && (
                        <span className="text-amber-400">· influence hub ★</span>
                      )}
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

function BlindspotPanel({ entityId }: { entityId: string }) {
  const [data, setData] = useState<BlindspotResponse | null>(null)
  const [open, setOpen] = useState(true)

  useEffect(() => {
    setData(null)
    api.blindspot(entityId).then(setData).catch(() => setData(null))
  }, [entityId])

  if (!data) return null
  const score = data.corroboration_score
  const color = score >= 75 ? '#34d399' : score >= 45 ? '#fbbf24' : '#ef4444'

  return (
    <div className="rounded-lg border border-white/5 bg-white/[0.02] p-3 backdrop-blur-md">
      <button onClick={() => setOpen(!open)}
              className="flex w-full items-center justify-between text-left">
        <div className="flex items-center gap-1.5">
          <EyeOff size={12} style={{ color }} />
          <h3 className="font-mono text-[10px] uppercase tracking-[0.25em] text-slate-400">
            Blindspots · what we don't know
          </h3>
        </div>
        {open ? <ChevronDown size={12} className="text-slate-500" /> : <ChevronRight size={12} className="text-slate-500" />}
      </button>
      {open && (
        <div className="mt-2.5">
          <div className="flex items-center gap-2">
            <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-slate-800">
              <div className="h-full rounded-full transition-all"
                   style={{ width: `${score}%`, background: color }} />
            </div>
            <span className="font-mono text-[11px] font-bold" style={{ color }}>{score}</span>
          </div>
          <p className="mt-1 font-mono text-[9px] uppercase tracking-wider" style={{ color }}>
            {data.verdict}
          </p>
          <ul className="mt-2 space-y-1">
            {data.gaps.map((g, i) => (
              <li key={i} className="flex items-start gap-1.5 text-[10px] leading-snug text-slate-400">
                <span className="mt-1 h-1 w-1 shrink-0 rounded-full" style={{ background: color }} />
                {g}
              </li>
            ))}
            {data.gaps.length === 0 && (
              <li className="text-[10px] text-slate-500">No blindspots detected — all three layers corroborated.</li>
            )}
          </ul>
          <p className="mt-2 font-mono text-[8px] text-slate-600">
            {data.stats.observed} observed · {data.stats.inferred} inferred · {data.stats.independent_sources} sources
          </p>
        </div>
      )}
    </div>
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

const SAMPLE_EVIDENCE = `Statement of complainant — Sunita Devi (W/o Ramesh), S-12 GALI, BANJARA HILLS\n
Shikayatkarta Sunita Devi ne bataya ki 12 Aug ko raat 9 baje accused Nehaa Kumaar aur Mr Mohammad Arif ne use phone par dhamkaya.\n
फोन नंबर +91 8044997278 तथा खाता AC0076617711 का उपयोग किया गया। संदिग्ध रमेश कुमार ने मोहम्मद आरिफ़ को पैसे ट्रांसफर किए।\n
Account citibank NRC-1000721; vehicle KA01MN2233 तेज़ रफ्तार से भागा।`

const DECISION_STYLE: Record<EvidenceResolve['rows'][number]['decision'], { color: string; label: string }> = {
  MATCH: { color: '#34d399', label: 'Match' },
  UNCERTAIN: { color: '#fbbf24', label: 'Review' },
  REJECT: { color: '#ef4444', label: 'Reject' },
  NEW: { color: '#60a5fa', label: 'New' },
}

function EvidenceAutoResolve() {
  const [text, setText] = useState('')
  const [pdf, setPdf] = useState<File | null>(null)
  const [res, setRes] = useState<EvidenceResolve | null>(null)
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState<string | null>(null)

  async function runText() {
    if (text.trim().length < 10) { setErr('paste the document text (min 10 chars)'); return }
    setBusy(true); setErr(null)
    try { setRes(await api.resolveEvidence(text)) }
    catch (e) { setErr(e instanceof Error ? e.message : 'evidence resolve failed') }
    finally { setBusy(false) }
  }
  async function runPdf() {
    if (!pdf) { setErr('choose a PDF first'); return }
    setBusy(true); setErr(null)
    try { setRes(await api.resolveEvidencePdf(pdf)) }
    catch (e) { setErr(e instanceof Error ? e.message : 'evidence pdf failed') }
    finally { setBusy(false) }
  }

  return (
    <div className="rounded-lg border border-violet-400/15 bg-violet-500/[0.03] p-3 backdrop-blur-md">
      <div className="mb-2.5 flex items-center gap-1.5">
        <FileText size={12} className="text-violet-400" />
        <h3 className="font-mono text-[10px] uppercase tracking-[0.25em] text-slate-400">
          Evidence · auto-resolve
        </h3>
      </div>
      <textarea
        value={text} onChange={(e) => setText(e.target.value)}
        rows={3}
        placeholder="Paste a document / FIR text — every person is resolved against the case graph automatically"
        className="mb-1.5 w-full resize-y rounded-md border border-slate-700/50 bg-slate-900/60 px-2.5 py-1.5 text-[11px] leading-snug text-slate-100 outline-none transition-colors placeholder:text-slate-600 focus:border-violet-400/40"
      />
      <div className="mb-1.5 flex items-center gap-2">
        <button
          onClick={() => { setText(SAMPLE_EVIDENCE); setErr(null) }}
          className="rounded-md border border-slate-700/50 bg-slate-900/50 px-2 py-1 font-mono text-[9px] text-slate-400 transition-colors hover:border-violet-400/40 hover:text-violet-300"
        >
          Load sample
        </button>
        <button
          onClick={runText} disabled={busy || !text.trim()}
          className="flex flex-1 items-center justify-center gap-1 rounded-md bg-violet-500/15 py-1.5 text-xs font-medium text-violet-300 transition-colors hover:bg-violet-500/25 disabled:opacity-50"
        >
          {busy ? <Loader2 size={11} className="animate-spin" /> : <Zap size={11} />}
          Resolve text
        </button>
      </div>

      <label className="mb-1 flex cursor-pointer items-center gap-1.5 rounded-md border border-dashed border-slate-700/60 bg-slate-900/40 px-2.5 py-2 transition-colors hover:border-violet-400/40">
        <Upload size={11} className="text-slate-500" />
        <span className="flex-1 truncate font-mono text-[10px] text-slate-400">
          {pdf ? pdf.name : '…or upload a PDF (extracted server-side)'}
        </span>
        <input
          type="file" accept="application/pdf,.pdf"
          onChange={(e) => setPdf(e.target.files?.[0] ?? null)}
          className="hidden"
        />
      </label>
      {pdf && (
        <button
          onClick={runPdf} disabled={busy}
          className="mb-1 flex w-full items-center justify-center gap-1 rounded-md bg-violet-500/15 py-1.5 text-xs font-medium text-violet-300 transition-colors hover:bg-violet-500/25 disabled:opacity-50"
        >
          {busy ? <Loader2 size={11} className="animate-spin" /> : <FileText size={11} />}
          Resolve PDF
        </button>
      )}

      {err && <p className="mt-2 flex items-center gap-1 text-[10px] text-red-400"><AlertTriangle size={9} /> {err}</p>}

      {res && (
        <div className="mt-3 space-y-2">
          <div className="flex items-center justify-between">
            <span className="font-mono text-[10px] text-slate-400">
              {res.count} person{res.count === 1 ? '' : 's'} · {res.candidate_count} graph candidates
            </span>
            <span className="rounded px-1.5 py-0.5 font-mono text-[9px] text-violet-300" style={{ border: '1px solid #a78bfa40', background: '#a78bfa10' }}>
              {res.engine}
            </span>
          </div>
          <ul className="space-y-1.5">
            {res.rows.map((r, i) => {
              const d = DECISION_STYLE[r.decision]
              return (
                <li key={i} className="rounded-md border border-slate-800 bg-slate-900/50 px-2 py-1.5">
                  <div className="flex items-center justify-between gap-2">
                    <span className="min-w-0 truncate font-mono text-[11px] text-slate-100" title={r.surface}>{r.surface}</span>
                    <span className="shrink-0 rounded px-1.5 py-0.5 font-mono text-[8px] uppercase"
                      style={{ color: d.color, border: `1px solid ${d.color}50`, background: `${d.color}12` }}>
                      {d.label} · {(r.confidence * 100).toFixed(0)}%
                    </span>
                  </div>
                  <div className="mt-1 flex items-center justify-between gap-2">
                    <span className="min-w-0 truncate text-[10px] text-slate-400">
                      {r.match ? `→ ${r.match.label}` : 'no graph match'}
                    </span>
                    <div className="flex items-center gap-1.5">
                      <span className="font-mono text-[8px] text-slate-600">N {r.basis.name.toFixed(2)} · P {r.basis.phonetic.toFixed(2)}</span>
                      {r.route_to_review && (
                        <span className="flex items-center gap-0.5 font-mono text-[8px] text-amber-400">
                          <Shield size={8} /> review
                        </span>
                      )}
                    </div>
                  </div>
                </li>
              )
            })}
          </ul>
          <p className="flex items-start gap-1 font-mono text-[8px] leading-relaxed text-slate-500">
            <AlertTriangle size={8} className="mt-0.5 shrink-0 text-amber-400/70" />
            {res.disclosure}
          </p>
        </div>
      )}
    </div>
  )
}

function PersonDossierCard() {
  const [name, setName] = useState('')
  const [res, setRes] = useState<PersonDossier | null>(null)
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState<string | null>(null)
  const [open, setOpen] = useState(true)

  async function run() {
    if (name.trim().length < 2) { setErr('enter a name (any script)'); return }
    setBusy(true); setErr(null)
    try { setRes(await api.resolvePerson(name)) }
    catch (e) { setErr(e instanceof Error ? e.message : 'dossier failed') }
    finally { setBusy(false) }
  }

  return (
    <div className="rounded-lg border border-cyan-400/15 bg-cyan-500/[0.03] p-3 backdrop-blur-md">
      <button onClick={() => setOpen((o) => !o)}
              className="mb-2 flex w-full items-center gap-1.5">
        <Fingerprint size={12} className="text-cyan-400" />
        <h3 className="font-mono text-[10px] uppercase tracking-[0.25em] text-slate-400">
          Person dossier
        </h3>
        {open ? <ChevronDown size={10} className="ml-auto text-slate-600" />
              : <ChevronRight size={10} className="ml-auto text-slate-600" />}
      </button>
      {open && (
        <>
          <div className="flex gap-1.5">
            <input
              value={name}
              onChange={(e) => setName(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && run()}
              placeholder="Mohammad Arif / मोहम्मद आरिफ"
              className="min-w-0 flex-1 rounded border border-cyan-400/20 bg-slate-900/60 px-2 py-1 text-[10px] text-slate-200 outline-none focus:border-cyan-400/40"
            />
            <button onClick={run} disabled={busy}
                    className="flex items-center gap-1 rounded bg-cyan-500/10 px-2 py-1 font-mono text-[9px] text-cyan-300 transition-colors hover:bg-cyan-500/20 disabled:opacity-40">
              {busy ? <Loader2 size={9} className="animate-spin" /> : <Zap size={9} />}
              dossier
            </button>
          </div>
          {err && (
            <p className="mt-1.5 flex items-center gap-1 font-mono text-[8px] text-red-400">
              <AlertTriangle size={8} /> {err}
            </p>
          )}
          {res && res.found && (
            <div className="mt-2 space-y-2">
              <div className="flex items-center justify-between gap-2">
                <span className="truncate font-mono text-[11px] font-semibold text-slate-200">
                  {res.name}
                </span>
                <span className="shrink-0 font-mono text-[8px] text-cyan-400">
                  match {(res.match_confidence ?? 0).toFixed(3)}
                </span>
              </div>
              {res.aliases && res.aliases.length > 1 && (
                <div className="flex flex-wrap gap-1">
                  {res.aliases.map((a) => (
                    <span key={a} className="rounded bg-slate-800/70 px-1 py-0.5 font-mono text-[8px] text-slate-400">
                      {a}
                    </span>
                  ))}
                </div>
              )}
              <div className="flex flex-wrap gap-1">
                {res.roles?.map((r) => (
                  <span key={r} className="flex items-center gap-0.5 rounded bg-cyan-500/10 px-1 py-0.5 font-mono text-[8px] text-cyan-300">
                    <Shield size={7} /> {r}
                  </span>
                ))}
                {res.victim_shielded && (
                  <span className="flex items-center gap-0.5 rounded bg-purple-500/10 px-1 py-0.5 font-mono text-[8px] text-purple-300">
                    <EyeOff size={7} /> victim-shielded
                  </span>
                )}
              </div>
              {res.firs && res.firs.length > 0 && (
                <ul className="space-y-1">
                  {res.firs.slice(0, 5).map((f) => (
                    <li key={f.record_id}
                        className="rounded border border-white/5 bg-white/[0.02] px-2 py-1.5">
                      <div className="flex items-center justify-between gap-2">
                        <span className="font-mono text-[9px] text-slate-300">{f.record_id}</span>
                        <span className="font-mono text-[8px] text-amber-400/90">IPC {f.section?.join(', ')}</span>
                      </div>
                      <div className="mt-0.5 font-mono text-[8px] text-slate-500">
                        {f.district} · {f.police_station ?? '—'} · {f.role}
                      </div>
                    </li>
                  ))}
                </ul>
              )}
              {res.identifiers && (
                <div className="grid grid-cols-3 gap-1.5">
                  <div>
                    <div className="font-mono text-[7px] uppercase text-slate-600">phones</div>
                    <div className="truncate font-mono text-[9px] text-slate-400">
                      {res.identifiers.phones.slice(0, 3).join(', ') || '—'}
                    </div>
                  </div>
                  <div>
                    <div className="font-mono text-[7px] uppercase text-slate-600">accounts</div>
                    <div className="truncate font-mono text-[9px] text-slate-400">
                      {res.identifiers.accounts.slice(0, 3).join(', ') || '—'}
                    </div>
                  </div>
                  <div>
                    <div className="font-mono text-[7px] uppercase text-slate-600">vehicles</div>
                    <div className="truncate font-mono text-[9px] text-slate-400">
                      {res.identifiers.vehicles.slice(0, 3).join(', ') || '—'}
                    </div>
                  </div>
                </div>
              )}
              <p className="flex items-start gap-1 font-mono text-[8px] leading-relaxed text-slate-500">
                <AlertTriangle size={8} className="mt-0.5 shrink-0 text-cyan-400/70" />
                {res.disclosure}
              </p>
            </div>
          )}
          {res && !res.found && (
            <p className="mt-1.5 flex items-start gap-1 font-mono text-[8px] leading-relaxed text-slate-500">
              <AlertTriangle size={8} className="mt-0.5 shrink-0 text-amber-400/70" />
              {res.disclosure}
            </p>
          )}
        </>
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

// Stalking-escalation leads (GET /api/escalation) — the Women Safety centerpiece.
// A rising caller→receiver trajectory with night calls, BEFORE the next FIR. The
// sparkline makes the trajectory visible at a glance; victim-linked rows flag
// CRITICAL while keeping the protected party shielded (phone-level display only).
function EscalationPanel({ onPick }: { onPick: (id: string) => void }) {
  const [data, setData] = useState<EscalationResponse | null>(null)
  const [open, setOpen] = useState(true)

  useEffect(() => {
    api.escalation().then(setData).catch(() => setData(null))
  }, [])

  if (!data || data.alerts.length === 0) return null

  const sevColor = { CRITICAL: '#ef4444', HIGH: '#f59e0b', MEDIUM: '#38bdf8' } as const

  return (
    <div className="rounded-lg border border-red-500/30 bg-red-500/[0.05] p-3 backdrop-blur-md">
      <button
        onClick={() => setOpen(!open)}
        className="mb-1 flex w-full items-center justify-between"
      >
        <div className="flex items-center gap-1.5">
          <TrendingUp size={12} className="text-red-400" />
          <h3 className="font-mono text-[10px] uppercase tracking-[0.25em] text-red-400">
            Escalating contact · {data.total}
          </h3>
        </div>
        {open ? <ChevronDown size={12} className="text-slate-500" /> : <ChevronRight size={12} className="text-slate-500" />}
      </button>
      {open && (
        <>
          <ul className="space-y-2">
            {data.alerts.slice(0, 5).map((a) => {
              const c = sevColor[a.severity]
              const max = Math.max(...a.weekly_counts, 1)
              return (
                <li key={a.id}>
                  <button
                    onClick={() => onPick(a.caller)}
                    title={a.reason}
                    className="w-full rounded-md border border-transparent px-2 py-2 text-left transition-all duration-150 hover:border-slate-700/50 hover:bg-slate-800/40"
                  >
                    <div className="flex items-center justify-between gap-2">
                      <span className="min-w-0 truncate font-mono text-[10px] text-slate-200">
                        {a.caller_label}
                      </span>
                      <span
                        className="flex shrink-0 items-center gap-1 rounded px-1 py-0.5 font-mono text-[8px] uppercase"
                        style={{ color: c, border: `1px solid ${c}40`, background: `${c}10` }}
                      >
                        {a.victim_linked && <Shield size={8} />}
                        {a.severity}
                      </span>
                    </div>
                    {/* trajectory sparkline — the escalation is visible */}
                    <div className="mt-1.5 flex items-end gap-1">
                      {a.weekly_counts.map((n, i) => (
                        <div
                          key={i}
                          className="w-4 rounded-sm"
                          style={{
                            height: `${4 + (n / max) * 14}px`,
                            background: i === a.weekly_counts.length - 1 ? c : `${c}55`,
                          }}
                          title={`week ${i + 1}: ${n} calls`}
                        />
                      ))}
                      <span className="ml-1 font-mono text-[8px] text-slate-500">
                        {a.weekly_counts.join(' → ')} calls/wk
                      </span>
                      {a.night_calls > 0 && (
                        <span className="ml-auto flex items-center gap-0.5 font-mono text-[8px] text-indigo-300">
                          <MoonStar size={8} /> {a.night_calls} night
                        </span>
                      )}
                    </div>
                    {a.victim_linked && (
                      <p className="mt-1 font-mono text-[8px] text-purple-300/80">
                        receiver is a complainant on record · shielded
                      </p>
                    )}
                  </button>
                </li>
              )
            })}
          </ul>
          <p className="mt-2 border-t border-white/5 pt-1.5 font-mono text-[8px] leading-relaxed text-slate-600">
            trajectory leads — intervene before the next FIR · not a determination of guilt
          </p>
        </>
      )}
    </div>
  )
}
