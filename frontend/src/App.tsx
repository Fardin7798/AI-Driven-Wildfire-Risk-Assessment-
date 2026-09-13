import { BrowserRouter, Routes, Route } from "react-router-dom"
import { Nav } from "./components/Nav"
import Home from "./pages/Home"

export default function App() {
  return (
    <BrowserRouter>
      <div className="flex min-h-screen bg-zinc-950 font-sans text-zinc-100">
        {/* Desktop Sidebar (z-index 20) */}
        <aside className="w-64 shrink-0 hidden md:block sticky top-0 h-screen z-20">
          <Nav />
        </aside>

        {/* Main Content Area */}
        <main className="flex-1 overflow-y-auto">
          <Routes>
            <Route path="/" element={<Home />} />
            <Route path="*" element={<Home />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  )
}
