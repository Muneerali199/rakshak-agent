// Aadhaar-verified officer session — client-side storage + React context.
// The token (from POST /api/auth/login) is bound to the verified officer; the
// backend derives identity/rank from it, so the client can never self-attest.
// Raw Aadhaar material never appears in the token payload — only masked views.
import { createContext, useContext, useState, type ReactNode } from 'react'

export type OfficerRole = 'IO' | 'FORENSIC' | 'SP'

export interface OfficerSessionView {
  id: string
  name: string
  badge: string
  role: OfficerRole
  role_label: string
  vault: string
  district: string
  police_station: string
  aadhaar_masked: string
}

export interface AuthResult {
  token: string
  expires_in: number
  officer: OfficerSessionView
  authentication: {
    bridge: string
    txn: string
    retcode: string
    consent_id: string
    verified_at: string
  }
  disclosure?: string
}

const STORAGE_KEY = 'rakshak.auth.session'

export function saveSession(result: AuthResult): void {
  sessionStorage.setItem(STORAGE_KEY, JSON.stringify(result))
}
export function loadSession(): AuthResult | null {
  try {
    const raw = sessionStorage.getItem(STORAGE_KEY)
    if (!raw) return null
    const parsed = JSON.parse(raw) as AuthResult
    if (!parsed?.token || !parsed?.officer) return null
    return parsed
  } catch {
    return null
  }
}
export function clearSession(): void {
  sessionStorage.removeItem(STORAGE_KEY)
}
export function token(): string | null {
  return loadSession()?.token ?? null
}

const AuthCtx = createContext<{
  session: AuthResult | null
  setSession: (s: AuthResult | null) => void
}>({ session: null, setSession: () => {} })

export function AuthProvider({ children }: { children: ReactNode }) {
  const [session, setSession] = useState<AuthResult | null>(() => loadSession())
  return <AuthCtx.Provider value={{ session, setSession }}>{children}</AuthCtx.Provider>
}

export function useAuth() {
  return useContext(AuthCtx)
}