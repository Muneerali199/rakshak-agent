import { useMemo, useState } from 'react'
import {
  Background, Controls, MiniMap, ReactFlow, type Edge, type Node,
} from '@xyflow/react'
import '@xyflow/react/dist/style.css'
import EntityNode, { type EntityNodeData } from './EntityNode'
import LayeredEdge, { type LayeredEdgeData } from './LayeredEdge'
import { LAYER_COLOR, LAYER_LABEL, type LayerName, type SubgraphResponse } from '@/lib/api'

const nodeTypes = { entity: EntityNode }
const edgeTypes = { layered: LayeredEdge }

const LANES: LayerName[] = ['communication', 'financial', 'spatial']
const LANE_GAP = 14
const COL_W = 250
const ROW_H = 100
const MAX_COLS = 5          // wrap long lanes into a grid so nodes stay readable

interface LaneBox { name: LayerName; top: number; height: number }

// Assign each node to its primary lane, then lay nodes out in a wrapped grid
// within the lane (row wraps every MAX_COLS). Deterministic, no external layout.
function layout(
  sg: SubgraphResponse,
  onEdgeClick: (edgeId: string) => void,
  focusTick: number,
): { nodes: Node[]; edges: Edge[]; lanes: LaneBox[] } {
  const laneOf = (layers: LayerName[]): LayerName =>
    LANES.find((l) => layers.includes(l)) ?? 'communication'

  // 1) count nodes per lane → lane heights
  const counts: Record<string, number> = {}
  for (const n of sg.nodes) {
    const l = laneOf(n.layers)
    counts[l] = (counts[l] ?? 0) + 1
  }
  const lanes: LaneBox[] = []
  let top = 0
  for (const name of LANES) {
    const rows = Math.max(1, Math.ceil((counts[name] ?? 0) / MAX_COLS))
    const height = Math.max(140, rows * ROW_H + 56)
    lanes.push({ name, top, height })
    top += height + LANE_GAP
  }
  const laneTop = Object.fromEntries(lanes.map((l) => [l.name, l.top])) as Record<LayerName, number>

  // 2) place nodes on a wrapped grid inside their lane
  const perLane: Record<string, number> = {}
  const nodes: Node[] = sg.nodes.map((n) => {
    const lane = laneOf(n.layers)
    const i = (perLane[lane] = (perLane[lane] ?? 0) + 1) - 1
    const col = i % MAX_COLS
    const row = Math.floor(i / MAX_COLS)
    return {
      id: n.id,
      type: 'entity',
      position: {
        x: 28 + col * COL_W,
        y: laneTop[lane] + 34 + row * ROW_H + (col % 2) * 14,
      },
      data: {
        label: n.label, type: n.type, layers: n.layers, risk: n.risk,
        role: (n.meta?.role as string | undefined) ?? null,
        isRoot: n.id === sg.root,
        focusTick: n.id === sg.root ? focusTick : undefined,
      } as EntityNodeData,
    }
  })

  const edges: Edge[] = sg.edges.map((e) => ({
    id: e.id,
    source: e.source,
    target: e.target,
    type: 'layered',
    data: {
      layer: e.layer, creation_method: e.creation_method,
      confidence: e.confidence, etype: e.type, review_status: e.review_status,
      focusGlow: e.source === sg.root || e.target === sg.root,
      onEdgeClick,
    } as LayeredEdgeData,
  }))
  return { nodes, edges, lanes }
}

const HINT_KEY = 'rakshak-workbench-hint-dismissed'

