import { BrowserRouter, Routes, Route } from "react-router-dom"
import { Nav } from "./components/Nav"
import Home from "./pages/Home"

export default function App() {
  return (
    <BrowserRouter>
      <div className="flex min-h-screen bg-zinc-950 text-zinc-100">
        <aside className="w-60 shrink-0 hidden md:block">
          <Nav />
        </aside>
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
