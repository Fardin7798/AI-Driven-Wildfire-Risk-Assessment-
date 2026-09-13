import {
  AlertTriangle,
  ArrowUpRight,
  CloudRain,
  Droplets,
  Flame,
  Wind,
  Activity,
  ShieldCheck,
  Compass
} from 'lucide-react'
import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis
} from 'recharts'
import type {
  WildfireAssessment,
  WeatherData,
  AirQualityData,
  CommunityPreparedness
} from '../types'

export function Panel({
  title,
  eyebrow,
  children,
  className = '',
  action
}: {
  title: string
  eyebrow?: string
  children: React.ReactNode
  className?: string
  action?: React.ReactNode
}) {
  return (
    <section className={`rounded-2xl border border-white/[0.08] bg-[#111214] p-5 shadow-2xl shadow-black/10 backdrop-blur-md ${className}`}>
      <div className="mb-4 flex items-start justify-between">
        <div>
          <p className="font-mono text-[9px] uppercase tracking-[0.22em] text-zinc-500">{eyebrow}</p>
          <h2 className="mt-1 text-sm font-semibold tracking-tight text-zinc-100">{title}</h2>
        </div>
        {action}
      </div>
      {children}
    </section>
  )
}

// 1. Canadian FWI Risk Gauge
export function RiskGauge({ risk }: { risk: WildfireAssessment }) {
  const fwi = risk?.fwi_score ?? 0
  const percent = Math.min(Math.round((fwi / 50) * 100), 100)
  const conicColor = fwi >= 32 ? '#9333ea' : fwi >= 21 ? '#ef4444' : fwi >= 12 ? '#f97316' : fwi >= 5 ? '#eab308' : '#10b981'

  return (
    <Panel
      title="Canadian FWI Danger Rating"
      eyebrow="Composite Wildfire Potential // Physics Engine"
      action={
        <span className={`rounded-full px-2.5 py-0.5 text-xs font-bold uppercase tracking-wider border ${risk?.badge || 'bg-zinc-800 text-zinc-300'}`}>
          {risk?.risk_level || 'Unknown'}
        </span>
      }
      className="flex h-full flex-col justify-between"
    >
      <div className="flex flex-col items-center justify-center py-2">
        <div
          className="relative grid h-44 w-44 place-items-center rounded-full transition-all duration-700"
          style={{
            background: `conic-gradient(${conicColor} 0 ${percent}%, #27272a ${percent}% 100%)`
          }}
        >
          <div className="grid h-36 w-36 place-items-center rounded-full bg-[#111214]">
            <div className="text-center">
              <div className="tabular-nums font-mono text-5xl font-black text-white">
                {fwi}
              </div>
              <div className="mt-0.5 font-mono text-[10px] uppercase tracking-[0.2em] text-zinc-400">
                FWI Index
              </div>
            </div>
          </div>
        </div>

        <div className="mt-3 flex items-center gap-4 font-mono text-[9px] uppercase tracking-widest text-zinc-500">
          <span className="flex items-center gap-1.5"><i className="h-2 w-2 rounded-full bg-emerald-400" />0–5 Low</span>
          <span className="flex items-center gap-1.5"><i className="h-2 w-2 rounded-full bg-yellow-400" />5–12 Mod</span>
          <span className="flex items-center gap-1.5"><i className="h-2 w-2 rounded-full bg-orange-400" />12–21 High</span>
          <span className="flex items-center gap-1.5"><i className="h-2 w-2 rounded-full bg-red-500" />21+ Ext</span>
        </div>
      </div>

      {/* Scientific Sub-indices with plain-language hazard interpretations */}
      <div className="mt-3 grid grid-cols-2 gap-2">
        <div className="rounded-xl border border-white/[0.06] bg-black/20 p-2.5">
          <div className="flex items-center justify-between text-zinc-400 text-xs">
            <span className="text-[10px] uppercase font-mono">FFMC Fuel Dryness</span>
            <Activity className="h-3 w-3 text-cyan-400" />
          </div>
          <p className="mt-1 tabular-nums font-mono text-lg font-bold text-zinc-100">{risk?.ffmc ?? 0}</p>
          <p className="text-[9px] text-zinc-400 font-medium">
            {(risk?.ffmc ?? 0) >= 88 ? 'Combustible dry litter' : (risk?.ffmc ?? 0) >= 80 ? 'Moderate dry fuels' : 'Moist surface fuels'}
          </p>
        </div>
        <div className="rounded-xl border border-white/[0.06] bg-black/20 p-2.5">
          <div className="flex items-center justify-between text-zinc-400 text-xs">
            <span className="text-[10px] uppercase font-mono">ISI Spread Velocity</span>
            <Compass className="h-3 w-3 text-orange-400" />
          </div>
          <p className="mt-1 tabular-nums font-mono text-lg font-bold text-zinc-100">{risk?.isi ?? 0}</p>
          <p className="text-[9px] text-zinc-400 font-medium">
            {(risk?.isi ?? 0) >= 10 ? 'Rapid wind spread' : (risk?.isi ?? 0) >= 5 ? 'Moderate spread potential' : 'Slow ground propagation'}
          </p>
        </div>
      </div>

      {/* Proximity warning */}
      {risk?.closest_active_fire_km !== null && risk?.closest_active_fire_km !== undefined && (
        <div className="mt-3 flex items-center justify-between rounded-xl border border-orange-500/20 bg-orange-950/20 px-3 py-2 text-xs">
          <span className="flex items-center gap-1.5 text-orange-300">
            <AlertTriangle className="h-3.5 w-3.5 shrink-0" />
            Nearest NASA VIIRS Fire:
          </span>
          <span className="tabular-nums font-mono font-bold text-orange-400">
            {risk.closest_active_fire_km < 900 ? `${risk.closest_active_fire_km.toFixed(1)} km away` : 'No fire in 50km'}
          </span>
        </div>
      )}
    </Panel>
  )
}

