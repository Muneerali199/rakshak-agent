import { useState } from 'react'
import { Languages, Loader2, RefreshCcw } from 'lucide-react'
import { api, type HindiProfileResponse } from '@/lib/api'

const SAMPLE_EN = `SUNITA DEVI, daughter of Rajesh Kumar, wife of Ramesh Kumar.
Address: S-12 Gali, Karol Bagh, New Delhi 110005.
Phone: +91-8044997278. Account: AC7234309805.
Vehicle: UP78 GC 4978. Complaint under IPC 354D, recorded at Delhi PS Karol Bagh.`

// Judge-facing identity-resolution → Hindi-dossier demo: upload English
// profile text, get the complete profile back in Devanagari. Offline.
export default function HindiProfilePanel() {
  const [text, setText] = useState(SAMPLE_EN)
  const [res, setRes] = useState<HindiProfileResponse | null>(null)
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState<string | null>(null)

  async function run() {
    if (text.trim().length < 4) { setErr('paste an English profile first'); return }
    setBusy(true); setErr(null)
    try { setRes(await api.hindiProfile({ text })) }
    catch (e) { setErr(e instanceof Error ? e.message : 'hindi profile failed') }
    finally { setBusy(false) }
  }

  return (
    <div className="rounded-lg border border-fuchsia-400/20 bg-fuchsia-500/[0.04] p-3 backdrop-blur-md">
      <div className="mb-2 flex items-center gap-1.5">
        <Languages size={12} className="text-fuchsia-300" />
        <h3 className="font-mono text-[10px] uppercase tracking-[0.25em] text-slate-400">
          Identity → हिंदी profile
        </h3>
        <button onClick={(e) => { setText(SAMPLE_EN); setRes(null); setErr(null); (e.currentTarget as HTMLButtonElement).blur() }}
                className="ml-auto rounded p-0.5 text-slate-600 hover:text-fuchsia-300" title="reset sample">
          <RefreshCcw size={10} />
        </button>
      </div>
      <textarea
        value={text}
        onChange={(e) => setText(e.target.value)}
        rows={5}
        spellCheck={false}
        placeholder="Paste an English identity profile (names, address, phone, account, vehicle, IPC section)…"
        className="w-full resize-y rounded border border-fuchsia-400/20 bg-slate-900/60 px-2 py-1.5 font-mono text-[10px] leading-relaxed text-slate-200 outline-none placeholder:text-slate-600 focus:border-fuchsia-400/50"
      />
      <div className="mt-2 flex items-center gap-2">
        <button onClick={run} disabled={busy}
                className="flex items-center gap-1 rounded bg-fuchsia-500/15 px-2.5 py-1 font-mono text-[10px] text-fuchsia-200 transition-colors hover:bg-fuchsia-500/25 disabled:opacity-40">
          {busy ? <Loader2 size={10} className="animate-spin" /> : <Languages size={10} />}
          {busy ? 'translating…' : 'Translate → हिंदी'}
        </button>
        {res && (
          <span className="ml-auto font-mono text-[8px] text-slate-600">{res.engine}</span>
        )}
      </div>

      {err && <p className="mt-1.5 font-mono text-[8px] text-red-400">{err}</p>}

      {res && (
        <div className="mt-3 space-y-2">
          <div className="rounded border border-fuchsia-400/20 bg-slate-950/60 p-2.5">
            <div className="mb-1 font-mono text-[8px] uppercase tracking-[0.25em] text-fuchsia-400/70">
              हिंदी प्रोफ़ाइल
            </div>
            <p className="font-mono text-[11px] leading-relaxed text-slate-100">{res.paragraph}</p>
          </div>
          <ul className="space-y-1">
            {res.items.map((it) => (
              <li key={it.field ?? it.label}
                  className="grid grid-cols-[86px_1fr_1fr] items-start gap-1.5 rounded border border-white/5 bg-white/[0.02] px-2 py-1">
                <span className="font-mono text-[7px] uppercase tracking-wider text-slate-600">{it.label}</span>
                <span className="truncate font-mono text-[9px] text-slate-400" title={it.original}>{it.original}</span>
                <span className="truncate font-mono text-[9px] text-fuchsia-200" title={it.hindi}>{it.hindi}</span>
              </li>
            ))}
          </ul>
          <p className="flex items-start gap-1 font-mono text-[8px] leading-relaxed text-slate-500">
            <RefreshCcw size={8} className="mt-0.5 shrink-0 text-fuchsia-400/60" />
            {res.disclosure}
          </p>
        </div>
      )}
    </div>
  )
}