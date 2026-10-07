// Warrant Gate — the DEPA consent moment. Identity is the Aadhaar-verified
// session: the requester is whoever is signed in; countersignature runs under a
// *different* SP officer's verified session (four-eyes), fetched through the
// same e-KYC session. The backend rejects any client-claimed identity — it reads
// the bearer token — so these fields are read-only here.
import { useEffect, useMemo, useState } from 'react'
import { Loader2, ShieldCheck, Stamp, X, AlertTriangle } from 'lucide-react'
import { api, ApiError, type AuthOfficer } from '@/lib/api'
import { useAuth } from '@/lib/auth'

export default function WarrantGateModal({
  scope, onClose, onGranted,
}: {
  scope: string
  onClose: () => void
  onGranted: (warrantId: string) => void
}) {
  const { session } = useAuth()
  const officer = session?.officer

  const [reason, setReason] = useState('victim identity required for chargesheet')
  const [warrantId, setWarrantId] = useState<string | null>(null)
  const [approvers, setApprovers] = useState<AuthOfficer[]>([])
  const [approverId, setApproverId] = useState<string>('')
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState<string | null>(null)

  // SP candidates for countersignature, excluding the signed-in officer (four-eyes)
  useEffect(() => {
    api.authOfficers().then((all) => {
      const sps = all.filter((o) => o.role === 'SP' && o.id !== officer?.id)
      setApprovers(sps)
      setApproverId(sps[0]?.id ?? '')
    }).catch(() => setErr('could not load countersigning officers'))
  }, [officer?.id])

  const approver = useMemo(() => approvers.find((a) => a.id === approverId) ?? null, [approvers, approverId])

  async function request() {
    if (!officer) return
    setBusy(true); setErr(null)
    try {
      const out = await api.requestWarrant({
        scope, requester_id: officer.id, requester_role: officer.role, reason: reason.trim(),
      })
      setWarrantId(out.warrant_id ?? null)
    } catch (e) {
      setErr(e instanceof ApiError ? e.message : 'request failed')
    } finally { setBusy(false) }
  }

  async function approve() {
    if (!warrantId || !approver?.demo) return
    setBusy(true); setErr(null)
    try {
      // countersign under the SP officer's own verified e-KYC session (sim bridge)
      const spSession = await api.login(approver.demo.aadhaar, approver.demo.otp, 'warrant countersignature')
      const out = await api.approveWarrant(
        warrantId, { approver_id: approver.id, approver_role: approver.role }, spSession.token)
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
          Protected-party access needs a scoped, expiring warrant — requested by the signed-in IO,
          countersigned by a different SP officer (four-eyes), both Aadhaar-verified. Every step
          is ledgered. Scope: <span className="text-slate-300">{scope}</span>
        </p>

        {/* step 1 — request (identity = session) */}
        <div className={`space-y-3 rounded-lg border p-3 ${warrantId ? 'border-emerald-400/20 opacity-60' : 'border-white/10'}`}>
          <p className="font-mono text-[9px] uppercase tracking-wider text-slate-400">
            1 · Investigating officer {warrantId ? `— requested (${warrantId})` : ''}
          </p>
          <div className="rounded-md border border-white/10 bg-white/[0.03] px-2.5 py-2">
            <span className="font-mono text-[10px] text-emerald-300">✓ {officer?.name ?? '—'}</span>
            <span className="ml-2 font-mono text-[9px] text-slate-500">
              {officer?.badge} · {officer?.role} · {officer?.aadhaar_masked}
            </span>
          </div>
          <label className="block">
            <span className={labelCls}>Reason</span>
            <input value={reason} onChange={(e) => setReason(e.target.value)} disabled={!!warrantId} className={inputCls} />
          </label>
          {!warrantId && (
            <button onClick={request} disabled={busy || !reason.trim()}
                    className="flex w-full items-center justify-center gap-2 rounded-lg bg-purple-500/15 py-2 text-xs font-semibold text-purple-300 hover:bg-purple-500/25 disabled:opacity-40">
              {busy ? <Loader2 size={13} className="animate-spin" /> : <Stamp size={13} />}
              Request warrant as {officer?.name ?? 'signed-in officer'}
            </button>
          )}
        </div>

        {/* step 2 — countersignature (different SP officer session) */}
        {warrantId && (
          <div className="mt-3 space-y-3 rounded-lg border border-white/10 p-3">
            <p className="font-mono text-[9px] uppercase tracking-wider text-slate-400">
              2 · Senior countersignature (a different SP officer)
            </p>
            <label className="block">
              <span className={labelCls}>Countersigning SP (Aadhaar-verified)</span>
              <select value={approverId} onChange={(e) => setApproverId(e.target.value)} className={inputCls}>
                {approvers.map((a) => (
                  <option key={a.id} value={a.id}>{a.name} · {a.badge}</option>
                ))}
              </select>
            </label>
            <p className="font-mono text-[9px] leading-relaxed text-slate-600">
              The system establishes an SP session via the DigiLocker e-KYC bridge and signs
              with its token — the four-eyes moment, no client-claimed identity possible.
            </p>
            <button onClick={approve} disabled={busy || !approver}
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