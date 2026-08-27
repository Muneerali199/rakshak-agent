import { Handle, Position, type NodeProps } from '@xyflow/react'
import { User, Phone, Building2, MapPin, Car, Shield } from 'lucide-react'
import { LAYER_COLOR, type LayerName, type NodeType } from '@/lib/api'

export interface EntityNodeData {
  label: string
  type: NodeType
  layers: LayerName[]
  risk: number | null
  role?: string | null
  isRoot?: boolean
  [key: string]: unknown
}

const ICON_MAP: Record<NodeType, typeof User> = {
  PERSON: User,
  PHONE: Phone,
  ACCOUNT: Building2,
  LOCATION: MapPin,
  VEHICLE: Car,
}

const ICON_TINT: Record<NodeType, string> = {
  PERSON: '#38bdf8',
  PHONE: '#22d3ee',
  ACCOUNT: '#34d399',
  LOCATION: '#fbbf24',
  VEHICLE: '#c084fc',
}

const TYPE_SUBLABEL: Record<NodeType, string> = {
  PERSON: 'Person',
  PHONE: 'Phone',
  ACCOUNT: 'Account',
  LOCATION: 'Location',
  VEHICLE: 'Vehicle',
}

export default function EntityNode({ data, selected }: NodeProps) {
  const d = data as EntityNodeData
  const highRisk = (d.risk ?? 0) > 0.6
  const isHub = d.layers.length >= 2
  const isVictim = d.role === 'victim'
  const isRoot = d.isRoot

  const Icon = isVictim ? Shield : ICON_MAP[d.type]
  const tint = isVictim ? '#c084fc' : ICON_TINT[d.type]
  const riskPct = d.risk != null ? Math.round(d.risk * 100) : null

  return (
    <div
      className={[
        'relative flex w-[168px] flex-col items-center gap-1.5 rounded-lg p-3',
        'backdrop-blur-md border shadow-lg transition-all duration-200',
        'bg-slate-900/80 border-slate-700/50',
        selected ? 'ring-2 ring-cyan-400/60 shadow-cyan-500/10' : '',
        highRisk ? 'ring-2 ring-red-500/50 shadow-red-500/20' : '',
        isVictim ? 'border-dashed border-purple-400/50' : '',
        isRoot && !highRisk ? 'ring-1 ring-cyan-400/30' : '',
        isHub && !highRisk ? 'shadow-cyan-500/5' : '',
      ].filter(Boolean).join(' ')}
    >
      <Handle type="target" position={Position.Left} className="!h-2 !w-2 !border-0 !bg-slate-600" />
      <Handle type="source" position={Position.Right} className="!h-2 !w-2 !border-0 !bg-slate-600" />

      {/* Layer indicator dots — top right */}
      <div className="absolute -top-1.5 right-2 flex gap-0.5">
        {d.layers.map((l) => (
          <span
            key={l}
            className="h-1.5 w-1.5 rounded-full"
            style={{ background: LAYER_COLOR[l], boxShadow: `0 0 4px ${LAYER_COLOR[l]}80` }}
          />
        ))}
      </div>

      {/* Root indicator — top left */}
      {isRoot && (
        <div className="absolute -top-1.5 left-2 flex items-center">
          <span className="h-1.5 w-1.5 rounded-full bg-cyan-400 shadow-[0_0_6px_rgba(34,211,238,0.8)]" />
        </div>
      )}

      {/* Icon */}
      <div
        className="grid h-10 w-10 place-items-center rounded-lg"
        style={{
          background: `${tint}15`,
          border: `1px solid ${tint}30`,
        }}
      >
        <Icon size={18} strokeWidth={1.8} style={{ color: tint }} />
      </div>

      {/* Label */}
      <div className="w-full text-center">
        <p
          className="truncate text-xs font-semibold text-slate-100"
          title={d.label}
        >
          {d.label}
        </p>
        <p className="mt-0.5 font-mono text-[9px] tracking-wide text-slate-500">
          {isVictim ? (
            <span className="text-purple-400">🛡 SHIELDED</span>
          ) : riskPct != null ? (
            <span className={highRisk ? 'text-red-400' : 'text-slate-500'}>
              Risk: {riskPct}%
            </span>
          ) : (
            TYPE_SUBLABEL[d.type]
          )}
        </p>
      </div>
    </div>
  )
}
