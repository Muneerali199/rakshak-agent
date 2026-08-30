// Warrant Gate — the DEPA consent moment, kept deliberately simple:
// step 1 the IO requests access (name, rank, reason) → step 2 a senior officer
// countersigns (different person, SP+) → the evidence unmasks and the whole
// exchange is hash-chained into the warrant ledger.
import { useState } from 'react'
import { Loader2, ShieldCheck, Stamp, X, AlertTriangle } from 'lucide-react'
import { api, ApiError } from '@/lib/api'

const RANKS = ['SI', 'INSPECTOR', 'ACP', 'DCP', 'SP', 'SSP', 'DIG']
const SENIOR = new Set(['SP', 'SSP', 'DIG'])

export default function WarrantGateModal({
  scope, onClose, onGranted,
}: {
  scope: string
  onClose: () => void
  onGranted: (warrantId: string) => void
}) {
  const [reqId, setReqId] = useState('io.sharma')
  const [reqRole, setReqRole] = useState('INSPECTOR')
  const [reason, setReason] = useState('victim identity required for chargesheet')
  const [warrantId, setWarrantId] = useState<string | null>(null)
  const [apId, setApId] = useState('sp.rao')
  const [apRole, setApRole] = useState('SP')
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState<string | null>(null)

  async function request() {
    setBusy(true); setErr(null)
    try {
      const out = await api.requestWarrant({ scope, requester_id: reqId.trim(), requester_role: reqRole, reason: reason.trim() })
      setWarrantId(out.warrant_id ?? null)
    } catch (e) {
      setErr(e instanceof ApiError ? e.message : 'request failed')
    } finally { setBusy(false) }
  }

  async function approve() {
    if (!warrantId) return
    setBusy(true); setErr(null)
    try {
      const out = await api.approveWarrant(warrantId, { approver_id: apId.trim(), approver_role: apRole })
      if (out.ok) onGranted(warrantId)
      else setErr(out.error ?? 'approval denied')
    } catch (e) {
      setErr(e instanceof ApiError ? e.message : 'approval failed')
    } finally { setBusy(false) }
  }

  const inputCls = 'w-full rounded-md border border-slate-700/50 bg-slate-900/60 px-2.5 py-1.5 text-xs text-slate-100 outline-none focus:border-cyan-400/40'
  const labelCls = 'mb-1 block font-mono text-[9px] uppercase tracking-wider text-slate-500'

  return (
    <div className="absolute inset-0 z-50 flex items-center justify-center bg-black/60 p-4 backdrop-blur-sm" onClick={onClose}>
      <div className="w-full max-w-md rounded-xl border border-white/10 bg-[#0a0f1c] p-5 shadow-2xl"
           onClick={(e) => e.stopPropagation()}>
        <div className="mb-4 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <ShieldCheck size={15} className="text-purple-400" />
            <h2 className="font-mono text-[11px] uppercase tracking-[0.25em] text-slate-300">Warrant gate</h2>
          </div>
          <button onClick={onClose} className="text-slate-500 hover:text-slate-200"><X size={16} /></button>
        </div>

        <p className="mb-4 font-mono text-[9px] leading-relaxed text-slate-500">
          Protected-party access needs a scoped, expiring warrant — requested by the IO,
          countersigned by a senior officer (four-eyes). Every step is ledgered. Scope:{' '}
          <span className="text-slate-300">{scope}</span>
        </p>

        {/* step 1 — request */}
        <div className={`space-y-3 rounded-lg border p-3 ${warrantId ? 'border-emerald-400/20 opacity-60' : 'border-white/10'}`}>
          <p className="font-mono text-[9px] uppercase tracking-wider text-slate-400">
            1 · Investigating officer {warrantId ? `— requested (${warrantId})` : ''}
          </p>
          <div className="grid grid-cols-2 gap-2">
            <label className="block">
              <span className={labelCls}>Officer ID</span>
              <input value={reqId} onChange={(e) => setReqId(e.target.value)} disabled={!!warrantId} className={inputCls} />
            </label>
            <label className="block">
              <span className={labelCls}>Rank</span>
              <select value={reqRole} onChange={(e) => setReqRole(e.target.value)} disabled={!!warrantId} className={inputCls}>
                {RANKS.map((r) => <option key={r} value={r}>{r}</option>)}
              </select>
            </label>
          </div>
          <label className="block">
            <span className={labelCls}>Reason</span>
            <input value={reason} onChange={(e) => setReason(e.target.value)} disabled={!!warrantId} className={inputCls} />
          </label>
          {!warrantId && (
            <button onClick={request} disabled={busy || !reqId.trim() || !reason.trim()}
                    className="flex w-full items-center justify-center gap-2 rounded-lg bg-purple-500/15 py-2 text-xs font-semibold text-purple-300 hover:bg-purple-500/25 disabled:opacity-40">
              {busy ? <Loader2 size={13} className="animate-spin" /> : <Stamp size={13} />}
              Request warrant
            </button>
          )}
        </div>

        {/* step 2 — countersign */}
        {warrantId && (
          <div className="mt-3 space-y-3 rounded-lg border border-white/10 p-3">
            <p className="font-mono text-[9px] uppercase tracking-wider text-slate-400">
              2 · Senior countersignature (SP+, different officer)
            </p>
            <div className="grid grid-cols-2 gap-2">
              <label className="block">
                <span className={labelCls}>Senior officer ID</span>
                <input value={apId} onChange={(e) => setApId(e.target.value)} className={inputCls} />
              </label>
              <label className="block">
                <span className={labelCls}>Rank</span>
                <select value={apRole} onChange={(e) => setApRole(e.target.value)} className={inputCls}>
                  {[...SENIOR].map((r) => <option key={r} value={r}>{r}</option>)}
                </select>
              </label>
            </div>
            <button onClick={approve} disabled={busy || !apId.trim()}
                    className="flex w-full items-center justify-center gap-2 rounded-lg bg-emerald-500/15 py-2 text-xs font-semibold text-emerald-300 hover:bg-emerald-500/25 disabled:opacity-40">
              {busy ? <Loader2 size={13} className="animate-spin" /> : <ShieldCheck size={13} />}
              Countersign &amp; unmask
            </button>
          </div>
        )}

        {err && (
          <p className="mt-3 flex items-center gap-1.5 font-mono text-[10px] text-red-400">
            <AlertTriangle size={11} /> {err}
          </p>
        )}
      </div>
    </div>
  )
}