// 2. Weather Telemetry Bar
export function WeatherBar({ weather }: { weather: WeatherData }) {
  const temp = weather?.temperature ?? 0
  const hum = weather?.humidity ?? 0
  const wind = weather?.wind_speed ?? 0
  const rain = weather?.precipitation ?? 0

  const values = [
    ['Surface Temp', temp.toString(), '°C', Flame, temp > 35 ? 'text-orange-400' : 'text-emerald-400', Math.min((temp / 50) * 100, 100)],
    ['Relative Humidity', hum.toString(), '%', Droplets, hum < 25 ? 'text-orange-400' : 'text-cyan-400', hum],
    ['Wind Velocity', wind.toString(), 'km/h', Wind, wind > 25 ? 'text-orange-400' : 'text-emerald-400', Math.min((wind / 50) * 100, 100)],
    ['24h Precipitation', rain.toString(), 'mm', CloudRain, 'text-blue-400', Math.min(rain * 10, 100)]
  ] as const

  return (
    <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
      {values.map(([label, value, unit, Icon, colorClass, barWidth]) => (
        <div key={label} className="rounded-2xl border border-white/[0.08] bg-[#111214] p-4 shadow-lg shadow-black/10">
          <div className="flex items-center justify-between">
            <span className="text-[10px] font-mono uppercase tracking-[0.16em] text-zinc-500">{label}</span>
            <Icon className={`h-4 w-4 ${colorClass}`} />
          </div>
          <div className="mt-4 font-mono text-2xl font-bold tabular-nums text-zinc-100">
            {value}
            <span className="ml-1 text-xs font-normal text-zinc-500">{unit}</span>
          </div>
          <div className="mt-3 h-1 w-full rounded-full bg-zinc-800">
            <div
              className="h-full rounded-full bg-cyan-400 transition-all duration-500"
              style={{ width: `${barWidth}%` }}
            />
          </div>
        </div>
      ))}
    </div>
  )
}

