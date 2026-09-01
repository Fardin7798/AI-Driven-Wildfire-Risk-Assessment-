import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { Nav } from './components/Nav'
import Home from './pages/Home'
import RegionDetail from './pages/RegionDetail'
import PreparednessPage from './pages/Preparedness'

export default function App() {
  return (
    <BrowserRouter>
      <div className="flex min-h-screen">
        <aside className="w-56 shrink-0">
          <Nav />
        </aside>
        <main className="flex-1 overflow-y-auto">
          <Routes>
            <Route path="/" element={<Home />} />
            <Route path="/region/:id" element={<RegionDetail />} />
            <Route path="/preparedness" element={<PreparednessPage />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  )
}
