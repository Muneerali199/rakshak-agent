import {
  BaseEdge,
  EdgeLabelRenderer,
  getBezierPath,
  type EdgeProps,
} from '@xyflow/react'
import { Eye, Brain, Check, X } from 'lucide-react'
import { LAYER_COLOR, type CreationMethod, type LayerName, type ReviewStatus } from '@/lib/api'

export interface LayeredEdgeData {
  layer: LayerName
  creation_method: CreationMethod
  confidence: number
  etype: string
  review_status?: ReviewStatus
  onEdgeClick?: (edgeId: string) => void
  [key: string]: unknown
}

export default function LayeredEdge(props: EdgeProps) {
  const {
    sourceX, sourceY, targetX, targetY,
    sourcePosition, targetPosition, markerEnd, selected,
  } = props
  const d = props.data as LayeredEdgeData
  const [path, labelX, labelY] = getBezierPath({
    sourceX, sourceY, sourcePosition, targetX, targetY, targetPosition,
  })

  const inferred = d.creation_method === 'INFERRED'
  const accepted = d.review_status === 'ACCEPTED'
  const rejected = d.review_status === 'REJECTED'
  const solid = !inferred || accepted
  const color = inferred && !accepted ? '#64748b' : LAYER_COLOR[d.layer]
  const opacity = rejected ? 0.12 : solid ? 1 : 0.4 + 0.6 * d.confidence
  const width = selected ? 3.5 : solid ? 2.5 : 1.5

  const labelText = rejected
    ? `${d.etype.toLowerCase()} · rejected`
    : solid && inferred
      ? `✓ ${d.etype.toLowerCase()} · ${d.confidence.toFixed(2)}`
      : inferred
        ? `${d.etype.toLowerCase()} · ${d.confidence.toFixed(2)}`
        : d.etype

  return (
    <>
      <BaseEdge
        id={props.id}
        path={path}
        markerEnd={markerEnd}
        interactionWidth={24}
        style={{
          stroke: color,
          strokeWidth: width,
          strokeDasharray: solid ? undefined : '8 8',
          opacity,
          filter: selected ? `drop-shadow(0 0 5px ${color})` : undefined,
          transition: 'stroke-width 0.15s, opacity 0.15s',
        }}
      />
      {(inferred || selected) && (
        <EdgeLabelRenderer>
          <div
            onClick={(e) => { e.stopPropagation(); d.onEdgeClick?.(props.id) }}
            className="nodrag nopan absolute flex cursor-pointer items-center gap-1 rounded-md px-2 py-0.5 font-mono text-[8px] backdrop-blur-md"
            style={{
              transform: `translate(-50%,-50%) translate(${labelX}px,${labelY}px)`,
              background: 'rgba(15,23,42,0.9)',
              border: `1px solid ${color}40`,
              color,
              opacity: rejected ? 0.3 : undefined,
              boxShadow: selected ? `0 0 8px ${color}40` : '0 2px 8px rgba(0,0,0,0.4)',
            }}
          >
            {rejected ? (
              <X size={8} strokeWidth={2.5} />
            ) : solid && inferred ? (
              <Check size={8} strokeWidth={2.5} />
            ) : inferred ? (
              <Brain size={8} strokeWidth={2} />
            ) : (
              <Eye size={8} strokeWidth={2} />
            )}
            {labelText}
          </div>
        </EdgeLabelRenderer>
      )}
    </>
  )
}
