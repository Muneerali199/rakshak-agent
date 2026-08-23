import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router'
import GraphCanvas from '@/workbench/GraphCanvas'
import QueryRail from '@/workbench/QueryRail'
import EvidencePanel from '@/workbench/EvidencePanel'
import {
  api, LAYER_COLOR, type EntitySummary, type LayerName, type SubgraphResponse,
} from '@/lib/api'

const DEFAULT_LAYERS: LayerName[] = ['communication', 'financial', 'spatial']

export default function Workbench() {
  const [entities, setEntities] = useState<EntitySummary[]>([])
  const [activeId, setActiveId] = useState<string | null>(null)
  const [raw, setRaw] = useState<SubgraphResponse | null>(null)
  const [selectedEdge, setSelectedEdge] = useState<string | null>(null)
  const [layers, setLayers] = useState<LayerName[]>(DEFAULT_LAYERS)
  const [minConf, setMinConf] = useState(0.5)
  const [showInferred, setShowInferred] = useState(true)
  const [online, setOnline] = useState<boolean | null>(null)

  // bootstrap: health check + top entities
  useEffect(() => {
    api.health().then(() => setOnline(true)).catch(() => setOnline(false))
    api.entities('PERSON', 24)
      .then((e) => { setEntities(e); if (e[0]) setActiveId(e[0].id) })
      .catch(() => setOnline(false))
  }, [])

  // fetch subgraph when the active entity changes
  useEffect(() => {
    if (!activeId) return
    setSelectedEdge(null)
    api.subgraph(activeId, 2).then(setRaw).catch(() => setRaw(null))
  }, [activeId])

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

  return (
    <div className="flex h-screen w-screen flex-col bg-[#050505] text-zinc-200">
      {/* top bar */}
      <header className="flex h-14 shrink-0 items-center justify-between border-b border-zinc-800 px-4">
        <div className="flex items-center gap-3">
          <Link to="/" className="font-cinzel text-sm font-bold tracking-[0.3em] text-white">RAKSHAK</Link>
          <span className="font-mono text-[10px] tracking-[0.25em] text-zinc-500">CASE WORKBENCH</span>
        </div>
        <div className="flex items-center gap-4">
          {filtered && (
            <span className="font-mono text-[10px] text-zinc-500">
              {filtered.stats.nodes} nodes · {filtered.stats.edges} edges · {filtered.stats.inferred} inferred
            </span>
          )}
          <span className="rounded-full border border-amber-500/40 px-2 py-0.5 font-mono text-[9px] text-amber-400">
            uncalibrated
          </span>
          <span className="flex items-center gap-1.5 font-mono text-[10px] text-zinc-400">
            <span className="h-1.5 w-1.5 rounded-full"
                  style={{ background: online === false ? '#ff2d55' : online ? '#34d399' : '#8b93a7' }} />
            {online === false ? 'API offline' : online ? 'live' : '…'}
          </span>
        </div>
      </header>

      {online === false && (
        <div className="border-b border-[#ff2d55]/30 bg-[#ff2d55]/10 px-4 py-2 text-center font-mono text-[11px] text-[#ff2d55]">
          Backend API not reachable at {api.base}. Run: <span className="text-zinc-200">cd app/backend &amp;&amp; uvicorn api.main:app --port 8000</span>
        </div>
      )}

      <div className="flex min-h-0 flex-1">
        <QueryRail
          entities={entities} activeId={activeId} onPick={setActiveId}
          layers={layers} setLayers={setLayers}
          minConf={minConf} setMinConf={setMinConf}
          showInferred={showInferred} setShowInferred={setShowInferred}
        />
        <main className="min-w-0 flex-1">
          <GraphCanvas subgraph={filtered} onEdgeClick={setSelectedEdge} selectedEdge={selectedEdge} />
        </main>
        <EvidencePanel edgeId={selectedEdge} layerColorHint={selectedLayerColor} />
      </div>
    </div>
  )
}
