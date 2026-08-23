import { Routes, Route } from 'react-router'
import SmoothScroll from './components/SmoothScroll'
import Home from './pages/Home'
import Workbench from './pages/Workbench'

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<SmoothScroll><Home /></SmoothScroll>} />
      <Route path="/workbench" element={<Workbench />} />
    </Routes>
  )
}