// 3. Air Quality Card
export function AirQuality({ aqi }: { aqi: AirQualityData }) {
  const aqiVal = aqi?.cpcb_aqi ?? 0
  const aqiPercentage = Math.min(Math.round((aqiVal / 500) * 100), 100)
  const p = aqi?.pollutants || { pm2_5: 0, pm10: 0, o3: 0, no2: 0, so2: 0, co: 0 }

  const pollutantsList = [
    ['PM2.5', p.pm2_5, 'µg/m³', Math.min((p.pm2_5 / 120) * 100, 100)],
    ['PM10', p.pm10, 'µg/m³', Math.min((p.pm10 / 200) * 100, 100)],
    ['Ozone (O3)', p.o3, 'µg/m³', Math.min((p.o3 / 100) * 100, 100)],
    ['NO2', p.no2, 'µg/m³', Math.min((p.no2 / 80) * 100, 100)],
    ['SO2', p.so2, 'µg/m³', Math.min((p.so2 / 80) * 100, 100)],
    ['CO', p.co, 'µg/m³', Math.min((p.co / 2000) * 100, 100)]
  ] as const

  return (
    <Panel
      title="CPCB National AQI"
      eyebrow="Atmospheric Telemetry // Copernicus CAMS"
      action={
        <span className={`rounded-full px-2.5 py-0.5 text-xs font-bold uppercase tracking-wider border ${aqi?.badge || 'bg-zinc-800 text-zinc-300'}`}>
          {aqi?.category || 'Unknown'}
        </span>
      }
      className="flex h-full flex-col justify-between"
    >
      <div>
        <div className="flex items-end gap-4">
          <div className="tabular-nums font-mono text-5xl font-black text-white" style={{ color: aqi?.color || '#38bdf8' }}>
            {aqiVal}
          </div>
          <div className="mb-1 text-xs text-zinc-500">
            CPCB NAQI Index
            <br />
            <span className="font-semibold text-zinc-300">{aqi?.category || 'Moderate'} Tier</span>
          </div>
        </div>

        <div className="mt-3">
          <div className="flex justify-between text-[9px] text-zinc-500 font-mono mb-1">
            <span>0 Good</span>
            <span>100 Mod</span>
            <span>250 Poor</span>
            <span>500 Severe</span>
          </div>
          <div className="h-1.5 w-full overflow-hidden rounded-full bg-zinc-800">
            <div
              className="h-full rounded-full transition-all duration-500"
              style={{
                width: `${aqiPercentage}%`,
                backgroundColor: aqi?.color || '#38bdf8'
              }}
            />
          </div>
        </div>

        <div className="mt-4 space-y-2">
          {pollutantsList.slice(0, 4).map(([name, val, unit, bar]) => (
            <div key={name} className="flex items-center gap-3">
              <span className="w-16 font-mono text-[10px] text-zinc-400">{name}</span>
              <div className="h-1.5 flex-1 rounded-full bg-zinc-800">
                <div
                  className="h-full rounded-full bg-cyan-400 transition-all duration-500"
                  style={{ width: `${bar}%` }}
                />
              </div>
              <span className="w-20 text-right font-mono text-[10px] tabular-nums text-zinc-200">
                {val} {unit}
              </span>
            </div>
          ))}
        </div>
      </div>

      <p className="mt-3 text-[10px] text-zinc-500">
        Supercomputer chemical transport modeling via Copernicus CAMS.
      </p>
    </Panel>
  )
}

// 4. Forecast Chart Card
export function ForecastChart({ forecast }: { forecast?: AirQualityData['forecast_72h'] }) {
  const safeList = forecast || []
  const data = safeList.slice(0, 48).map((pt) => ({
    time: pt?.time ? (pt.time.split('T')[1] || pt.time) : '--:--',
    aqi: pt?.aqi ?? 0,
    smoke: pt?.wildfire_smoke_pm10 ?? 0
  }))

  return (
    <Panel
      title="Copernicus CAMS 48-Hour Forecast"
      eyebrow="Hourly Chemical Trajectory // Wildfire Optical Depth"
      action={
        <div className="flex items-center gap-3 text-xs font-mono">
          <span className="flex items-center gap-1.5 text-cyan-400">
            <i className="h-2 w-2 rounded-full bg-cyan-400" /> NAQI Trend
          </span>
          <span className="flex items-center gap-1.5 text-orange-400">
            <i className="h-2 w-2 rounded-full bg-orange-400" /> Smoke PM10
          </span>
        </div>
      }
      className="flex h-full flex-col justify-between"
    >
      <div className="h-[220px] w-full mt-2">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={data} margin={{ top: 12, right: 10, left: -20, bottom: 0 }}>
            <defs>
              <linearGradient id="aqiGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#06b6d4" stopOpacity={0.4} />
                <stop offset="95%" stopColor="#06b6d4" stopOpacity={0} />
              </linearGradient>
              <linearGradient id="smokeGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#f97316" stopOpacity={0.5} />
                <stop offset="95%" stopColor="#f97316" stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid stroke="#27272a" strokeDasharray="2 4" vertical={false} />
            <XAxis dataKey="time" stroke="#71717a" fontSize={9} tickLine={false} axisLine={false} />
            <YAxis stroke="#71717a" fontSize={9} tickLine={false} axisLine={false} />
            <Tooltip
              contentStyle={{
                backgroundColor: '#18181b',
                borderColor: '#27272a',
                borderRadius: '0.75rem',
                fontSize: '11px',
                color: '#f4f4f5'
              }}
            />
            <Area type="monotone" dataKey="aqi" stroke="#06b6d4" strokeWidth={2} fillOpacity={1} fill="url(#aqiGrad)" />
            <Area type="monotone" dataKey="smoke" stroke="#f97316" strokeWidth={1.5} fillOpacity={1} fill="url(#smokeGrad)" />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </Panel>
  )
}

