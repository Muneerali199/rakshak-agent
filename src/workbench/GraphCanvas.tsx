import { useMemo } from 'react'
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
const LANE_H = 240
const COL_W = 210

// Assign each node to its primary lane (first layer in LANES order), then lay nodes
// out left→right within the lane. Deterministic, no external layout dependency.
function layout(sg: SubgraphResponse): { nodes: Node[]; edges: Edge[] } {
  const laneOf = (layers: LayerName[]): LayerName =>
    LANES.find((l) => layers.includes(l)) ?? 'communication'

  const perLane: Record<string, number> = {}
  const nodes: Node[] = sg.nodes.map((n) => {
    const lane = laneOf(n.layers)
    const laneIdx = LANES.indexOf(lane)
    const col = (perLane[lane] = (perLane[lane] ?? 0) + 1) - 1
    return {
      id: n.id,
      type: 'entity',
      position: { x: 60 + col * COL_W, y: 70 + laneIdx * LANE_H + (col % 2) * 42 },
      data: {
        label: n.label, type: n.type, layers: n.layers, risk: n.risk,
        isRoot: n.id === sg.root,
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
      confidence: e.confidence, etype: e.type,
    } as LayeredEdgeData,
  }))
  return { nodes, edges }
}

export default function GraphCanvas({
  subgraph, onEdgeClick, selectedEdge,
}: {
  subgraph: SubgraphResponse | null
  onEdgeClick: (edgeId: string) => void
  selectedEdge: string | null
}) {
  const { nodes, edges } = useMemo(
    () => (subgraph ? layout(subgraph) : { nodes: [], edges: [] }),
    [subgraph],
  )

  const styledEdges = useMemo(
    () => edges.map((e) => ({ ...e, selected: e.id === selectedEdge })),
    [edges, selectedEdge],
  )

  return (
    <div className="relative h-full w-full">
      {/* lane backgrounds + labels */}
      <div className="pointer-events-none absolute inset-0 z-0">
        {LANES.map((lane, i) => (
          <div key={lane} className="absolute inset-x-0" style={{ top: i * LANE_H + 40, height: LANE_H }}>
            <div className="h-full w-full" style={{ background: `${LAYER_COLOR[lane]}0a` }} />
            <span className="absolute left-3 top-2 font-mono text-[9px] uppercase tracking-[0.3em]"
                  style={{ color: LAYER_COLOR[lane] }}>
              {LAYER_LABEL[lane]}
            </span>
          </div>
        ))}
      </div>

      <ReactFlow
        nodes={nodes}
        edges={styledEdges}
        nodeTypes={nodeTypes}
        edgeTypes={edgeTypes}
        onEdgeClick={(_, edge) => onEdgeClick(edge.id)}
        fitView
        proOptions={{ hideAttribution: true }}
        className="!bg-transparent"
        minZoom={0.2}
      >
        <Background color="#1a1d24" gap={26} />
        <MiniMap pannable zoomable
                 style={{ background: '#0b0d12', border: '1px solid #27272a' }}
                 nodeColor={(n) => {
                   const risk = (n.data as EntityNodeData)?.risk ?? 0
                   return risk > 0.6 ? '#ff2d55' : '#3f3f46'
                 }} />
        <Controls className="!border-zinc-700 !bg-[#0b0d12] [&>button]:!border-zinc-700 [&>button]:!bg-[#0b0d12] [&>button]:!fill-zinc-300" />
      </ReactFlow>

      {!subgraph && (
        <div className="absolute inset-0 z-10 grid place-items-center">
          <p className="font-mono text-xs text-zinc-500">Select an entity to render its network…</p>
        </div>
      )}
    </div>
  )
}
