import { NavLink } from "react-router-dom"
import { LayoutDashboard, Zap, ShieldAlert, Activity } from "lucide-react"
import { DOCS_URL } from "../lib/api"

export function Nav() {
  const linkClass = ({ isActive }: { isActive: boolean }) =>
    `flex items-center gap-2.5 rounded-xl px-3.5 py-2.5 text-xs font-semibold transition-all ${
      isActive
        ? "bg-cyan-500/10 text-cyan-400 border border-cyan-500/20 shadow-sm shadow-cyan-500/10"
        : "text-zinc-400 hover:bg-zinc-900/80 hover:text-zinc-200 border border-transparent"
    }`

  return (
    <nav className="flex h-full flex-col border-r border-zinc-800/80 bg-zinc-950/95 p-5 backdrop-blur-md">
      {/* Brand Header */}
      <div className="mb-6 px-1">
        <div className="flex items-center gap-2">
          <span className="relative flex h-2.5 w-2.5">
            <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-75"></span>
            <span className="relative inline-flex h-2.5 w-2.5 rounded-full bg-emerald-400"></span>
          </span>
          <span className="font-mono text-[11px] font-bold tracking-widest text-cyan-400">
            AERORISK
          </span>
          <span className="rounded bg-zinc-800 px-1.5 py-0.5 text-[9px] font-mono text-zinc-400">
            v1.0
          </span>
        </div>
        <h2 className="mt-2 text-sm font-bold text-white tracking-tight">India Ops Portal</h2>
        <p className="text-[11px] text-zinc-500">Live Environmental Defense</p>
      </div>

      {/* Navigation Links */}
      <div className="flex flex-col gap-1.5">
        <NavLink to="/" end className={linkClass}>
          <LayoutDashboard className="h-4 w-4" />
          <span>Unified Bento</span>
        </NavLink>
        <a
          href={DOCS_URL}
          target="_blank"
          rel="noreferrer"
          className="flex items-center gap-2.5 rounded-xl px-3.5 py-2.5 text-xs font-semibold text-zinc-400 hover:bg-zinc-900/80 hover:text-zinc-200 border border-transparent transition-all"
        >
          <Zap className="h-4 w-4 text-amber-400" />
          <span>Swagger /docs</span>
        </a>
      </div>

      {/* Telemetry Status Indicator */}
      <div className="mt-6 rounded-xl border border-zinc-800/60 bg-zinc-900/30 p-3">
        <div className="flex items-center gap-1.5 text-[10px] font-mono text-zinc-400">
          <Activity className="h-3 w-3 text-cyan-400" />
          <span>DATA FEEDS ACTIVE</span>
        </div>
        <div className="mt-2 space-y-1 text-[10px] text-zinc-500">
          <div className="flex justify-between">
            <span>NASA FIRMS VIIRS</span>
            <span className="text-emerald-400 font-mono">LIVE</span>
          </div>
          <div className="flex justify-between">
            <span>Copernicus CAMS</span>
            <span className="text-emerald-400 font-mono">72H SYNC</span>
          </div>
          <div className="flex justify-between">
            <span>Supabase PostGIS</span>
            <span className="text-cyan-400 font-mono">CONNECTED</span>
          </div>
          <div className="flex justify-between">
            <span>Open-Meteo High-Res</span>
            <span className="text-emerald-400 font-mono">0.05ms</span>
          </div>
        </div>
      </div>

      {/* National Emergency Speed-Dial Banner */}
      <div className="mt-auto rounded-xl border border-red-500/20 bg-red-950/20 p-3.5 text-xs">
        <div className="flex items-center gap-1.5 text-red-400 font-semibold">
          <ShieldAlert className="h-3.5 w-3.5 shrink-0" />
          <span>Emergency Support</span>
        </div>
        <p className="mt-1 text-red-300 font-mono font-bold text-sm tracking-wide">Dial 112 / 101</p>
        <p className="mt-0.5 text-[10px] text-zinc-400">NDMA National Helpline: 1078</p>
      </div>
    </nav>
  )
}
