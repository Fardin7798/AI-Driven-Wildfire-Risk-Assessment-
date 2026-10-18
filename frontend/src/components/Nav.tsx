import { NavLink } from "react-router-dom"
import { LayoutDashboard, ShieldAlert } from "lucide-react"

export function Nav() {
  const linkClass = ({ isActive }: { isActive: boolean }) =>
    `flex items-center gap-2.5 rounded-xl px-3.5 py-2.5 text-xs font-semibold transition-all ${
      isActive
        ? "bg-sky-50 text-sky-800 border border-sky-200 shadow-xs font-bold"
        : "text-slate-600 hover:bg-slate-50 hover:text-slate-900 border border-transparent"
    }`

  return (
    <nav className="flex h-full flex-col border-r border-slate-200 bg-white p-5 shadow-xs">
      {/* Brand Header */}
      <div className="mb-6 px-1">
        <div className="flex items-center gap-2">
          <span className="relative flex h-2.5 w-2.5">
            <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-75"></span>
            <span className="relative inline-flex h-2.5 w-2.5 rounded-full bg-emerald-600"></span>
          </span>
          <span className="font-mono text-[11px] font-bold tracking-widest text-sky-700">
            AERORISK
          </span>
        </div>
        <h2 className="mt-2 text-sm font-bold text-slate-900 tracking-tight">Wildfire & Air Quality</h2>
        <p className="text-[11px] text-slate-500">Check risk for your area</p>
      </div>

      {/* Navigation Links */}
      <div className="flex flex-col gap-1.5">
        <NavLink to="/" end className={linkClass}>
          <LayoutDashboard className="h-4 w-4 text-sky-600" />
          <span>Dashboard</span>
        </NavLink>
      </div>

      {/* National Emergency Speed-Dial Banner */}
      <div className="mt-auto rounded-xl border border-red-200 bg-red-50/80 p-3.5 text-xs">
        <div className="flex items-center gap-1.5 text-red-700 font-bold">
          <ShieldAlert className="h-3.5 w-3.5 shrink-0" />
          <span>Emergency Support</span>
        </div>
        <p className="mt-1 text-red-700 font-mono font-bold text-sm tracking-wide">Dial 112 / 101</p>
        <p className="mt-0.5 text-[10px] text-red-800">NDMA National Helpline: 1078</p>
      </div>
    </nav>
  )
}