// 5. Emergency Speed-Dials & Community Directives
export function EmergencyCards({ prep }: { prep: CommunityPreparedness }) {
  const actions = prep?.recommended_actions || []
  const calls = [
    ['NDMA', '1078', 'Disaster helpline', 'bg-amber-400'],
    ['FIRE', '101', 'Fire response', 'bg-orange-500'],
    ['AMBULANCE', '108', 'Medical aid', 'bg-rose-500'],
    ['NATIONAL', '112', 'Unified emergency', 'bg-emerald-400']
  ] as const

  return (
    <Panel
      title="Actionable Preparedness & Emergency Directory"
      eyebrow="NDMA / SDRF Actionable Directives"
      action={
        <span
          className={`rounded-full px-2.5 py-0.5 text-xs font-bold uppercase tracking-wider border ${
            prep?.status === 'alert'
              ? 'bg-red-500/10 text-red-400 border-red-500/20'
              : 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20'
          }`}
        >
          {prep?.status === 'alert' ? 'Elevated Alert Active' : 'Normal Vigilance'}
        </span>
      }
    >
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-12">
        {/* Recommended Actions */}
        <div className="lg:col-span-8 space-y-2">
          <span className="text-[10px] font-mono font-semibold uppercase tracking-[0.18em] text-zinc-500">
            Target Health & Safety Protocols
          </span>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 mt-1">
            {actions.map((act, i) => (
              <div key={i} className="flex items-start gap-2.5 rounded-xl border border-white/[0.06] bg-black/20 p-2.5 text-xs text-zinc-200">
                <ShieldCheck className="h-4 w-4 text-cyan-400 shrink-0 mt-0.5" />
                <span>{act}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Speed-Dial Buttons */}
        <div className="lg:col-span-4">
          <span className="text-[10px] font-mono font-semibold uppercase tracking-[0.18em] text-zinc-500">
            Emergency Speed-Dials
          </span>
          <div className="grid grid-cols-2 gap-2 mt-1">
            {calls.map(([label, number, sub, dot]) => (
              <a
                href={`tel:${number}`}
                key={number}
                className="group rounded-xl border border-white/[0.06] bg-white/[0.02] p-2.5 transition hover:border-white/20 hover:bg-white/[0.05]"
              >
                <div className="flex items-center gap-1.5">
                  <i className={`h-2 w-2 rounded-full ${dot}`} />
                  <span className="font-mono text-[9px] tracking-widest text-zinc-400">{label}</span>
                </div>
                <div className="mt-2 flex items-center justify-between">
                  <span className="font-mono text-lg font-bold text-zinc-100">{number}</span>
                  <ArrowUpRight className="h-3.5 w-3.5 text-zinc-600 transition group-hover:text-zinc-200" />
                </div>
                <p className="mt-0.5 text-[9px] text-zinc-500 truncate">{sub}</p>
              </a>
            ))}
          </div>
        </div>
      </div>
    </Panel>
  )
}

// 6. State Badge Component
export function StateBadge({ state }: { state: 'empty' | 'loading' | 'error' | 'partial' | 'populated' }) {
  if (state === 'loading') return <span className="font-mono text-[10px] uppercase tracking-widest text-zinc-500">SYNCING TELEMETRY...</span>
  if (state === 'error') return <span className="inline-flex items-center gap-1.5 font-mono text-[10px] uppercase tracking-widest text-red-400"><AlertTriangle className="h-3 w-3" />DATA LINK DEGRADED</span>
  return (
    <span className="inline-flex items-center gap-2 font-mono text-[10px] uppercase tracking-widest text-emerald-400">
      <i className="h-2 w-2 animate-pulse rounded-full bg-emerald-400" />
      {state === 'partial' ? 'PARTIAL COVERAGE' : 'LIVE SYSTEMS ONLINE'}
    </span>
  )
}