export default function GraphCanvas({
  subgraph, onEdgeClick, onNodeClick, selectedEdge, focusTick,
}: {
  subgraph: SubgraphResponse | null
  onEdgeClick: (edgeId: string) => void
  onNodeClick?: (nodeId: string) => void
  selectedEdge: string | null
  focusTick: number
}) {
  const { nodes, edges, lanes } = useMemo(
    () => (subgraph ? layout(subgraph, onEdgeClick, focusTick) : { nodes: [], edges: [], lanes: [] }),
    [subgraph, onEdgeClick, focusTick],
  )

  // the focused entity — for the "investigating" banner
  const rootNode = subgraph?.nodes.find((n) => n.id === subgraph.root) ?? null

  const styledEdges = useMemo(
    () => edges.map((e) => ({ ...e, selected: e.id === selectedEdge })),
    [edges, selectedEdge],
  )

  const [hint, setHint] = useState(() => localStorage.getItem(HINT_KEY) !== 'off')
  const dismissHint = () => { localStorage.setItem(HINT_KEY, 'off'); setHint(false) }

  return (
    <div className="relative h-full w-full">
      {/* lane backgrounds + labels */}
      <div className="pointer-events-none absolute inset-0 z-0">
        {lanes.map(({ name, top, height }) => (
          <div key={name} className="absolute inset-x-0" style={{ top, height }}>
            <div className="h-full w-full rounded-lg" style={{ background: `${LAYER_COLOR[name]}08` }} />
            <span className="absolute left-3 top-2 font-mono text-[9px] uppercase tracking-[0.3em]"
                  style={{ color: LAYER_COLOR[name] }}>
              {LAYER_LABEL[name]}
            </span>
          </div>
        ))}
      </div>

      {/* first-visit quick start */}
      {hint && subgraph && (
        <div className="absolute left-3 top-8 z-10 w-64 rounded-lg border border-white/10 bg-slate-900/90 p-3 shadow-xl backdrop-blur-md">
          <div className="mb-1.5 flex items-center justify-between">
            <span className="font-mono text-[9px] uppercase tracking-[0.25em] text-zinc-400">Quick start</span>
            <button onClick={dismissHint} className="font-mono text-[10px] text-zinc-500 hover:text-zinc-200">✕</button>
          </div>
          <ol className="space-y-1.5 text-[11px] leading-snug text-zinc-400">
            <li><span className="mr-1 font-mono text-[#00f0ff]">1.</span>Pick a person from the left rail</li>
            <li><span className="mr-1 font-mono text-[#00f0ff]">2.</span>Click a <b className="text-zinc-200">node</b> to re-center on them</li>
            <li><span className="mr-1 font-mono text-[#00f0ff]">3.</span>Click an <b className="text-zinc-200">edge</b> to inspect its evidence</li>
            <li><span className="mr-1 font-mono text-[#00f0ff]">4.</span>Accept / Reject / Modify — logged &amp; hashed</li>
          </ol>
        </div>
      )}

      {/* focus banner — whose network am I looking at? */}
      {rootNode && (
        <div className="pointer-events-none absolute left-1/2 top-2 z-10 w-max max-w-[75%] -translate-x-1/2">
          <div className="flex items-center gap-2.5 rounded-full border border-cyan-400/25 bg-slate-900/90 py-1.5 pl-3 pr-3.5 shadow-lg backdrop-blur-md">
            <span className="relative flex h-2 w-2 shrink-0">
              <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-cyan-400 opacity-60" />
              <span className="relative inline-flex h-2 w-2 rounded-full bg-cyan-400" />
            </span>
            <span className="shrink-0 font-mono text-[8px] uppercase tracking-[0.28em] text-cyan-400/80">
              investigating
            </span>
            <span className="truncate text-xs font-semibold text-slate-100" title={rootNode.label}>
              {rootNode.label}
            </span>
            <span className="hidden shrink-0 rounded border border-slate-700/60 px-1.5 py-0.5 font-mono text-[8px] uppercase tracking-wider text-slate-500 sm:inline">
              {rootNode.type.toLowerCase()}
            </span>
            <span className="hidden shrink-0 font-mono text-[8px] text-slate-600 md:inline">
              {rootNode.id}
            </span>
          </div>
        </div>
      )}

      {/* edge legend — always visible */}
      {subgraph && (
        <div className="pointer-events-none absolute bottom-3 left-3 z-10 flex flex-col gap-1 rounded-md border border-white/10 bg-slate-900/90 px-2.5 py-2 font-mono text-[9px] text-slate-400 backdrop-blur-md">
          <span className="flex items-center gap-2">
            <span className="inline-block h-0.5 w-6" style={{ background: '#00f0ff' }} /> observed fact
          </span>
          <span className="flex items-center gap-2">
            <span className="inline-block h-0.5 w-6 opacity-70"
                  style={{ background: 'repeating-linear-gradient(90deg,#71717a 0 4px,transparent 4px 7px)' }} />
            inferred · needs review
          </span>
          <span className="flex items-center gap-2">
            <span className="inline-block h-2 w-2 animate-pulse rounded-full bg-[#ff2d55]" /> high risk
          </span>
        </div>
      )}

      <ReactFlow
        nodes={nodes}
        edges={styledEdges}
        nodeTypes={nodeTypes}
        edgeTypes={edgeTypes}
        onEdgeClick={(_, edge) => onEdgeClick(edge.id)}
        onNodeClick={(_, node) => onNodeClick?.(node.id)}
        nodesDraggable={false}
        fitView
        fitViewOptions={{ padding: 0.18, maxZoom: 1 }}
        minZoom={0.15}
        maxZoom={1.6}
        proOptions={{ hideAttribution: true }}
        className="!bg-transparent"
      >
        <Background color="#1e293b" gap={28} />
        <MiniMap pannable zoomable
                 style={{ background: '#0a0f1c', border: '1px solid #1e293b', width: 160, height: 110 }}
                 maskColor="rgba(10,15,28,0.8)"
                 nodeColor={(n) => {
                   const risk = (n.data as EntityNodeData)?.risk ?? 0
                   return risk > 0.6 ? '#ef4444' : '#334155'
                 }} />
        <Controls className="!border-slate-700/50 !bg-slate-900/90 [&>button]:!border-slate-700/50 [&>button]:!bg-slate-900/90 [&>button]:!fill-slate-300" />
      </ReactFlow>

      {!subgraph && (
        <div className="absolute inset-0 z-10 grid place-items-center">
          <p className="font-mono text-xs text-slate-600">Select an entity to render its network…</p>
        </div>
      )}
    </div>
  )
}
