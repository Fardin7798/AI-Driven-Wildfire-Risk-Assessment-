import { BrowserRouter, Routes, Route, NavLink } from "react-router-dom"
import { LayoutDashboard, Zap } from "lucide-react"
import { Nav } from "./components/Nav"
import Home from "./pages/Home"
import Docs from "./pages/Docs"

export default function App() {
  return (
    <BrowserRouter>
      <div className="flex min-h-screen bg-zinc-950 font-sans text-zinc-100 pb-16 md:pb-0">
        {/* Desktop Sidebar */}
        <aside className="w-64 shrink-0 hidden md:block sticky top-0 h-screen z-20">
          <Nav />
        </aside>

        {/* Main Content Area */}
        <main className="flex-1 overflow-y-auto">
          <Routes>
            <Route path="/" element={<Home />} />
            <Route path="/docs" element={<Docs />} />
            <Route path="*" element={<Home />} />
          </Routes>
        </main>

        {/* Mobile Floating Bottom Navigation Bar (Bug #2 Fixed) */}
        <nav className="fixed bottom-0 left-0 right-0 z-40 flex md:hidden items-center justify-around border-t border-zinc-800/90 bg-zinc-950/90 backdrop-blur-xl px-4 py-2.5">
          <NavLink
            to="/"
            end
            className={({ isActive }) =>
              `flex flex-col items-center gap-1 text-[11px] font-semibold transition-all ${
                isActive ? "text-cyan-400" : "text-zinc-400 hover:text-zinc-200"
              }`
            }
          >
            <LayoutDashboard className="h-5 w-5" />
            <span>Dashboard</span>
          </NavLink>

          <NavLink
            to="/docs"
            className={({ isActive }) =>
              `flex flex-col items-center gap-1 text-[11px] font-semibold transition-all ${
                isActive ? "text-cyan-400" : "text-zinc-400 hover:text-zinc-200"
              }`
            }
          >
            <Zap className="h-5 w-5" />
            <span>API Docs</span>
          </NavLink>

          <div className="flex flex-col items-center gap-1 text-[10px] font-mono text-emerald-400">
            <span className="relative flex h-2 w-2 mt-1.5">
              <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-75"></span>
              <span className="relative inline-flex h-2 w-2 rounded-full bg-emerald-500"></span>
            </span>
            <span className="text-[9px] uppercase tracking-wider">Telemetry</span>
          </div>
        </nav>
      </div>
    </BrowserRouter>
  )
}
