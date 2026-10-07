// File New FIR — the demo's opening moment.
// An investigator pastes a raw complaint (Hindi / English / Hinglish); the system
// extracts entities with deterministic regex NER, highlights them inline in the
// pasted text, fires cross-district collision alerts against the existing case
// graph, and merges the FIR into the live graph. Zero LLM — every highlight is
// auditable against the source text.
import { useMemo, useRef, useState } from 'react'
import {
  FilePlus2, Loader2, AlertTriangle, Shield, ArrowRight,
  Phone, Building2, Car, User, Scale, X, Network, BadgeCheck, BadgeX,
  MapPin, Landmark, Mic, Square, Volume2,
} from 'lucide-react'
import {
  api, ApiError, type ExtractedEntityOut, type IngestResponse,
} from '@/lib/api'
import { dictate, speak, speechAvailable, stopSpeaking, VOICE_MODE } from '@/lib/voice'

const DEFAULT_COMPLAINANT = 'Sunita Devi'
const DEFAULT_ACCUSED = 'Ramesh Kumar'

const narrativeDate = () => {
  const d = new Date()
  return `${String(d.getDate()).padStart(2, '0')}/${String(d.getMonth() + 1).padStart(2, '0')}/${d.getFullYear()}`
}

const todayISO = () => new Date().toLocaleDateString('en-CA')

const SAMPLE = `दिनांक ${narrativeDate()} को शिकायतकर्ता ${DEFAULT_COMPLAINANT} ने बताया कि ${DEFAULT_ACCUSED} ने उसे +91-8044997278 से धमकी भरा कॉल किया। संदिग्ध का वाहन UP78 GC 4978 देखा गया। पैसे खाता AC7234309805 में ट्रांसफर हुए। धारा 354D लगाई गई। संदिग्ध का संबंध Desi Traders Pvt Ltd कंपनी से बताया गया और वह करोल बाग मार्केट में रुका हुआ देखा गया।`

const KIND_STYLE: Record<string, { color: string; bg: string; label: string }> = {
  PERSON: { color: '#7dd3fc', bg: 'rgba(125,211,252,0.12)', label: 'Person' },
  PHONE: { color: '#22d3ee', bg: 'rgba(34,211,238,0.12)', label: 'Phone' },
  ACCOUNT: { color: '#34d399', bg: 'rgba(52,211,153,0.12)', label: 'Account' },
  VEHICLE: { color: '#c084fc', bg: 'rgba(192,132,252,0.12)', label: 'Vehicle' },
  IPC: { color: '#fbbf24', bg: 'rgba(251,191,36,0.12)', label: 'IPC' },
  ORGANIZATION: { color: '#f472b6', bg: 'rgba(244,114,182,0.12)', label: 'Organization' },
  LOCATION: { color: '#4ade80', bg: 'rgba(74,222,128,0.12)', label: 'Location' },
}

const KIND_ICON: Record<string, typeof Phone> = {
  PERSON: User, PHONE: Phone, ACCOUNT: Building2, VEHICLE: Car, IPC: Scale,
  ORGANIZATION: Landmark, LOCATION: MapPin,
}

// Render the narrative with entity spans highlighted — the "forensic" moment.
function HighlightedNarrative({ text, entities }: { text: string; entities: ExtractedEntityOut[] }) {
  const parts = useMemo(() => {
    const spans = entities
      .filter((e) => e.span && e.span[1] > e.span[0])
      .sort((a, b) => a.span[0] - b.span[0])
    const out: Array<{ text: string; ent: ExtractedEntityOut | null }> = []
    let cur = 0
    for (const e of spans) {
      if (e.span[0] < cur) continue                    // overlapping span — skip
      if (e.span[0] > cur) out.push({ text: text.slice(cur, e.span[0]), ent: null })
      out.push({ text: text.slice(e.span[0], e.span[1]), ent: e })
      cur = e.span[1]
    }
    if (cur < text.length) out.push({ text: text.slice(cur), ent: null })
    return out
  }, [text, entities])

  return (
    <p className="text-[13px] leading-7 text-slate-300">
      {parts.map((p, i) => {
        if (!p.ent) return <span key={i}>{p.text}</span>
        const st = KIND_STYLE[p.ent.kind] ?? KIND_STYLE.PERSON
        return (
          <mark
            key={i}
            className="rounded px-1 py-0.5 font-medium"
            style={{ background: st.bg, color: st.color, boxShadow: `inset 0 -1px 0 ${st.color}55` }}
            title={`${st.label} · ${p.ent.normalized}`}
          >
            {p.text}
          </mark>
        )
      })}
    </p>
  )
}

