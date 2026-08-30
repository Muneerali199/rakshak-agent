// Evidence Chain Report — the court-ready artifact.
// One entity, every connection, each row carrying its source record, live SHA-256
// verification, and review status; anomaly context; and the hash-chained ledger's
// integrity statement. This is the document an investigating officer can attach
// to a charge sheet. Print-friendly (Ctrl/Cmd-P).
import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router'
import {
  ShieldCheck, ShieldAlert, Fingerprint, ArrowLeft, Printer,
  CheckCircle2, AlertTriangle, Clock, FileText, EyeOff,
} from 'lucide-react'
import { api, type ReportResponse } from '@/lib/api'

export default function Report() {
  const { entityId = '' } = useParams()
  const [rep, setRep] = useState<ReportResponse | null>(null)
  const [err, setErr] = useState<string | null>(null)

  useEffect(() => {
    if (!entityId) return
    api.report(entityId).then(setRep).catch(() => setErr('Report unavailable — entity not found or API offline'))
  }, [entityId])

  if (err) {
    return (
      <div className="grid min-h-screen place-items-center bg-[#0a0f1c] p-6">
        <p className="flex items-center gap-2 font-mono text-xs text-red-400"><AlertTriangle size={14} /> {err}</p>
      </div>
    )
  }
  if (!rep) {
    return (
      <div className="grid min-h-screen place-items-center bg-[#0a0f1c] p-6">
        <p className="font-mono text-xs text-slate-500">compiling evidence chain…</p>
      </div>
    )
  }

  const verified = rep.rows.filter((r) => r.hash_verified).length

  return (
    <div className="min-h-screen bg-[#0a0f1c] text-slate-200 print:bg-white print:text-black">
      {/* toolbar (screen only) */}
      <div className="sticky top-0 z-10 flex items-center justify-between border-b border-white/5 bg-[#0a0f1c]/95 px-5 py-3 backdrop-blur-md print:hidden">
        <Link to="/workbench" className="flex items-center gap-1.5 font-mono text-[10px] text-slate-400 hover:text-cyan-400">
          <ArrowLeft size={12} /> workbench
        </Link>
        <button onClick={() => window.print()}
                className="flex items-center gap-1.5 rounded-md border border-cyan-400/40 bg-cyan-400/10 px-3 py-1.5 font-mono text-[10px] text-cyan-300 hover:bg-cyan-400/20">
          <Printer size={11} /> Print / export PDF
        </button>
      </div>

      <main className="mx-auto max-w-3xl px-6 py-8">
        {/* header block */}
        <header className="border-b border-slate-700/40 pb-5">
          <p className="font-mono text-[9px] uppercase tracking-[0.35em] text-slate-500">
            RAKSHAK-NET · Evidence Chain Report
          </p>
          <h1 className="mt-2 flex items-center gap-2 text-xl font-semibold text-white print:text-black">
            {rep.victim_shield
              ? <><ShieldAlert size={18} className="text-purple-400" /> {rep.label}</>
              : <><ShieldCheck size={18} className="text-cyan-400" /> {rep.label}</>}
          </h1>
          <div className="mt-2 flex flex-wrap items-center gap-x-4 gap-y-1 font-mono text-[10px] text-slate-500">
            <span>entity {rep.entity_id}</span>
            <span>type {rep.type}{rep.role ? ` · role ${rep.role}` : ''}</span>
            <span className="flex items-center gap-1"><Clock size={9} /> {rep.generated_at}</span>
          </div>
          {rep.victim_shield && (
            <p className="mt-3 rounded-md border border-purple-400/30 bg-purple-400/[0.06] px-3 py-2 text-[11px] text-purple-300">
              Protected party: identity pseudonymized under Women Safety Division policy.
              This report analyses the offender network only.
            </p>
          )}
        </header>

        {/* integrity summary */}
        <section className="mt-5 grid grid-cols-2 gap-3 sm:grid-cols-4">
          {[
            { label: 'Connections', value: rep.rows.length, icon: FileText },
            { label: 'Hash-verified', value: `${verified}/${rep.rows.length}`, icon: Fingerprint },
            {
              label: 'Ledger', value: rep.ledger.ok ? 'intact' : 'BROKEN', icon: rep.ledger.ok ? CheckCircle2 : AlertTriangle,
              tone: rep.ledger.ok ? '#34d399' : '#ef4444',
            },
            ...(rep.blindspot ? [{
              label: 'Corroboration', value: `${rep.blindspot.corroboration_score}/100`,
              icon: EyeOff,
              tone: rep.blindspot.corroboration_score >= 75 ? '#34d399'
                : rep.blindspot.corroboration_score >= 45 ? '#fbbf24' : '#ef4444',
            }] : []),
          ].map((s) => (
            <div key={s.label} className="rounded-lg border border-slate-700/50 bg-slate-900/40 p-3 print:border-slate-300">
              <div className="flex items-center gap-1.5 font-mono text-[8px] uppercase tracking-wider text-slate-500">
                <s.icon size={10} style={{ color: (s as { tone?: string }).tone }} /> {s.label}
              </div>
              <p className="mt-1 font-mono text-lg font-semibold text-white print:text-black">{s.value}</p>
            </div>
          ))}
        </section>

        {/* blindspots — honest statement of what the system does not know */}
        {rep.blindspot && rep.blindspot.gaps.length > 0 && (
          <section className="mt-6">
            <h2 className="font-mono text-[10px] uppercase tracking-[0.25em] text-amber-400">
              Blindspots — what this report cannot establish
            </h2>
            <ul className="mt-2 space-y-1.5">
              {rep.blindspot.gaps.map((g, i) => (
                <li key={i} className="rounded-md border border-amber-500/25 bg-amber-500/[0.05] px-3 py-2 text-xs text-slate-300">
                  {g}
                </li>
              ))}
            </ul>
          </section>
        )}

        {/* jurisdiction chain — signed mesh receipts behind cross-district links */}
        {rep.mesh_exchanges && rep.mesh_exchanges.length > 0 && (
          <section className="mt-6">
            <h2 className="font-mono text-[10px] uppercase tracking-[0.25em] text-cyan-400">
              Jurisdiction chain · {rep.mesh_exchanges.length} signed exchanges
            </h2>
            <p className="mt-1 font-mono text-[9px] text-slate-500">
              Cross-district links were established via signed vault-to-vault queries —
              data never left its district; each exchange is hash-chained on the mesh ledger.
            </p>
            <ul className="mt-2 space-y-1">
              {rep.mesh_exchanges.map((ex) => (
                <li key={ex.exchange_id}
                    className="flex items-center justify-between rounded border border-cyan-400/20 bg-cyan-400/[0.04] px-3 py-1.5 font-mono text-[9px] text-slate-400">
                  <span>
                    {ex.request_id} · {ex.origin_vault} →{' '}
                    {ex.receipts.map((r) => `${r.responder_vault} (${r.hits})`).join(' + ')}
                  </span>
                  <span title={ex.chain_hash}>⛓ {ex.chain_hash.slice(0, 12)}…</span>
                </li>
              ))}
            </ul>
          </section>
        )}

        {/* protected-data access log */}
        {rep.warrant_events && rep.warrant_events.length > 0 && (
          <section className="mt-6">
            <h2 className="font-mono text-[10px] uppercase tracking-[0.25em] text-purple-400">
              Protected-data access log · hash-chained
            </h2>
            <ul className="mt-2 space-y-1">
              {rep.warrant_events.map((w) => (
                <li key={w.id}
                    className="flex items-center justify-between rounded border border-purple-400/20 bg-purple-400/[0.04] px-3 py-1.5 font-mono text-[9px] text-slate-400">
                  <span>
                    {w.warrant_id} · {w.event} · {w.requester_id} ({w.requester_role})
                    {w.approver_id ? ` · countersigned ${w.approver_id} (${w.approver_role})` : ''}
                  </span>
                  <span title={w.chain_hash}>⛓ {w.chain_hash.slice(0, 12)}…</span>
                </li>
              ))}
            </ul>
          </section>
        )}

        {/* anomaly context */}
        {rep.anomalies.length > 0 && (
          <section className="mt-6">
            <h2 className="font-mono text-[10px] uppercase tracking-[0.25em] text-red-400">Anomaly context</h2>
            <ul className="mt-2 space-y-1.5">
              {rep.anomalies.map((a) => (
                <li key={a.id} className="rounded-md border border-red-500/25 bg-red-500/[0.05] px-3 py-2 text-xs text-slate-300">
                  <span className="font-mono text-[9px] uppercase text-red-400">{a.kind.replace(/_/g, ' ')}</span>
                  {' — '}{a.reason}
                </li>
              ))}
            </ul>
          </section>
        )}

        {/* the chain */}
        <section className="mt-6">
          <h2 className="font-mono text-[10px] uppercase tracking-[0.25em] text-slate-400">
            Evidence chain · {rep.rows.length} links
          </h2>
          <div className="mt-3 overflow-hidden rounded-lg border border-slate-700/50 print:border-slate-300">
            {rep.rows.map((r, i) => (
              <div key={r.edge_id}
                   className={`px-3.5 py-2.5 ${i > 0 ? 'border-t border-slate-800 print:border-slate-200' : ''}`}>
                <p className="text-xs leading-snug text-slate-200 print:text-black">{r.claim}</p>
                <div className="mt-1.5 flex flex-wrap items-center gap-x-3 gap-y-1 font-mono text-[8px] text-slate-500">
                  <span className="uppercase">{r.layer}</span>
                  <span>{r.creation_method === 'INFERRED' ? 'inferred' : 'observed'} · conf {r.confidence.toFixed(2)}</span>
                  {r.timestamp && <span>{r.timestamp}</span>}
                  <span>src {r.provenance.split(':').pop()}</span>
                  <span className={r.hash_verified ? 'text-emerald-400' : 'text-red-400'}>
                    {r.hash_verified ? '✓ hash' : '⚠ hash'}
                  </span>
                  <span className={
                    r.review_status === 'ACCEPTED' ? 'text-emerald-400'
                    : r.review_status === 'REJECTED' ? 'text-red-400' : 'text-amber-400'
                  }>
                    {r.review_status.toLowerCase()}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </section>

        {/* review history */}
        {rep.review_history.length > 0 && (
          <section className="mt-6">
            <h2 className="font-mono text-[10px] uppercase tracking-[0.25em] text-slate-400">
              Human review log · hash-chained
            </h2>
            <ul className="mt-2 space-y-1">
              {rep.review_history.map((r) => (
                <li key={r.id} className="flex items-center justify-between rounded border border-slate-800 px-3 py-1.5 font-mono text-[9px] text-slate-400 print:border-slate-200">
                  <span>#{r.id} {r.decision} · {r.edge_id} · {r.reviewer_id}</span>
                  <span title={r.chain_hash}>⛓ {r.chain_hash.slice(0, 12)}…</span>
                </li>
              ))}
            </ul>
          </section>
        )}

        <footer className="mt-8 border-t border-slate-700/40 pt-4">
          <p className="font-mono text-[8px] leading-relaxed text-slate-600">{rep.disclosure}</p>
        </footer>
      </main>
    </div>
  )
}
