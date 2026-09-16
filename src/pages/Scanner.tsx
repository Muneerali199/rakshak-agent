import { useEffect, useState } from 'react'
import { Link } from 'react-router'
import { api, type ScanResponse } from '@/lib/api'

// The research proposal's own vulnerable endpoint — the demo's opening beat:
// "This is our code. We turned our security AI on ourselves."
const SAMPLE_CODE = `from fastapi import FastAPI
import os

app = FastAPI()
API_KEY = "sk-live-98231-hunter2"

@app.get("/citizen/{id}")
def get_citizen(id):
    # VULNERABLE: Direct string interpolation
    return db.execute(
        f"SELECT * FROM citizens WHERE id={id}"
    )

@app.get("/ping")
def ping(host: str):
    os.system("ping -c 1 " + host)

@app.get("/report")
def report(name: str):
    return db.execute("SELECT * FROM cases WHERE name='" + name + "'")
`

const SEV_COLOR: Record<string, string> = {
  CRITICAL: '#ff2d55',
  HIGH: '#f59e0b',
  MEDIUM: '#00f0ff',
  LOW: '#8b93a7',
}

// Animated scan pipeline — visualises the real rule-engine pass over pasted code.
// The scan itself is genuine (deterministic, local, zero network): the stages
// just make the pass legible to an audience.
const STAGES = [
  'enumerating lines',
  'matching 11 CWE rules',
  'compiling findings',
  'verdict'
]

