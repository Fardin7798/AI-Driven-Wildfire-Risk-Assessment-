import { BrowserRouter, Routes, Route, NavLink } from "react-router-dom"
import { LayoutDashboard, PhoneCall } from "lucide-react"
import { Nav } from "./components/Nav"
import Home from "./pages/Home"

export default function App() {
  return (
    <BrowserRouter>
      <div className="flex min-h-screen bg-[#F8FAFC] font-sans text-slate-900 pb-16 md:pb-0">
        {/* Desktop Sidebar in Post 1 Solid White */}
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

        {/* Mobile Floating Bottom Navigation Bar (Post 1 Light Theme) */}
        <nav className="fixed bottom-0 left-0 right-0 z-40 flex md:hidden items-center justify-around border-t border-slate-200 bg-white/95 backdrop-blur-md px-4 py-2.5 shadow-sm">
          <NavLink
            to="/"
            end
            className={({ isActive }) =>
              `flex flex-col items-center gap-1 text-[11px] font-semibold transition-all ${
                isActive ? "text-sky-700 font-bold" : "text-slate-500 hover:text-slate-800"
              }`
            }
          >
            <LayoutDashboard className="h-5 w-5" />
            <span>Dashboard</span>
          </NavLink>


          <a
            href="tel:112"
            className="flex flex-col items-center gap-1 text-[11px] font-semibold text-red-600"
          >
            <PhoneCall className="h-5 w-5" />
            <span>Call 112</span>
          </a>
        </nav>
      </div>
    </BrowserRouter>
  )
}
