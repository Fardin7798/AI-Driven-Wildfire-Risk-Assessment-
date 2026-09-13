import { ShieldCheck, Flame, Wind, GraduationCap, PhoneCall } from 'lucide-react'

export function Footer() {
  return (
    <footer className="mt-12 border-t border-zinc-800/80 bg-zinc-950/90 pt-10 pb-16 text-zinc-400">
      <div className="mx-auto max-w-[1500px] px-4 sm:px-6 lg:px-8 space-y-8">
        <div className="grid grid-cols-1 gap-8 md:grid-cols-2 lg:grid-cols-4 border-b border-zinc-800/60 pb-8 text-xs">
          {/* Column 1: Academic & Engineering Credentials */}
          <div className="space-y-3">
            <div className="flex items-center gap-2 text-white font-bold text-sm">
              <GraduationCap className="h-4 w-4 text-cyan-400" />
              <span>Academic Engineering Thesis</span>
            </div>
            <p className="text-zinc-400 leading-relaxed">
              Bachelor of Engineering (B.E.) Capstone Platform
              <br />
              <strong className="text-zinc-200">Dept. of Computer Science & Engineering</strong>
            </p>
            <p className="text-zinc-500 font-mono text-[11px] leading-normal">
              Shri Sant Gadge Baba College of Engg. & Technology, Bhusawal
              <br />
              Dr. Babasaheb Ambedkar Technological University (Dr. BATU Lonere)
            </p>
          </div>

          {/* Column 2: Scientific Standards & Formulations */}
          <div className="space-y-3">
            <div className="flex items-center gap-2 text-white font-bold text-sm">
              <Flame className="h-4 w-4 text-amber-400" />
              <span>Scientific Methodologies</span>
            </div>
            <ul className="space-y-1.5 font-mono text-[11px] text-zinc-400">
              <li className="flex items-center gap-1.5">
                <i className="h-1.5 w-1.5 rounded-full bg-cyan-400" />
                <span>Canadian FWI System (Van Wagner 1987)</span>
              </li>
              <li className="flex items-center gap-1.5">
                <i className="h-1.5 w-1.5 rounded-full bg-orange-400" />
                <span>NASA LANCE FIRMS (Suomi-NPP VIIRS 375m)</span>
              </li>
              <li className="flex items-center gap-1.5">
                <i className="h-1.5 w-1.5 rounded-full bg-blue-400" />
                <span>Copernicus CAMS Chemical Transport</span>
              </li>
              <li className="flex items-center gap-1.5">
                <i className="h-1.5 w-1.5 rounded-full bg-emerald-400" />
                <span>CPCB National AQI Standard (2014)</span>
              </li>
            </ul>
          </div>

          {/* Column 3: Platform Invariants & Coverage */}
          <div className="space-y-3">
            <div className="flex items-center gap-2 text-white font-bold text-sm">
              <Wind className="h-4 w-4 text-emerald-400" />
              <span>Surveillance Grid</span>
            </div>
            <div className="space-y-1.5 text-zinc-400 text-[11px]">
              <p>Coverage: <span className="font-mono text-zinc-200">39 Key Vulnerable Eco-Districts</span></p>
              <p>Spatial Engine: <span className="font-mono text-zinc-200">PostGIS Geodetic Polygons</span></p>
              <p>Sync Cadence: <span className="font-mono text-zinc-200">Hourly Atmospheric & Orbital Sweep</span></p>
              <p>Hotspot Detection: <span className="font-mono text-zinc-200">Near-Real-Time (NRT) 50km Buffer</span></p>
            </div>
          </div>

          {/* Column 4: Civil Defense & Helplines */}
          <div className="space-y-3">
            <div className="flex items-center gap-2 text-white font-bold text-sm">
              <PhoneCall className="h-4 w-4 text-rose-400" />
              <span>Emergency Directives</span>
            </div>
            <div className="rounded-xl border border-red-500/20 bg-red-950/20 p-3 space-y-1">
              <p className="text-[11px] text-zinc-300">National Emergency: <strong className="text-red-400 font-mono font-bold text-xs">112</strong></p>
              <p className="text-[11px] text-zinc-300">NDMA Disaster Line: <strong className="text-amber-400 font-mono font-bold text-xs">1078</strong></p>
              <p className="text-[10px] text-zinc-500 pt-1">Direct telephonic link for rapid emergency civil mobilization.</p>
            </div>
          </div>
        </div>

        {/* Bottom Disclaimer & Copyright */}
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between text-[11px] text-zinc-500">
          <p className="flex items-center gap-1.5">
            <ShieldCheck className="h-3.5 w-3.5 text-cyan-400" />
            <span>AERORISK INDIA — Official Environmental Risk & Preparedness Research Framework. Verified Telemetry.</span>
          </p>
          <div className="flex items-center gap-4 font-mono text-[10px]">
            <span>REPUBLIC OF INDIA JURISDICTION</span>
            <span>•</span>
            <span>ISO/IEC COMPLIANT ARCHITECTURE</span>
          </div>
        </div>
      </div>
    </footer>
  )
}
