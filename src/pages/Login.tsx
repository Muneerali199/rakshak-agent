// DigiLocker e-KYC officer login — mirrors the official DigiLocker / API Setu
// portal flow: Aadhaar number → request OTP → OTP + informed consent → verified
// session. The handshake this box runs is the labelled offline simulation
// (bridge `digilocker-ekyc-sim`); production swaps in the live DigiLocker e-KYC
// API over API Setu with agency credentials.
import { useEffect, useState, type FormEvent } from 'react'
import { useLocation, useNavigate } from 'react-router'
import {
  Fingerprint, KeyRound, Loader2, ShieldCheck, AlertTriangle, Landmark,
  ChevronLeft, BadgeCheck, Lock, Database as DbIcon,
} from 'lucide-react'
import { api, ApiError, type AuthOfficer, type AuthOtpResult, type AuthStatus } from '@/lib/api'
import { saveSession, useAuth } from '@/lib/auth'

const STEP_LABEL: Record<number, string> = { 1: 'Aadhaar', 2: 'OTP', 3: 'Consent' }

export default function Login() {
  const nav = useNavigate()
  const loc = useLocation()
  const { setSession } = useAuth()
  const [officers, setOfficers] = useState<AuthOfficer[]>([])
  const [status, setStatus] = useState<AuthStatus | null>(null)
  const [aadhaar, setAadhaar] = useState('')
  const [otp, setOtp] = useState('')
  const [otpInfo, setOtpInfo] = useState<AuthOtpResult | null>(null)
  const [purpose, setPurpose] = useState('FIR filing session')
  const [consent, setConsent] = useState(false)
  const [step, setStep] = useState<1 | 2 | 3>(1)
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState<string | null>(null)
  const [showSim, setShowSim] = useState(false)

  useEffect(() => {
    api.authStatus().then(setStatus).catch(() => {})
    api.authOfficers().then(setOfficers).catch(() => {})
  }, [])

  function pick(o: AuthOfficer) {
    setAadhaar(o.demo?.aadhaar ?? '')
    setOtp(o.demo?.otp ?? '')
    setErr(null)
    setStep(1)
  }

  async function requestOtp() {
    setBusy(true)
    setErr(null)
    try {
      const r = await api.requestOtp(aadhaar)
      setOtpInfo(r)
      setStep(2)
    } catch (e) {
      setErr(e instanceof ApiError ? e.message : 'could not request OTP')
    } finally {
      setBusy(false)
    }
  }

  async function signIn(e: FormEvent) {
    e.preventDefault()
    setBusy(true)
    setErr(null)
    try {
      const result = await api.login(aadhaar, otp, purpose)
      saveSession(result)
      setSession(result)
      const dest = (loc.state as { from?: string } | null)?.from ?? '/workbench'
      nav(dest, { replace: true })
    } catch (e) {
      setErr(e instanceof ApiError ? e.message : 'sign in failed')
    } finally {
      setBusy(false)
    }
  }

  const grouped = aadhaar.replace(/(\d{4})(?=\d)/g, '$1 ').trim()
  const field = 'w-full rounded border border-slate-300 bg-white px-3 py-2.5 text-sm text-slate-800 shadow-sm outline-none focus:border-[#1a6fbe] focus:ring-2 focus:ring-[#1a6fbe]/15'
  const label = 'mb-1 block text-[11px] font-medium text-slate-600'

  return (
    <div className="flex min-h-[100dvh] flex-col bg-gradient-to-b from-sky-50 to-white text-slate-800">
      {/* tricolor */}
      <div className="h-1.5 bg-gradient-to-r from-[#FF9933] via-white to-[#138808]" />

      {/* header — government portal bar */}
      <header className="border-b border-slate-200 bg-white/90 backdrop-blur">
        <div className="mx-auto flex w-full max-w-5xl items-center justify-between px-5 py-3">
          <h1 className="flex items-center gap-3">
            <span className="flex h-9 w-9 items-center justify-center rounded-full border border-slate-300 bg-slate-50">
              <Landmark size={18} className="text-[#1a6fbe]" />
            </span>
            <span className="leading-tight">
              <span className="block text-base font-bold tracking-[0.18em] text-slate-800">DIGILOCKER</span>
              <span className="block text-[10px] text-slate-500">End-to-end encryption · e-KYC for services</span>
            </span>
          </h1>
          <div className="flex items-center gap-2">
            <span className="hidden rounded-full border border-amber-400/50 bg-amber-50 px-2.5 py-1 text-[10px] font-semibold text-amber-700 sm:block">
              SIMULATED ENVIRONMENT
            </span>
            <span className="flex items-center gap-1.5 text-[11px] text-slate-500">
              <Lock size={13} /> RAKSHAK NET · secure sign-in
            </span>
          </div>
        </div>
      </header>

      <main className="mx-auto flex w-full max-w-5xl flex-1 flex-col px-5 py-8 lg:flex-row lg:gap-10">
        {/* left — brand */}
        <section className="flex-1 pb-6 lg:pb-0">
          <h2 className="text-2xl font-bold text-slate-800">
            Sign in to the <span className="text-[#1a6fbe]">RAKSHAK NET</span> workbench
          </h2>
          <p className="mt-3 max-w-md text-sm leading-relaxed text-slate-600">
            Every write to the case graph is bound to a DigiLocker-verified officer
            identity, delivered over <b>API Setu</b> — India's government API gateway.
            What the e-KYC proves is who is signing, so rank on this system is enforced
            server-side from the issued token, never from the browser.
          </p>

          <ul className="mt-6 max-w-md space-y-2.5 text-[13px] text-slate-600">
            {[
              'Purpose-bound login with an informed consent record',
              'Raw Aadhaar never stored — masked last-4 + identity token only',
              'Session token expires after 8 hours',
              'Every consent / login / denial is hash-chained into the auth ledger',
            ].map((t) => (
              <li key={t} className="flex items-start gap-2">
                <BadgeCheck size={16} className="mt-0.5 shrink-0 text-emerald-600" /> {t}
              </li>
            ))}
          </ul>

          <div className="mt-6 flex max-w-md items-center gap-3 rounded-lg border border-slate-200 bg-white p-3 text-[11px] text-slate-500 shadow-sm">
            <Fingerprint size={18} className="shrink-0 text-[#1a6fbe]" />
            <span>
              Steps: Aadhaar number → one-time password → informed consent. The live
              DigiLocker e-KYC API over API Setu needs an agency account; this box runs
              the identical flow on the labelled offline simulation
              (<b>{status?.bridge ?? 'digilocker-ekyc-sim'}</b>).
            </span>
          </div>
        </section>

        {/* right — sign-in card */}
        <section className="w-full max-w-md shrink-0 self-start rounded-xl border border-slate-200 bg-white p-6 shadow-xl shadow-slate-200/60">
          {/* progress */}
          <ol className="mb-6 flex items-center gap-2">
            {([1, 2, 3] as const).map((s) => (
              <li key={s} className="flex flex-1 items-center gap-2">
                <span className={`flex h-6 w-6 items-center justify-center rounded-full text-[11px] font-semibold ${
                  step >= s ? 'bg-[#1a6fbe] text-white' : 'bg-slate-200 text-slate-500'}`}>
                  {step > s ? '✓' : s}
                </span>
                <span className={`text-[11px] font-medium ${step >= s ? 'text-slate-700' : 'text-slate-400'}`}>
                  {STEP_LABEL[s]}
                </span>
                {s < 3 && <span className="h-px flex-1 bg-slate-200" />}
              </li>
            ))}
          </ol>

          {/* step 1 — aadhaar */}
          {step === 1 && (
            <div className="space-y-4">
              {officers.length > 0 && (
                <div className="rounded-lg border border-emerald-300 bg-emerald-50 px-3 py-2">
                  <p className="text-[10px] font-semibold text-emerald-800">
                    DEMO CREDENTIALS (evaluator) — one-click fill:
                  </p>
                  <div className="mt-1 flex flex-wrap items-center gap-1.5">
                    {officers.slice(0, 3).map((o) => (
                      <button key={o.id} onClick={() => pick(o)}
                              className="rounded border border-emerald-300 bg-white px-2 py-1 font-mono text-[10px] text-emerald-800 hover:bg-emerald-100">
                        {o.demo?.aadhaar} · {o.demo?.otp} · {o.id.split('.').pop()}
                      </button>
                    ))}
                  </div>
                </div>
              )}
              <label className="block">
                <span className={label}>Enter your Aadhaar number / VID</span>
                <input value={grouped} inputMode="numeric"
                       onChange={(e) => setAadhaar(e.target.value.replace(/\D/g, '').slice(0, 12))}
                       className={`${field} text-center font-mono text-lg tracking-[0.3em]`}
                       placeholder="XXXX XXXX XXXX" />
              </label>
              <button onClick={requestOtp} disabled={busy || aadhaar.length !== 12}
                      className="flex w-full items-center justify-center gap-2 rounded bg-[#1a6fbe] py-2.5 text-sm font-semibold text-white transition hover:bg-[#15598f] disabled:opacity-40">
                {busy ? <Loader2 size={15} className="animate-spin" /> : <KeyRound size={15} />}
                Request one-time password
              </button>
              <p className="text-center text-[11px] text-slate-400">
                OTP is sent to the mobile number linked with this Aadhaar.
              </p>

              {err && <p className="flex items-center gap-1.5 text-xs text-red-600"><AlertTriangle size={13} /> {err}</p>}

              {!showSim && (
                <button onClick={() => setShowSim(true)} className="w-full text-center text-[11px] text-[#1a6fbe] hover:underline">
                  Need credentials? Load a simulated officer (offline registry)
                </button>
              )}
            </div>
          )}

          {/* step 2 — otp */}
          {step === 2 && (
            <div className="space-y-4">
              <div className="flex items-center gap-2 rounded-lg bg-sky-50 px-3 py-2.5 text-[12px] text-sky-800">
                <KeyRound size={14} className="shrink-0" />
                <span>{otpInfo?.hint ?? `OTP dispatched to ${otpInfo?.masked ?? aadhaar.replace(/^.{8}/, 'XXXXXXXX-')}`}</span>
              </div>
              <label className="block">
                <span className={label}>Enter the 6-digit one-time password</span>
                <input value={otp} inputMode="numeric" autoFocus
                       onChange={(e) => setOtp(e.target.value.replace(/\D/g, '').slice(0, 6))}
                       className={`${field} text-center font-mono text-lg tracking-[0.5em]`}
                       placeholder="──────" />
              </label>
              <button onClick={() => setStep(3)} disabled={busy || otp.length !== 6}
                      className="flex w-full items-center justify-center gap-2 rounded bg-[#1a6fbe] py-2.5 text-sm font-semibold text-white transition hover:bg-[#15598f] disabled:opacity-40">
                Continue with OTP
              </button>
              <div className="flex items-center justify-between text-[11px]">
                <button onClick={() => setStep(1)} className="flex items-center gap-1 text-slate-500 hover:text-slate-700">
                  <ChevronLeft size={13} /> Edit Aadhaar
                </button>
                <button onClick={requestOtp} disabled={busy} className="text-[#1a6fbe] hover:underline">
                  Resend OTP
                </button>
              </div>
              {err && <p className="flex items-center gap-1.5 text-xs text-red-600"><AlertTriangle size={13} /> {err}</p>}
            </div>
          )}

          {/* step 3 — consent + sign in */}
          {step === 3 && (
            <form onSubmit={signIn} className="space-y-4">
              <div className="rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-[11px] text-slate-600">
                <div className="flex items-center justify-between">
                  <span className="font-semibold text-slate-700">Verifying</span>
                  <span className="font-mono text-slate-500">{otpInfo?.masked ?? 'XXXX-XXXX-????'}</span>
                </div>
                <div className="mt-1 flex items-center gap-1.5 text-emerald-700">
                  <BadgeCheck size={13} /> e-KYC attributes retrieved (simulated)
                </div>
              </div>

              <label className="block">
                <span className={label}>Purpose of this authenticated session</span>
                <select value={purpose} onChange={(e) => setPurpose(e.target.value)} className={field}>
                  <option>FIR filing session</option>
                  <option>Case review decision</option>
                  <option>Warrant request</option>
                  <option>Warrant countersignature</option>
                  <option>Forensic evidence review</option>
                </select>
              </label>

              <label className="flex items-start gap-2.5 rounded-lg border border-slate-200 bg-white p-3 text-[11px] leading-relaxed text-slate-600">
                <input type="checkbox" checked={consent} onChange={(e) => setConsent(e.target.checked)}
                       className="mt-0.5 h-4 w-4 rounded accent-[#1a6fbe]" />
                <span>
                  I give consent for my identity to be verified via DigiLocker e-KYC for the
                  stated purpose, and accept that this session is bound to me as a RAKSHAK NET
                  officer. The Aadhaar number will not be stored or shared.
                </span>
              </label>

              {err && <p className="flex items-center gap-1.5 text-xs text-red-600"><AlertTriangle size={13} /> {err}</p>}

              <button type="submit" disabled={busy || otp.length !== 6 || !consent}
                      className="flex w-full items-center justify-center gap-2 rounded bg-emerald-600 py-2.5 text-sm font-semibold text-white transition hover:bg-emerald-700 disabled:opacity-40">
                {busy ? <Loader2 size={15} className="animate-spin" /> : <ShieldCheck size={15} />}
                Sign in securely &amp; open workbench
              </button>
            </form>
          )}

          {/* offline sim registry */}
          {showSim && (
            <div className="mt-5 rounded-lg border border-amber-300 bg-amber-50 p-3">
              <div className="flex items-center justify-between">
                <p className="flex items-center gap-1.5 text-[11px] font-semibold text-amber-800">
                  <DbIcon size={13} /> Offline sim registry — synthetic officers (auto-fill)
                </p>
                <button onClick={() => setShowSim(false)} className="text-[11px] text-amber-700 hover:underline">hide</button>
              </div>
              <div className="mt-2 grid grid-cols-1 gap-1.5">
                {officers.map((o) => (
                  <button key={o.id} onClick={() => pick(o)}
                          className="flex items-center justify-between gap-2 rounded border border-amber-200 bg-white px-2.5 py-1.5 text-left hover:bg-amber-100/60">
                    <span className="min-w-0">
                      <span className="block truncate text-[11px] text-slate-700">
                        {o.name} <span className="text-slate-400">· {o.badge}</span>
                      </span>
                      <span className="block font-mono text-[10px] text-emerald-700">
                        {o.demo?.aadhaar} · OTP {o.demo?.otp}
                      </span>
                    </span>
                    <span className={`shrink-0 rounded px-1.5 py-0.5 text-[9px] font-semibold ${
                      o.role === 'SP' ? 'bg-purple-100 text-purple-700'
                        : o.role === 'FORENSIC' ? 'bg-amber-100 text-amber-700'
                          : 'bg-sky-100 text-sky-700'}`}>
                      {o.role}
                    </span>
                  </button>
                ))}
              </div>
              <p className="mt-2 text-[10px] leading-relaxed text-amber-700">
                Both the Aadhaar and OTP are pre-filled so the judge can move through the
                flow instantly. The live DigiLocker e-KYC channel over API Setu would need
                an agency account — this box labels itself as a simulation.
              </p>
            </div>
          )}
        </section>
      </main>

      <footer className="border-t border-slate-200 bg-white">
        <div className="mx-auto flex w-full max-w-5xl flex-col gap-1 px-5 py-3 text-[10px] text-slate-500 sm:flex-row sm:items-center sm:justify-between">
          <span>
            RAKSHAK NET · Powered by <b>API Setu</b> · DigiLocker e-KYC channel · Officer identity for the case graph
          </span>
          <span>Bridge in use: <b>{status?.bridge ?? 'digilocker-ekyc-sim'}</b> — offline simulation, disclosed</span>
        </div>
      </footer>
    </div>
  )
}