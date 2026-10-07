import { Routes, Route, Navigate, useLocation } from 'react-router'
import { type ReactNode } from 'react'
import SmoothScroll from './components/SmoothScroll'
import Home from './pages/Home'
import Login from './pages/Login'
import Workbench from './pages/Workbench'
import Scanner from './pages/Scanner'
import Report from './pages/Report'
import { AuthProvider, useAuth } from './lib/auth'

// Aadhaar-verified gate: the investigator surfaces (workbench, scanner, evidence
// report) require an officer session; the public Home stays open (L1 reads are
// open by design, per the graded endpoint map).
function Protected({ children }: { children: ReactNode }) {
  const { session } = useAuth()
  const loc = useLocation()
  if (!session) {
    return <Navigate to="/login" replace state={{ from: loc.pathname }} />
  }
  return <>{children}</>
}

export default function App() {
  return (
    <AuthProvider>
      <Routes>
        <Route path="/" element={<SmoothScroll><Home /></SmoothScroll>} />
        <Route path="/login" element={<Login />} />
        <Route path="/workbench" element={<Protected><Workbench /></Protected>} />
        <Route path="/scanner" element={<Protected><Scanner /></Protected>} />
        <Route path="/report/:entityId" element={<Protected><Report /></Protected>} />
      </Routes>
    </AuthProvider>
  )
}