import { Routes, Route } from 'react-router'
import SmoothScroll from './components/SmoothScroll'
import Home from './pages/Home'

export default function App() {
  return (
    <SmoothScroll>
      <Routes>
        <Route path="/" element={<Home />} />
      </Routes>
    </SmoothScroll>
  )
}
