import { Routes, Route } from 'react-router'
import SmoothScroll from './components/SmoothScroll'
import Home from './pages/Home'
import Workbench from './pages/Workbench'
import Scanner from './pages/Scanner'
import Report from './pages/Report'

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<SmoothScroll><Home /></SmoothScroll>} />
      <Route path="/workbench" element={<Workbench />} />
      <Route path="/scanner" element={<Scanner />} />
      <Route path="/report/:entityId" element={<Report />} />
    </Routes>
  )
}
