import { Handle, Position, type NodeProps } from '@xyflow/react'
import { LAYER_COLOR, type LayerName, type NodeType } from '@/lib/api'

export interface EntityNodeData {
  label: string
  type: NodeType
  layers: LayerName[]
  risk: number | null
  isRoot?: boolean
  [key: string]: unknown
}

const TYPE_GLYPH: Record<NodeType, string> = {
  PERSON: '◉',
  PHONE: '☏',
  ACCOUNT: '₹',
  LOCATION: '⌖',
  VEHICLE: '⛟',
}

const TYPE_TINT: Record<NodeType, string> = {
  PERSON: '#e4e4e7',
  PHONE: '#00f0ff',
  ACCOUNT: '#34d399',
  LOCATION: '#f59e0b',
  VEHICLE: '#c084fc',
}

// One node renderer for all entity types. High risk (>0.6) gets a pulsing red ring;
// multi-layer "hub" nodes get a white halo — both cues from the UI spec.
export default function EntityNode({ data, selected }: NodeProps) {
  const d = data as EntityNodeData
  const highRisk = (d.risk ?? 0) > 0.6
  const isHub = d.layers.length >= 2
  const tint = TYPE_TINT[d.type]

  return (
    <div
      className={[
        'relative flex min-w-[132px] max-w-[180px] items-center gap-2 rounded-xl border px-3 py-2',
        'bg-[#0b0d12] transition-shadow',
        selected ? 'border-white shadow-[0_0_0_2px_rgba(255,255,255,0.5)]' : 'border-zinc-700',
        highRisk ? 'ring-2 ring-[#ff2d55] animate-pulse' : '',
        isHub && !highRisk ? 'shadow-[0_0_18px_-4px_rgba(255,255,255,0.35)]' : '',
      ].join(' ')}
    >
      <Handle type="target" position={Position.Left} className="!h-1.5 !w-1.5 !border-0 !bg-zinc-600" />
      <span className="grid h-8 w-8 shrink-0 place-items-center rounded-full text-sm"
            style={{ background: `${tint}1a`, color: tint }}>
        {TYPE_GLYPH[d.type]}
      </span>
      <div className="min-w-0">
        <div className="truncate text-[11px] font-medium text-zinc-100" title={d.label}>{d.label}</div>
        <div className="flex items-center gap-1">
          <span className="font-mono text-[8px] uppercase tracking-wider text-zinc-500">{d.type}</span>
          {d.risk != null && (
            <span className="font-mono text-[8px]" style={{ color: highRisk ? '#ff2d55' : '#8b93a7' }}>
              · r{d.risk.toFixed(2)}
            </span>
          )}
        </div>
      </div>
      {/* layer dots */}
      <div className="absolute -top-1.5 right-2 flex gap-0.5">
        {d.layers.map((l) => (
          <span key={l} className="h-1.5 w-1.5 rounded-full" style={{ background: LAYER_COLOR[l] }} />
        ))}
      </div>
      <Handle type="source" position={Position.Right} className="!h-1.5 !w-1.5 !border-0 !bg-zinc-600" />
    </div>
  )
}
