import { NavLink } from "react-router-dom"

export function Nav() {
  const linkClass = ({ isActive }: { isActive: boolean }) =>
    `flex items-center gap-2 rounded-xl px-3 py-2 text-xs font-semibold transition-all ${
      isActive
        ? "bg-cyan-500/10 text-cyan-400 border border-cyan-500/20 shadow-sm shadow-cyan-500/10"
        : "text-zinc-400 hover:bg-zinc-900 hover:text-zinc-200"
    }`

  return (
    <nav className="flex h-full flex-col border-r border-zinc-800/80 bg-zinc-950 p-4">
      <div className="mb-6 px-2">
        <div className="flex items-center gap-1.5">
          <span className="h-2 w-2 rounded-full bg-cyan-400 shadow-sm shadow-cyan-400"></span>
          <span className="font-mono text-[10px] font-bold tracking-widest text-cyan-400">
            AERORISK
          </span>
        </div>
        <h2 className="mt-1 text-sm font-bold text-white">India Ops Portal</h2>
        <p className="text-[11px] text-zinc-500">Live Environmental Defense</p>
      </div>

      <div className="flex flex-col gap-1.5">
        <NavLink to="/" end className={linkClass}>
          <span>❖</span>
          <span>Unified Bento</span>
        </NavLink>
        <a
          href="http://localhost:8000/docs"
          target="_blank"
          rel="noreferrer"
          className="flex items-center gap-2 rounded-xl px-3 py-2 text-xs font-semibold text-zinc-400 hover:bg-zinc-900 hover:text-zinc-200 transition-all"
        >
          <span>⚡</span>
          <span>Swagger /docs</span>
        </a>
      </div>

      <div className="mt-auto rounded-xl border border-zinc-800/60 bg-zinc-900/40 p-3 text-[11px] text-zinc-400">
        <p className="font-semibold text-zinc-300">National Emergency</p>
        <p className="mt-0.5 text-red-400 font-mono font-bold text-sm">Dial 112 / 101</p>
        <p className="mt-1 text-[10px] text-zinc-500">NDMA / State SDRF Active</p>
      </div>
    </nav>
  )
}