export default function FileFirPanel({
  onClose, onIngested,
}: {
  onClose: () => void
  onIngested: (res: IngestResponse) => void
}) {
  const [narrative, setNarrative] = useState('')
  const [district, setDistrict] = useState('Delhi')
  const [station, setStation] = useState('PS Karol Bagh')
  const [date, setDate] = useState(todayISO())
  const [complainant, setComplainant] = useState(DEFAULT_COMPLAINANT)
  const [accused, setAccused] = useState(DEFAULT_ACCUSED)
  const [busy, setBusy] = useState(false)
  const [res, setRes] = useState<IngestResponse | null>(null)
  const [err, setErr] = useState<string | null>(null)
  const [dictating, setDictating] = useState(false)
  const [listening, setListening] = useState(false)
  const [micNote, setMicNote] = useState<string | null>(null)
  const stopRef = useRef<() => void>(() => {})

  // Field-driven narrative: swap the sample-injected names so the highlighted
  // entities ALWAYS match what the investigator typed, not what the sample said.
  const setComplainantAndSync = (v: string) => {
    setComplainant(v)
    const name = v.trim() || DEFAULT_COMPLAINANT
    setNarrative((t) => t.split(DEFAULT_COMPLAINANT).join(name))
  }
  const setAccusedAndSync = (v: string) => {
    setAccused(v)
    const name = v.trim() || DEFAULT_ACCUSED
    setNarrative((t) => t.split(DEFAULT_ACCUSED).join(name))
  }
  const loadSample = () => {
    setNarrative(SAMPLE)
    setComplainant(DEFAULT_COMPLAINANT)
    setAccused(DEFAULT_ACCUSED)
    setDate(todayISO())
  }

  // Bhashini voice channel — on-device Hindi dictation (vetted before ingest).
  const startDictation = () => {
    if (dictating) return
    if (!speechAvailable()) {
      setMicNote('Speech not available in this browser')
      return
    }
    const base = narrative.replace(/\s+$/, '')
    setDictating(true)
    setMicNote('सुन रहा हूँ… बोलिए (dictating · hi-IN)')
    stopRef.current = dictate(
      (t, done) => {
        if (done) { setDictating(false); setMicNote('transcript vetted above — ready to ingest') }
        setNarrative(base ? `${base} ${t.trim()}`.trim() : t.trim())
      },
      () => { setDictating(false); setMicNote('dictation stopped') },
    )
  }
  const stopDictation = () => { stopRef.current(); setDictating(false); setMicNote('dictation stopped') }

  const toggleListen = () => {
    if (listening) { stopSpeaking(); setListening(false); return }
    speak(narrative.trim())
    setListening(true)
    setTimeout(() => setListening(false), Math.max(2000, narrative.length * 28))
  }

  async function submit() {
    setBusy(true); setErr(null)
    try {
      const out = await api.ingestFir({
        narrative: narrative.trim(),
        district: district.trim(),
        police_station: station.trim(),
        date,
        complainant_name: complainant.trim() || undefined,
        accused_names: accused.split(',').map((s) => s.trim()).filter(Boolean),
      })
      setRes(out)
      onIngested(out)
    } catch (e) {
      setErr(e instanceof ApiError ? `Ingest failed (${e.status})` : 'Ingest failed — backend live?')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="absolute inset-0 z-50 flex items-center justify-center bg-black/60 p-4 backdrop-blur-sm"
         onClick={onClose}>
      <div
        className="flex max-h-[88vh] w-full max-w-2xl flex-col overflow-hidden rounded-xl border border-white/10 bg-[#0a0f1c] shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        {/* header */}
        <div className="flex items-center justify-between border-b border-white/5 px-5 py-3.5">
          <div className="flex items-center gap-2">
            <FilePlus2 size={15} className="text-cyan-400" />
            <h2 className="font-mono text-[11px] uppercase tracking-[0.25em] text-slate-300">
              File new FIR
            </h2>
          </div>
          <button onClick={onClose} className="text-slate-500 transition-colors hover:text-slate-200">
            <X size={16} />
          </button>
        </div>

        <div className="min-h-0 flex-1 space-y-4 overflow-y-auto p-5">
          {!res ? (
            <>
              <div className="grid grid-cols-2 gap-3">
                <label className="block">
                  <span className="mb-1 block font-mono text-[9px] uppercase tracking-wider text-slate-500">District</span>
                  <input value={district} onChange={(e) => setDistrict(e.target.value)}
                         className="w-full rounded-md border border-slate-700/50 bg-slate-900/60 px-2.5 py-1.5 text-xs text-slate-100 outline-none focus:border-cyan-400/40" />
                </label>
                <label className="block">
                  <span className="mb-1 block font-mono text-[9px] uppercase tracking-wider text-slate-500">Police station</span>
                  <input value={station} onChange={(e) => setStation(e.target.value)}
                         className="w-full rounded-md border border-slate-700/50 bg-slate-900/60 px-2.5 py-1.5 text-xs text-slate-100 outline-none focus:border-cyan-400/40" />
                </label>
                <label className="block">
                  <span className="mb-1 block font-mono text-[9px] uppercase tracking-wider text-slate-500">FIR date</span>
                  <input type="date" value={date} onChange={(e) => setDate(e.target.value)}
                         className="w-full rounded-md border border-slate-700/50 bg-slate-900/60 px-2.5 py-1.5 text-xs text-slate-100 outline-none focus:border-cyan-400/40 [color-scheme:dark]" />
                </label>
                <label className="block">
                  <span className="mb-1 flex items-center gap-1 font-mono text-[9px] uppercase tracking-wider text-slate-500">
                    <Shield size={9} className="text-purple-400" /> Complainant (shielded)
                  </span>
<input value={complainant} onChange={(e) => setComplainantAndSync(e.target.value)}
                       className="w-full rounded-md border border-purple-400/30 bg-slate-900/60 px-2.5 py-1.5 text-xs text-slate-100 outline-none focus:border-purple-400/50" />
                </label>
                <label className="block">
                  <span className="mb-1 block font-mono text-[9px] uppercase tracking-wider text-slate-500">Accused (comma-sep)</span>
                  <input value={accused} onChange={(e) => setAccusedAndSync(e.target.value)}
                         className="w-full rounded-md border border-slate-700/50 bg-slate-900/60 px-2.5 py-1.5 text-xs text-slate-100 outline-none focus:border-cyan-400/40" />
                </label>
              </div>

              <label className="block">
                <span className="mb-1 flex items-center justify-between font-mono text-[9px] uppercase tracking-wider text-slate-500">
                  <span>FIR narrative — Hindi / English / Hinglish</span>
                  <span className="flex items-center gap-2">
                    <span className="hidden text-[8px] uppercase tracking-wider text-slate-600 sm:inline">
                      भाषिणी · on-device · {VOICE_MODE}
                    </span>
                    <button onClick={() => (dictating ? stopDictation() : startDictation())}
                            title="Dictate in Hindi (on-device STT — Nothing leaves the box)"
                            className={`flex items-center gap-1 rounded px-1.5 py-0.5 transition-colors ${
                              dictating ? 'bg-red-500/15 text-red-400' : 'text-cyan-500 hover:bg-cyan-500/10'}`}>
                      {dictating ? <Square size={11} /> : <Mic size={11} />}
                      {dictating ? 'stop' : 'dictate'}
                    </button>
                    <button onClick={toggleListen}
                            title="Listen to the narrative (on-device Hindi TTS)"
                            className={`flex items-center gap-1 rounded px-1.5 py-0.5 transition-colors ${
                              listening ? 'bg-emerald-500/15 text-emerald-400' : 'text-cyan-500 hover:bg-cyan-500/10'}`}>
                      <Volume2 size={11} /> listen
                    </button>
                    <button onClick={loadSample}
                            className="text-cyan-500 transition-colors hover:text-cyan-300">
                      load sample
                    </button>
                  </span>
                </span>
                {micNote && (
                  <p className="mb-1 flex items-center gap-1.5 font-mono text-[9px] text-amber-400/90">
                    <Mic size={9} /> {micNote}
                  </p>
                )}
                <textarea
                  value={narrative}
                  onChange={(e) => setNarrative(e.target.value)}
                  rows={6}
                  placeholder="FIR का मूल पाठ यहाँ paste करें…"
                  className="w-full resize-y rounded-md border border-slate-700/50 bg-slate-900/60 px-3 py-2 font-mono text-xs leading-relaxed text-slate-100 outline-none placeholder:text-slate-600 focus:border-cyan-400/40"
                />
              </label>

              {err && (
                <p className="flex items-center gap-1.5 font-mono text-[10px] text-red-400">
                  <AlertTriangle size={11} /> {err}
                </p>
              )}

              <button
                onClick={submit}
                disabled={busy || narrative.trim().length < 20}
                className="flex w-full items-center justify-center gap-2 rounded-lg bg-cyan-500/15 py-2.5 text-xs font-semibold text-cyan-400 transition-colors hover:bg-cyan-500/25 disabled:opacity-40"
              >
                {busy ? <Loader2 size={13} className="animate-spin" /> : <ArrowRight size={13} />}
                {busy ? 'Extracting & linking…' : 'Ingest into case graph'}
              </button>
            </>
          ) : (
            <>
              {/* result: highlighted narrative */}
              <div className="rounded-lg border border-white/5 bg-white/[0.02] p-3.5">
                <div className="mb-2 flex items-center justify-between">
                  <span className="font-mono text-[9px] uppercase tracking-wider text-slate-500">
                    {res.record_id} · entities highlighted in source
                  </span>
                  <span className="font-mono text-[9px] text-emerald-400">
                    ✓ merged · {res.graph_stats.nodes} nodes / {res.graph_stats.edges} edges
                  </span>
                </div>
                <HighlightedNarrative text={narrative} entities={res.entities} />
                <div className="mt-3 flex flex-wrap gap-1.5">
                  {res.entities.map((e, i) => {
                    const st = KIND_STYLE[e.kind] ?? KIND_STYLE.PERSON
                    const Icon = KIND_ICON[e.kind] ?? User
                    return (
                      <span key={i}
                            className="inline-flex items-center gap-1 rounded px-1.5 py-0.5 font-mono text-[9px]"
                            style={{ color: st.color, background: st.bg, border: `1px solid ${st.color}30` }}>
                        <Icon size={9} /> {e.normalized}
                      </span>
                    )
                  })}
                </div>
              </div>

              {/* cross-case collision alerts */}
              {res.cross_case_links.length > 0 ? (
                <div className="space-y-2">
                  <h3 className="flex items-center gap-1.5 font-mono text-[10px] uppercase tracking-[0.25em] text-red-400">
                    <AlertTriangle size={12} /> Cross-case linkage · {res.cross_case_links.length}
                  </h3>
                  {res.cross_case_links.map((l, i) => (
                    <div key={i} className="rounded-lg border border-red-500/25 bg-red-500/[0.05] p-3">
                      <p className="text-xs leading-snug text-slate-200">{l.alert}</p>
                      <div className="mt-1.5 flex flex-wrap gap-1">
                        {l.linked_records.slice(0, 4).map((r) => (
                          <span key={r.record_id}
                                className="rounded border border-slate-700/60 bg-slate-900/60 px-1.5 py-0.5 font-mono text-[8px] text-slate-400">
                            {r.source} · {r.record_id} · {r.district}
                          </span>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="rounded-lg border border-slate-700/50 bg-slate-900/40 p-3 font-mono text-[10px] text-slate-500">
                  No cross-case collisions — every extracted identifier is new to the case graph.
                </p>
              )}

              {/* mesh receipts — the UPI moment: signed answers from peer vaults */}
              {res.mesh && (
                <div className="space-y-2">
                  <h3 className="flex items-center gap-1.5 font-mono text-[10px] uppercase tracking-[0.25em] text-cyan-400">
                    <Network size={12} /> District vault mesh · {res.mesh.request_id}
                  </h3>
                  <p className="font-mono text-[9px] leading-snug text-slate-500">
                    Query travelled, data didn't — each vault signed its answer.
                    {res.mesh.all_verified ? ' All receipts verified ✓' : ''}
                  </p>
                  <div className="grid grid-cols-1 gap-1.5 sm:grid-cols-2">
                    {res.mesh.receipts.map((r) => (
                      <div key={r.responder_vault}
                           className="flex items-start justify-between gap-2 rounded-lg border border-cyan-400/20 bg-cyan-400/[0.04] p-2.5">
                        <div className="min-w-0">
                          <p className="font-mono text-[10px] font-semibold uppercase text-slate-200">
                            {r.responder_vault} vault
                          </p>
                          <p className="mt-0.5 font-mono text-[9px] text-slate-400">
                            {r.error
                              ? r.error
                              : r.hits > 0
                                ? `${r.hits} identifier match${r.hits > 1 ? 'es' : ''} · ` +
                                  `${r.hit_summaries.reduce((n, s) => n + s.record_count, 0)} records`
                                : 'no matches — clean'}
                          </p>
                          {r.hit_summaries.slice(0, 2).map((s) => (
                            <p key={s.entity_key} className="mt-0.5 truncate font-mono text-[8px] text-slate-500">
                              {s.entity_key} → {s.record_ids.slice(0, 3).join(', ')}
                              {s.record_count > 3 ? ` +${s.record_count - 3}` : ''}
                            </p>
                          ))}
                        </div>
                        {r.verified
                          ? <BadgeCheck size={14} className="shrink-0 text-emerald-400" />
                          : <BadgeX size={14} className="shrink-0 text-red-400" />}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {res.victim_shield_applied && (
                <div className="flex items-start gap-2 rounded-lg border border-purple-400/30 bg-purple-400/[0.06] p-3">
                  <Shield size={13} className="mt-0.5 shrink-0 text-purple-400" />
                  <p className="text-[11px] leading-snug text-slate-400">
                    Victim-shield applied — the complainant is pseudonymized and excluded from
                    network analysis under Women Safety Division policy.
                  </p>
                </div>
              )}

              <div className="flex gap-2">
                <button onClick={onClose}
                        className="flex-1 rounded-lg bg-cyan-500/15 py-2 text-xs font-semibold text-cyan-400 transition-colors hover:bg-cyan-500/25">
                  View in graph →
                </button>
                <button onClick={() => { setRes(null); setNarrative('') }}
                        className="rounded-lg bg-slate-700/40 px-4 py-2 text-xs font-medium text-slate-300 transition-colors hover:bg-slate-700/60">
                  File another
                </button>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  )
}
