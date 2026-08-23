import { BaseEdge, EdgeLabelRenderer, getBezierPath, type EdgeProps } from '@xyflow/react'
import { LAYER_COLOR, type CreationMethod, type LayerName } from '@/lib/api'

export interface LayeredEdgeData {
  layer: LayerName
  creation_method: CreationMethod
  confidence: number
  etype: string
  [key: string]: unknown
}

// The core visual contract (UI spec §Center):
//   Observed (EXTRACTED) → solid, layer color, opacity 1.0
//   Inferred (INFERRED)  → dashed grey, opacity 0.4 + 0.6·confidence
export default function LayeredEdge(props: EdgeProps) {
  const { sourceX, sourceY, targetX, targetY, sourcePosition, targetPosition, markerEnd, selected } = props
  const d = props.data as LayeredEdgeData
  const [path, labelX, labelY] = getBezierPath({
    sourceX, sourceY, sourcePosition, targetX, targetY, targetPosition,
  })

  const inferred = d.creation_method === 'INFERRED'
  const color = inferred ? '#71717a' : LAYER_COLOR[d.layer]
  const opacity = inferred ? 0.4 + 0.6 * d.confidence : 1
  const width = selected ? 3 : inferred ? 1.5 : 2

  return (
    <>
      <BaseEdge
        id={props.id}
        path={path}
        markerEnd={markerEnd}
        style={{
          stroke: color,
          strokeWidth: width,
          strokeDasharray: inferred ? '6 4' : undefined,
          opacity,
          filter: selected ? `drop-shadow(0 0 4px ${color})` : undefined,
        }}
      />
      {(inferred || selected) && (
        <EdgeLabelRenderer>
          <div
            className="nodrag nopan absolute rounded px-1 py-0.5 font-mono text-[8px]"
            style={{
              transform: `translate(-50%,-50%) translate(${labelX}px,${labelY}px)`,
              background: '#0b0d12',
              border: `1px solid ${color}66`,
              color,
            }}
          >
            {inferred ? `${d.etype.toLowerCase()} · ${d.confidence.toFixed(2)}` : d.etype}
          </div>
        </EdgeLabelRenderer>
      )}
    </>
  )
}
