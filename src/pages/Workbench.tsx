import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { Link } from 'react-router'
import GraphCanvas from '@/workbench/GraphCanvas'
import QueryRail from '@/workbench/QueryRail'
import QueryBar from '@/workbench/QueryBar'
import EvidencePanel from '@/workbench/EvidencePanel'
import TimeSlider from '@/workbench/TimeSlider'
import DemoMode from '@/workbench/DemoMode'
import FileFirPanel from '@/workbench/FileFirPanel'
import {
  api, LAYER_COLOR, type EntitySummary, type LayerName, type ReviewStatus, type SubgraphResponse,
} from '@/lib/api'

const DEFAULT_LAYERS: LayerName[] = ['communication', 'financial', 'spatial']

function useMediaQuery(query: string): boolean {
  const [matches, setMatches] = useState(
    () => typeof window !== 'undefined' && window.matchMedia(query).matches,
  )
  useEffect(() => {
    const mq = window.matchMedia(query)
    const onChange = () => setMatches(mq.matches)
    mq.addEventListener('change', onChange)
    return () => mq.removeEventListener('change', onChange)
  }, [query])
  return matches
}

type Pane = 'search' | 'graph' | 'evidence'

export default function Workbench() {
  const [entities, setEntities] = useState<EntitySummary[]>([])
  const [activeId, setActiveId] = useState<string | null>(null)
  const [raw, setRaw] = useState<SubgraphResponse | null>(null)
  const [selectedEdge, setSelectedEdge] = useState<string | null>(null)
  const [layers, setLayers] = useState<LayerName[]>(DEFAULT_LAYERS)
  const [minConf, setMinConf] = useState(0.5)
  const [showInferred, setShowInferred] = useState(true)
  const [depth, setDepth] = useState(1)
  const [online, setOnline] = useState<boolean | null>(null)
  const [vault, setVault] = useState<string | null>(null)
  const [pane, setPane] = useState<Pane>('graph')
  // auto-load context: which anomaly the workbench opened on (the case narrative)
  const [autoCase, setAutoCase] = useState<{ kind: string; label: string } | null>(null)
  // time-travel: end-of-window timestamp (ms); null = no time filter
  const [timeEnd, setTimeEnd] = useState<number | null>(null)
  // guided demo overlay
  const [demo, setDemo] = useState(false)
  // file-new-FIR modal + a bump counter that forces subgraph refetch after ingest
  const [fileFir, setFileFir] = useState(false)
  const [dataVersion, setDataVersion] = useState(0)

  const isNarrow = useMediaQuery('(max-width: 1023px)')

  // bootstrap: health check + top entities, then AUTO-LOAD the lead case —
  // the highest-severity circular-flow ring — so the workbench opens on the story,
  // not an empty screen.
  useEffect(() => {
    api.health().then((h) => { setOnline(true); setVault(h.vault ?? null) }).catch(() => setOnline(false))
    api.entities('PERSON', 24)
      .then((e) => setEntities(e))
      .catch(() => setOnline(false))
    api.anomalies()
      .then((a) => {
        const ring = a.anomalies.find((x) => x.kind === 'CIRCULAR_FLOW') ?? a.anomalies[0]
        if (ring) {
          setActiveId(ring.entity_id)
          setDepth(2)                    // rings need 2 hops to render fully
          setAutoCase({ kind: ring.kind, label: ring.label })
        }
      })
      .catch(() => {})
  }, [])

  // fetch subgraph when the active entity, depth, time window, or data version changes
  useEffect(() => {
    if (!activeId) return
    setSelectedEdge(null)
    const end = timeEnd ? new Date(timeEnd).toISOString().slice(0, 10) : undefined
    api.subgraph(activeId, depth, undefined, undefined, end).then(setRaw).catch(() => setRaw(null))
  }, [activeId, depth, timeEnd, dataVersion])

  // after a live FIR ingestion: refocus on the newly-created accused node and refetch
  const handleIngested = useCallback((res: { new_edges: Array<{ source: string }> }) => {
    const focus = res.new_edges[0]?.source
    setDataVersion((v) => v + 1)
    if (focus) setActiveId(focus)
  }, [])

  // NL-query results: focus the entity, then open the cited edge once its
  // subgraph has loaded (pendingEdge survives the refetch).
  const pendingEdge = useRef<string | null>(null)
  const handleQueryResult = useCallback((entityId: string, edgeId?: string) => {
    pendingEdge.current = edgeId ?? null
    setActiveId((cur) => {
      if (cur === entityId && edgeId) {
        setSelectedEdge(edgeId)          // same subgraph already loaded
        pendingEdge.current = null
      }
      return entityId
    })
  }, [])

  useEffect(() => {
    if (raw && pendingEdge.current) {
      const eid = pendingEdge.current
      pendingEdge.current = null
      if (raw.edges.some((e) => e.id === eid)) setSelectedEdge(eid)
    }
  }, [raw])

  // client-side filtering (layers · confidence · inferred toggle) without a refetch
  const filtered = useMemo<SubgraphResponse | null>(() => {
    if (!raw) return null
    const layerSet = new Set(layers)
    const edges = raw.edges.filter((e) =>
      layerSet.has(e.layer) &&
      e.confidence >= minConf &&
      (showInferred || e.creation_method === 'EXTRACTED'),
    )
    const keep = new Set<string>([raw.root])
    edges.forEach((e) => { keep.add(e.source); keep.add(e.target) })
    const nodes = raw.nodes.filter((n) => keep.has(n.id) && n.layers.some((l) => layerSet.has(l)))
    const nodeIds = new Set(nodes.map((n) => n.id))
    return {
      ...raw,
      nodes,
      edges: edges.filter((e) => nodeIds.has(e.source) && nodeIds.has(e.target)),
      stats: { nodes: nodes.length, edges: edges.length, inferred: edges.filter((e) => e.creation_method === 'INFERRED').length },
    }
  }, [raw, layers, minConf, showInferred])

  const selectedLayerColor = useMemo(() => {
    const e = raw?.edges.find((x) => x.id === selectedEdge)
    return e ? LAYER_COLOR[e.layer] : undefined
  }, [raw, selectedEdge])

  // time-travel window: earliest/latest edge timestamps in the loaded subgraph
  const timeRange = useMemo(() => {
    if (!raw) return null
    const stamps = raw.edges
      .map((e) => e.timestamp)
      .filter((t): t is string => !!t)
      .map((t) => Date.parse(t))
      .filter((t) => Number.isFinite(t))
    if (stamps.length < 2) return null
    return { min: Math.min(...stamps), max: Math.max(...stamps) }
  }, [raw])

  // reset the scrubber to "now" whenever a new entity is loaded
  useEffect(() => {
    setTimeEnd(null)
  }, [activeId])

  // HITL payoff: patch the reviewed edge into the in-memory subgraph so the canvas
  // re-renders instantly (accepted inferred → solid, rejected → ghosted).
  const handleReviewed = useCallback(
    (edgeId: string, status: ReviewStatus, confidence: number) => {
      setRaw((prev) => prev
        ? { ...prev, edges: prev.edges.map((e) => e.id === edgeId ? { ...e, review_status: status, confidence } : e) }
        : prev)
    },
    [],
  )

  const pickEntity = useCallback((id: string) => {
    setActiveId(id)
    if (isNarrow) setPane('graph')
  }, [isNarrow])

  const pickEdge = useCallback((edgeId: string) => {
    setSelectedEdge(edgeId)
    if (isNarrow) setPane('evidence')
  }, [isNarrow])

  // clicking a node re-centers the investigation on that entity
  const focusNode = useCallback((nodeId: string) => {
    setActiveId(nodeId)
  }, [])

  const rail = (
    <QueryRail
      entities={entities} activeId={activeId} onPick={pickEntity}
      layers={layers} setLayers={setLayers}
      minConf={minConf} setMinConf={setMinConf}
      showInferred={showInferred} setShowInferred={setShowInferred}
    />
  )
  const canvas = (
    <div className="relative h-full">
      <GraphCanvas subgraph={filtered} onEdgeClick={pickEdge} onNodeClick={focusNode} selectedEdge={selectedEdge} />
      {timeRange && (
        <TimeSlider
          minTs={timeRange.min}
          maxTs={timeRange.max}
          value={timeEnd ?? timeRange.max}
          onChange={(ts) => setTimeEnd(ts >= timeRange.max ? null : ts)}
          edgeCount={filtered?.stats.edges ?? 0}
        />
      )}
    </div>
  )
  const evidence = (
    <EvidencePanel edgeId={selectedEdge} layerColorHint={selectedLayerColor} onReviewed={handleReviewed} />
  )

  return (
    <div className="relative flex h-[100dvh] w-screen flex-col bg-[#0a0f1c] text-slate-200">
      {/* top bar */}
      <header className="flex h-14 shrink-0 items-center justify-between gap-3 border-b border-white/5 bg-[#0a0f1c] px-4 backdrop-blur-md">
        <div className="flex min-w-0 items-center gap-3">
          <Link to="/" className="font-cinzel text-sm font-bold tracking-[0.3em] text-white">RAKSHAK</Link>
          <span className="hidden font-mono text-[10px] tracking-[0.25em] text-slate-500 md:inline">CASE WORKBENCH</span>
          <button onClick={() => setFileFir(true)}
                  className="rounded-md border border-cyan-400/50 bg-cyan-400/15 px-2.5 py-1 font-mono text-[10px] font-semibold text-cyan-300 transition-colors hover:bg-cyan-400/25">
            ＋ File FIR
          </button>
          <Link to="/scanner"
                className="hidden rounded border border-slate-700/50 px-2 py-0.5 font-mono text-[9px] text-slate-400 transition-colors hover:border-red-400/50 hover:text-red-400 sm:inline">
            ⚡ RakshakAI scanner
          </Link>
          <button onClick={() => setDemo(true)}
                  className="rounded border border-slate-700/50 px-2 py-0.5 font-mono text-[9px] text-slate-400 transition-colors hover:border-cyan-400/50 hover:text-cyan-400">
            ▶ demo
          </button>
          {autoCase && (
            <span className="hidden rounded border border-red-400/30 bg-red-400/10 px-2 py-0.5 font-mono text-[9px] text-red-400 md:inline"
                  title={`Workbench opened on the lead anomaly: ${autoCase.label}`}>
              CASE AUTO-LOADED · {autoCase.kind.replace(/_/g, ' ')}
            </span>
          )}
        </div>
        <div className="flex items-center gap-3">
          {/* depth selector */}
          <div className="flex items-center gap-1.5">
            <span className="hidden font-mono text-[9px] uppercase tracking-wider text-slate-500 sm:inline">depth</span>
            <div className="flex overflow-hidden rounded-md border border-slate-700/50">
              {[1, 2, 3].map((d) => (
                <button key={d} onClick={() => setDepth(d)}
                        className={[
                          'px-2.5 py-1 font-mono text-[10px] transition-colors',
                          depth === d ? 'bg-cyan-400/15 text-cyan-400' : 'text-slate-500 hover:bg-white/5 hover:text-slate-300',
                        ].join(' ')}>
                  {d}
                </button>
              ))}
            </div>
          </div>
          {filtered && (
            <span className="hidden font-mono text-[10px] text-slate-500 lg:inline">
              {filtered.stats.nodes} nodes · {filtered.stats.edges} edges · {filtered.stats.inferred} inferred
            </span>
          )}
          {activeId && (
            <Link to={`/report/${encodeURIComponent(activeId)}`}
                  className="hidden rounded border border-slate-700/50 px-2 py-0.5 font-mono text-[9px] text-slate-400 transition-colors hover:border-emerald-400/50 hover:text-emerald-400 md:inline"
                  title="Court-ready evidence chain for the focused entity">
              ⎙ report
            </Link>
          )}
          {vault && (
            <span className="hidden rounded border border-cyan-400/30 bg-cyan-400/10 px-2 py-0.5 font-mono text-[9px] uppercase text-cyan-400 sm:inline"
                  title="This console is connected to one district vault — cross-district answers arrive as signed mesh receipts (data never leaves its district)">
              ⛁ {vault} vault
            </span>
          )}
          <span className="hidden rounded-full border border-amber-500/30 bg-amber-500/10 px-2 py-0.5 font-mono text-[9px] text-amber-400 sm:inline">
            uncalibrated
          </span>
          <span className="flex items-center gap-1.5 font-mono text-[10px] text-slate-400">
            <span className="h-1.5 w-1.5 rounded-full"
                  style={{ background: online === false ? '#ef4444' : online ? '#34d399' : '#64748b' }} />
            {online === false ? 'offline' : online ? 'live' : '…'}
          </span>
        </div>
      </header>

      {online === false && (
        <div className="border-b border-red-400/20 bg-red-400/10 px-4 py-2 text-center font-mono text-[11px] text-red-400">
          Backend API not reachable at {api.base}. Run: <span className="text-slate-200">cd app/backend &amp;&amp; uvicorn api.main:app --port 8000</span>
        </div>
      )}

      <QueryBar onResult={handleQueryResult} />

      {demo && (
        <DemoMode
          onClose={() => setDemo(false)}
          focusEntity={focusNode}
          openEdge={pickEdge}
        />
      )}

      {fileFir && (
        <FileFirPanel
          onClose={() => setFileFir(false)}
          onIngested={handleIngested}
        />
      )}

      {/* ── desktop: three panes ── */}
      {!isNarrow ? (
        <div className="flex min-h-0 flex-1">
          {rail}
          <main className="min-w-0 flex-1">{canvas}</main>
          {evidence}
        </div>
      ) : (
        /* ── narrow screens: one pane at a time + bottom tabs ── */
        <>
          <div className="min-h-0 flex-1 [&>aside]:!w-full">
            {pane === 'search' && rail}
            {pane === 'graph' && <main className="h-full">{canvas}</main>}
            {pane === 'evidence' && evidence}
          </div>
          <nav className="flex h-14 shrink-0 items-stretch border-t border-white/5 bg-[#0a0f1c]">
            {([
              ['search', 'Search', '⌕'],
              ['graph', 'Graph', '◉'],
              ['evidence', 'Evidence', '▤'],
            ] as const).map(([key, label, glyph]) => (
              <button key={key} onClick={() => setPane(key)}
                      className={[
                        'flex flex-1 flex-col items-center justify-center gap-0.5 font-mono text-[9px] uppercase tracking-wider transition-colors',
                        pane === key ? 'text-cyan-400' : 'text-slate-500 hover:text-slate-300',
                      ].join(' ')}>
                <span className="text-base leading-none">{glyph}</span>
                {label}
              </button>
            ))}
          </nav>
        </>
      )}
    </div>
  )
}