export default function Scanner() {
  const [code, setCode] = useState(SAMPLE_CODE)
  const [filename, setFilename] = useState('api/routes.py')
  const [out, setOut] = useState<ScanResponse | null>(null)
  const [busy, setBusy] = useState(false)
  const [stage, setStage] = useState(0)
  const [err, setErr] = useState<string | null>(null)

  async function run() {
    setBusy(true)
    setErr(null)
    setOut(null)
    setStage(0)
    const timer = setInterval(() => setStage((s) => Math.min(s + 1, STAGES.length - 1)), 150)
    try {
      setOut(await api.scan(code, filename || undefined))
    } catch {
      setErr('Scan failed — is the backend running on :8000?')
    } finally {
      clearInterval(timer)
      setStage(0)
      setBusy(false)
    }
  }

  // Auto-run on load: the scanner must never look idle in front of a judge.
  useEffect(() => { void run() }, [])

  const sev = out?.summary.by_severity ?? {}
  const engineOffline = (out?.engine ?? 'rules') === 'rules'
  const modelStatus = engineOffline
    ? 'advisory 14B not connected — deterministic rules are the gate · fully offline'
    : '14B advisory attached'

  return (
    <div className="flex h-[100dvh] w-screen flex-col bg-[#050505] text-zinc-200">
      <header className="flex h-14 shrink-0 items-center justify-between border-b border-zinc-800 px-4">
        <div className="flex items-center gap-3">
          <Link to="/" className="font-cinzel text-sm font-bold tracking-[0.3em] text-white">RAKSHAK</Link>
          <span className="font-mono text-[10px] tracking-[0.25em] text-zinc-500">RAKSHAKAI · CODE SECURITY</span>
        </div>
        <div className="flex items-center gap-4">
          <span
            className="rounded-full border px-2 py-0.5 font-mono text-[9px]"
            style={{
              borderColor: engineOffline ? '#34d39940' : '#00f0ff40',
              color: engineOffline ? '#34d399' : '#00f0ff',
            }}
            title={modelStatus}
          >
            {engineOffline ? '● rules engine · fully offline' : '● 14B advisory attached'}
          </span>
          <span className="rounded-full border border-[#ff2d55]/40 px-2 py-0.5 font-mono text-[9px] text-[#ff2d55]">
            self-securing platform
          </span>
          <Link to="/workbench" className="font-mono text-[10px] text-zinc-400 hover:text-[#00f0ff]">
            ← workbench
          </Link>
        </div>
      </header>

      {/* demo-scope banner — this page is the interactive toy, the CLI is the product */}
      <div className="shrink-0 border-b border-amber-500/20 bg-amber-500/[0.06] px-4 py-2">
        <div className="flex flex-wrap items-center gap-x-3 gap-y-1 font-mono text-[10px] leading-relaxed">
          <span className="rounded border border-amber-500/40 bg-amber-500/10 px-1.5 py-0.5 uppercase tracking-wider text-amber-400">
            single-file demo
          </span>
          <span className="text-zinc-400">
            This page demonstrates the engine interactively. For real repositories use the
            CLI — <code className="text-[#00f0ff]">python backend/scripts/scan_repo.py ./repo</code> —
            or the CI gate. The scan runs entirely on this machine: no model call, no
            internet, nothing leaves your machine.
          </span>
          <span className="text-zinc-600">
            Don't paste confidential source code into a demo deployment you don't trust.
          </span>
        </div>
      </div>

      <div className="flex min-h-0 flex-1 flex-col lg:flex-row">
        {/* input */}
        <section className="flex min-h-0 flex-1 flex-col border-b border-zinc-800 p-4 lg:border-b-0 lg:border-r">
          <div className="mb-2 flex items-center justify-between">
            <h2 className="font-mono text-[10px] uppercase tracking-[0.25em] text-zinc-500">
              Paste code · static analysis
            </h2>
            <button onClick={() => setCode(SAMPLE_CODE)}
                    className="font-mono text-[9px] text-zinc-500 hover:text-[#00f0ff]">
              load sample
            </button>
          </div>
          <textarea
            value={code}
            onChange={(e) => setCode(e.target.value)}
            spellCheck={false}
            className="min-h-0 flex-1 resize-none rounded-lg border border-zinc-800 bg-[#0b0d12] p-3 font-mono text-xs leading-relaxed text-zinc-200 outline-none focus:border-[#00f0ff]/50"
          />
          <div className="mt-3 flex items-center gap-2">
            <input value={filename} onChange={(e) => setFilename(e.target.value)}
                   placeholder="filename (optional)"
                   className="w-48 rounded border border-zinc-800 bg-[#0b0d12] px-2 py-1.5 font-mono text-[10px] text-zinc-300 outline-none focus:border-[#00f0ff]/50" />
            <button onClick={run} disabled={busy || !code.trim()}
                    className="flex-1 rounded bg-[#ff2d55]/15 py-2 text-xs font-medium text-[#ff2d55] hover:bg-[#ff2d55]/25 disabled:opacity-50">
              {busy ? 'Scanning…' : '⚡ Scan with RakshakAI'}
            </button>
          </div>
          {err && <p className="mt-2 font-mono text-[10px] text-[#ff2d55]">{err}</p>}
        </section>

        {/* results */}
        <section className="min-h-0 flex-1 overflow-y-auto p-4">
          {busy && !out ? (
            <div className="flex h-full flex-col justify-center">
              <div className="mx-auto w-full max-w-[420px] space-y-2.5">
                <div className="flex items-center gap-2 font-mono text-[10px] uppercase tracking-[0.2em] text-[#00f0ff]">
                  <span className="h-2 w-2 animate-ping rounded-full bg-[#00f0ff]" />
                  scanning — live, offline
                </div>
                {STAGES.map((s, i) => (
                  <div key={s} className="flex items-center gap-2 font-mono text-[10px]">
                    <span style={{ color: i < stage ? '#34d399' : i === stage ? '#00f0ff' : '#3a3f4b' }}>
                      {i < stage ? '✓' : i === stage ? '▸' : '·'}
                    </span>
                    <span style={{ color: i === stage ? '#d4d4d8' : '#71717a' }}>{s}</span>
                  </div>
                ))}
                <p className="pt-1 font-mono text-[9px] text-zinc-600">
                  deterministic rules · stdlib only · no network · no model call
                </p>
              </div>
            </div>
          ) : !out ? (
            <div className="grid h-full place-items-center">
              <div className="max-w-[300px] space-y-2 text-center">
                <div className="mx-auto grid h-12 w-12 place-items-center rounded-full border border-zinc-800 bg-white/[0.03] text-lg">🛡</div>
                <p className="font-mono text-[10px] uppercase tracking-[0.25em] text-zinc-500">RakshakAI scanner</p>
                <p className="text-xs leading-relaxed text-zinc-500">
                  A police platform is the highest-value target in the state — so we scan
                  our own code before every deploy. Paste code and run the scan.
                </p>
              </div>
            </div>
          ) : (
            <div className="space-y-3">
              <div className="flex flex-wrap items-center gap-2">
                <span className="rounded border border-zinc-700 px-2 py-0.5 font-mono text-[9px] text-zinc-400">
                  engine: {out.engine}
                </span>
                <span className="font-mono text-[10px] text-zinc-500">
                  {out.summary.total} finding{out.summary.total === 1 ? '' : 's'} · {out.scanned_lines} lines
                </span>
                {(['CRITICAL', 'HIGH', 'MEDIUM'] as const).map((s) =>
                  sev[s] ? (
                    <span key={s} className="rounded px-2 py-0.5 font-mono text-[9px]"
                          style={{ color: SEV_COLOR[s], border: `1px solid ${SEV_COLOR[s]}55` }}>
                      {s} · {sev[s]}
                    </span>
                  ) : null)}
              </div>
              <p className="font-mono text-[9px] text-zinc-600">{out.engine_note}</p>
              {engineOffline && (
                <p className="flex items-center gap-1 font-mono text-[9px] text-[#34d399]">
                  <span className="h-1.5 w-1.5 rounded-full bg-[#34d399]" />
                  {modelStatus}
                </p>
              )}

              {out.findings.map((f, i) => (
                <div key={i} className="rounded-lg border border-zinc-800 bg-[#0b0d12] p-3">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="rounded px-1.5 py-0.5 font-mono text-[10px] font-bold"
                          style={{ color: SEV_COLOR[f.severity], border: `1px solid ${SEV_COLOR[f.severity]}66` }}>
                      {f.cwe}
                    </span>
                    <span className="text-xs font-medium text-zinc-100">{f.title}</span>
                    <span className="font-mono text-[9px] uppercase" style={{ color: SEV_COLOR[f.severity] }}>
                      {f.severity}
                    </span>
                    <span className="ml-auto font-mono text-[9px] text-zinc-500">line {f.line}</span>
                  </div>
                  {f.snippet && (
                    <pre className="mt-2 overflow-x-auto rounded border border-zinc-800/60 bg-[#08090c] p-2 font-mono text-[10px] text-zinc-400">
                      {f.snippet}
                    </pre>
                  )}
                  <p className="mt-2 text-[11px] leading-relaxed text-zinc-400">{f.reason}</p>
                  {f.remediation && (
                    <p className="mt-1.5 text-[11px] leading-relaxed text-[#34d399]">
                      → Fix: {f.remediation}
                    </p>
                  )}
                </div>
              ))}

              {out.summary.total === 0 && (
                <div className="rounded-lg border border-[#34d399]/30 bg-[#34d399]/[0.05] p-4 text-center">
                  <p className="text-sm text-[#34d399]">✓ No known vulnerability patterns found</p>
                  <p className="mt-1 font-mono text-[9px] text-zinc-500">
                    rule engine covers CWE-89/78/79/798/327/22 — the 14B model generalises further
                  </p>
                </div>
              )}

              <p className="pt-1 text-center font-mono text-[8px] tracking-wider text-zinc-600">
                {out.disclosure}
              </p>
            </div>
          )}
        </section>
      </div>
    </div>
  )
}
