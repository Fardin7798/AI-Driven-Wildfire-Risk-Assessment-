import { ShieldCheck, Flame, Wind, GraduationCap, PhoneCall } from 'lucide-react'

export function Footer() {
  return (
    <footer className="mt-12 border-t border-slate-200 bg-slate-100/90 pt-10 pb-16 text-slate-600">
      <div className="mx-auto max-w-[1500px] px-4 sm:px-6 lg:px-8 space-y-8">
        <div className="grid grid-cols-1 gap-8 md:grid-cols-2 lg:grid-cols-4 border-b border-slate-200 pb-8 text-xs">
          {/* Column 1: Academic & Engineering Credentials */}
          <div className="space-y-3">
            <div className="flex items-center gap-2 text-slate-900 font-bold text-sm">
              <GraduationCap className="h-4 w-4 text-sky-600" />
              <span>Academic Engineering Thesis</span>
            </div>
            <p className="text-slate-600 leading-relaxed">
              Bachelor of Engineering (B.E.) Capstone Platform
              <br />
              <strong className="text-slate-900">Dept. of Computer Science & Engineering</strong>
            </p>
            <p className="text-slate-500 font-mono text-[11px] leading-normal">
              Shri Sant Gadge Baba College of Engg. & Technology, Bhusawal
              <br />
              Dr. Babasaheb Ambedkar Technological University (Dr. BATU Lonere)
            </p>
          </div>

          {/* Column 2: Scientific Standards & Formulations */}
          <div className="space-y-3">
            <div className="flex items-center gap-2 text-slate-900 font-bold text-sm">
              <Flame className="h-4 w-4 text-orange-600" />
              <span>Scientific Methodologies</span>
            </div>
            <ul className="space-y-1.5 font-mono text-[11px] text-slate-600">
              <li className="flex items-center gap-1.5">
                <i className="h-1.5 w-1.5 rounded-full bg-sky-600" />
                <span>Canadian FWI System (Van Wagner 1987)</span>
              </li>
              <li className="flex items-center gap-1.5">
                <i className="h-1.5 w-1.5 rounded-full bg-orange-600" />
                <span>NASA LANCE FIRMS (Suomi-NPP VIIRS 375m)</span>
              </li>
              <li className="flex items-center gap-1.5">
                <i className="h-1.5 w-1.5 rounded-full bg-blue-600" />
                <span>Copernicus CAMS Chemical Transport</span>
              </li>
              <li className="flex items-center gap-1.5">
                <i className="h-1.5 w-1.5 rounded-full bg-emerald-600" />
                <span>CPCB National AQI Standard (2014)</span>
              </li>
            </ul>
          </div>

          {/* Column 3: Platform Invariants & Coverage */}
          <div className="space-y-3">
            <div className="flex items-center gap-2 text-slate-900 font-bold text-sm">
              <Wind className="h-4 w-4 text-emerald-600" />
              <span>Surveillance Grid</span>
            </div>
            <div className="space-y-1.5 text-slate-600 text-[11px]">
              <p>Coverage: <span className="font-mono text-slate-900 font-semibold">39 Key Vulnerable Eco-Districts</span></p>
              <p>Spatial Engine: <span className="font-mono text-slate-900 font-semibold">PostGIS Geodetic Polygons</span></p>
              <p>Sync Cadence: <span className="font-mono text-slate-900 font-semibold">Hourly Atmospheric & Orbital Sweep</span></p>
              <p>Hotspot Detection: <span className="font-mono text-slate-900 font-semibold">Near-Real-Time (NRT) 50km Buffer</span></p>
            </div>
          </div>

          {/* Column 4: Civil Defense & Helplines */}
          <div className="space-y-3">
            <div className="flex items-center gap-2 text-slate-900 font-bold text-sm">
              <PhoneCall className="h-4 w-4 text-rose-600" />
              <span>Emergency Directives</span>
            </div>
            <div className="rounded-xl border border-red-200 bg-red-50/80 p-3 space-y-1">
              <p className="text-[11px] text-slate-700">National Emergency: <strong className="text-red-700 font-mono font-bold text-xs">112</strong></p>
              <p className="text-[11px] text-slate-700">NDMA Disaster Line: <strong className="text-amber-700 font-mono font-bold text-xs">1078</strong></p>
              <p className="text-[10px] text-slate-500 pt-1">Direct telephonic link for rapid emergency civil mobilization.</p>
            </div>
          </div>
        </div>

        {/* Bottom Disclaimer & Copyright */}
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between text-[11px] text-slate-500">
          <p className="flex items-center gap-1.5">
            <ShieldCheck className="h-3.5 w-3.5 text-sky-600" />
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
