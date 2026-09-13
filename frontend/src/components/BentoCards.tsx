import {
  AlertTriangle,
  ArrowUpRight,
  CloudRain,
  Droplets,
  Flame,
  Wind,
  Activity,
  ShieldCheck,
  Thermometer,
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
import { BentoGridItem } from './ui/BentoGrid'

// 1. Canadian FWI Risk Card (Post 1 Light Palette: Nordic Cool Slate & Sapphire)
export function RiskGaugeCard({ risk }: { risk: WildfireAssessment }) {
  const fwi = risk?.fwi_score ?? 0
  const percent = Math.min(Math.round((fwi / 50) * 100), 100)
  
  // Semantic spotlight color in light mode (subtle tint)
  const spotlightColor =
    fwi >= 32
      ? 'rgba(147, 51, 234, 0.08)'
      : fwi >= 21
      ? 'rgba(239, 68, 68, 0.08)'
      : fwi >= 12
      ? 'rgba(249, 115, 22, 0.08)'
      : fwi >= 5
      ? 'rgba(234, 179, 8, 0.08)'
      : 'rgba(16, 185, 129, 0.08)'

  const conicColor =
    fwi >= 32
      ? '#9333ea'
      : fwi >= 21
      ? '#dc2626'
      : fwi >= 12
      ? '#ea580c'
      : fwi >= 5
      ? '#d97706'
      : '#059669'

  const badgeStyle =
    fwi >= 21
      ? 'bg-red-50 text-red-700 border-red-200'
      : fwi >= 12
      ? 'bg-orange-50 text-orange-700 border-orange-200'
      : fwi >= 5
      ? 'bg-amber-50 text-amber-700 border-amber-200'
      : 'bg-emerald-50 text-emerald-700 border-emerald-200'

  return (
    <BentoGridItem
      className="lg:col-span-1"
      spotlightColor={spotlightColor}
      eyebrow="Canadian FWI // Physics Engine"
      action={
        <span
          className={`rounded-full px-2.5 py-0.5 text-[10px] font-bold uppercase tracking-wider border ${badgeStyle}`}
        >
          {risk?.risk_level || 'Unknown'}
        </span>
      }
      header={
        <div className="flex flex-col items-center justify-center py-2">
          <div
            className="relative grid h-40 w-40 place-items-center rounded-full transition-all duration-700 shadow-inner"
            style={{
              background: `conic-gradient(${conicColor} 0 ${percent}%, #f1f5f9 ${percent}% 100%)`,
            }}
          >
            <div className="grid h-32 w-32 place-items-center rounded-full bg-white shadow-sm border border-slate-100">
              <div className="text-center">
                <div className="tabular-nums font-mono text-4xl font-black text-slate-900">
                  {fwi}
                </div>
                <div className="mt-0.5 font-mono text-[9px] uppercase tracking-[0.2em] text-slate-500 font-semibold">
                  FWI Index
                </div>
              </div>
            </div>
          </div>

          <div className="mt-3 flex items-center gap-2 font-mono text-[9px] uppercase tracking-wider text-slate-600">
            <span className="flex items-center gap-1 bg-emerald-50 text-emerald-700 border border-emerald-200 px-1.5 py-0.5 rounded font-semibold"><i className="h-1.5 w-1.5 rounded-full bg-emerald-600" />0–5 Low</span>
            <span className="flex items-center gap-1 bg-amber-50 text-amber-700 border border-amber-200 px-1.5 py-0.5 rounded font-semibold"><i className="h-1.5 w-1.5 rounded-full bg-amber-600" />5–12 Mod</span>
            <span className="flex items-center gap-1 bg-orange-50 text-orange-700 border border-orange-200 px-1.5 py-0.5 rounded font-semibold"><i className="h-1.5 w-1.5 rounded-full bg-orange-600" />12–21 High</span>
            <span className="flex items-center gap-1 bg-red-50 text-red-700 border border-red-200 px-1.5 py-0.5 rounded font-semibold"><i className="h-1.5 w-1.5 rounded-full bg-red-600" />21+ Ext</span>
          </div>

          {/* Scientific Sub-indices */}
          <div className="mt-3 grid grid-cols-2 gap-2 w-full">
            <div className="rounded-xl border border-slate-200 bg-slate-50/70 p-2.5">
              <span className="font-mono text-[9px] uppercase tracking-wider text-slate-500 block font-semibold">FFMC (Fuel Dryness)</span>
              <div className="flex items-baseline justify-between mt-1">
                <span className="font-mono text-base font-bold text-slate-900">{risk?.ffmc ?? '--'}</span>
                <span className="text-[9px] text-amber-700 font-mono font-bold">
                  {(risk?.ffmc ?? 0) >= 88 ? 'High Dryness' : 'Equilibrium'}
                </span>
              </div>
            </div>
            <div className="rounded-xl border border-slate-200 bg-slate-50/70 p-2.5">
              <span className="font-mono text-[9px] uppercase tracking-wider text-slate-500 block font-semibold">ISI (Spread Rate)</span>
              <div className="flex items-baseline justify-between mt-1">
                <span className="font-mono text-base font-bold text-slate-900">{risk?.isi ?? '--'}</span>
                <span className="text-[9px] text-orange-700 font-mono font-bold">
                  {(risk?.isi ?? 0) >= 10 ? 'Rapid Spread' : 'Moderate'}
                </span>
              </div>
            </div>
          </div>
        </div>
      }
      icon={<Flame className="h-4 w-4 text-orange-600" />}
      title="Canadian Forest Fire Weather Index (FWI)"
      description="Van Wagner (1987) fire danger rating coupling fuel moisture equilibrium, wind spread velocity, and drought buildup."
    />
  )
}

// 2. Surface Atmospheric Telemetry Card (Post 1 Light Palette)
export function WeatherBarCard({ weather }: { weather: WeatherData }) {
  const items = [
    {
      label: 'Surface Temp',
      val: `${weather?.temperature !== undefined ? weather.temperature.toFixed(1) : '--'}°C`,
      sub: 'Dry-bulb 2m',
      icon: Thermometer,
      accent: 'text-amber-600',
    },
    {
      label: 'Relative Humidity',
      val: `${weather?.humidity !== undefined ? weather.humidity.toFixed(0) : '--'}%`,
      sub: 'Vapor saturation',
      icon: Droplets,
      accent: 'text-sky-600',
    },
    {
      label: '10m Wind Velocity',
      val: `${weather?.wind_speed !== undefined ? weather.wind_speed.toFixed(1) : '--'} km/h`,
      sub: 'Anemometer 10m',
      icon: Wind,
      accent: 'text-cyan-600',
    },
    {
      label: 'Precipitation',
      val: `${weather?.precipitation !== undefined ? weather.precipitation.toFixed(1) : '0.0'} mm`,
      sub: 'Surface wetting',
      icon: CloudRain,
      accent: 'text-indigo-600',
    },
  ]

  return (
    <BentoGridItem
      className="lg:col-span-3"
      spotlightColor="rgba(2, 132, 199, 0.05)"
      eyebrow="Surface Telemetry // Open-Meteo Synoptic Feed"
      action={
        <span className="font-mono text-[9px] uppercase tracking-wider text-emerald-700 bg-emerald-50 border border-emerald-200 px-2 py-0.5 rounded-full flex items-center gap-1.5 font-semibold">
          <i className="h-1.5 w-1.5 rounded-full bg-emerald-600 animate-pulse" />
          Live Observation
        </span>
      }
      header={
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 py-1">
          {items.map((it) => {
            const Icon = it.icon
            return (
              <div
                key={it.label}
                className="rounded-xl border border-slate-200 bg-slate-50/70 p-3.5 transition duration-200 hover:border-slate-300 hover:bg-slate-50"
              >
                <div className="flex items-center justify-between">
                  <span className="font-mono text-[9px] uppercase tracking-wider text-slate-500 font-semibold">
                    {it.label}
                  </span>
                  <Icon className={`h-4 w-4 ${it.accent}`} />
                </div>
                <div className="mt-2 font-mono text-2xl font-bold tracking-tight text-slate-900">
                  {it.val}
                </div>
                <div className="mt-1 font-mono text-[10px] text-slate-500">
                  {it.sub}
                </div>
              </div>
            )
          })}
        </div>
      }
      icon={<Wind className="h-4 w-4 text-sky-600" />}
      title="Surface Atmospheric Telemetry"
      description="Continuous observations calibrated for atmospheric boundary layer stability and fire fuel moisture equilibrium."
    />
  )
}

// 3. CPCB Air Quality Index Card (Post 1 Light Palette)
export function AirQualityCard({ aqi }: { aqi: AirQualityData }) {
  const aqiScore = aqi?.cpcb_aqi ?? 0
  const aqiPercentage = Math.min(Math.round((aqiScore / 500) * 100), 100)

  const spotlightColor =
    aqiScore > 200
      ? 'rgba(239, 68, 68, 0.08)'
      : aqiScore > 100
      ? 'rgba(234, 179, 8, 0.08)'
      : 'rgba(16, 185, 129, 0.08)'

  const badgeColorClass =
    aqiScore > 300
      ? 'bg-purple-50 text-purple-700 border-purple-200'
      : aqiScore > 200
      ? 'bg-red-50 text-red-700 border-red-200'
      : aqiScore > 100
      ? 'bg-orange-50 text-orange-700 border-orange-200'
      : aqiScore > 50
      ? 'bg-amber-50 text-amber-700 border-amber-200'
      : 'bg-emerald-50 text-emerald-700 border-emerald-200'

  const pollutants = aqi?.pollutants || ({} as AirQualityData['pollutants'])
  const pollutantsList = [
    ['PM2.5', pollutants.pm2_5 !== undefined ? pollutants.pm2_5.toFixed(1) : '--', 'µg/m³', Math.min(((pollutants.pm2_5 || 0) / 120) * 100, 100)],
    ['PM10', pollutants.pm10 !== undefined ? pollutants.pm10.toFixed(1) : '--', 'µg/m³', Math.min(((pollutants.pm10 || 0) / 250) * 100, 100)],
    ['NO2', pollutants.no2 !== undefined ? pollutants.no2.toFixed(1) : '--', 'µg/m³', Math.min(((pollutants.no2 || 0) / 180) * 100, 100)],
    ['O3', pollutants.o3 !== undefined ? pollutants.o3.toFixed(1) : '--', 'µg/m³', Math.min(((pollutants.o3 || 0) / 180) * 100, 100)],
  ] as const

  return (
    <BentoGridItem
      className="lg:col-span-1"
      spotlightColor={spotlightColor}
      eyebrow="Air Quality Index // CPCB Standard"
      action={
        <span
          className={`rounded-full px-2.5 py-0.5 text-[10px] font-bold uppercase tracking-wider border ${badgeColorClass}`}
        >
          {aqi?.category || 'Moderate'}
        </span>
      }
      header={
        <div className="py-2">
          <div className="flex items-baseline justify-between">
            <div>
              <span className="font-mono text-4xl font-black text-slate-900">
                {aqiScore}
              </span>
              <span className="ml-2 font-mono text-[10px] text-slate-500 uppercase tracking-widest font-semibold">
                CPCB NAQI
              </span>
            </div>
            <span className="font-mono text-xs font-semibold text-slate-600">
              Criteria Pollutants
            </span>
          </div>

          <div className="mt-3">
            <div className="flex justify-between text-[8px] text-slate-500 font-mono mb-1 font-semibold">
              <span>0 Good</span>
              <span>100 Mod</span>
              <span>250 Poor</span>
              <span>500 Sev</span>
            </div>
            <div className="h-2 w-full overflow-hidden rounded-full bg-slate-100 border border-slate-200/60">
              <div
                className="h-full rounded-full transition-all duration-500"
                style={{
                  width: `${aqiPercentage}%`,
                  backgroundColor: aqi?.color || '#0284c7',
                }}
              />
            </div>
          </div>

          <div className="mt-4 space-y-2">
            {pollutantsList.map(([name, val, unit, bar]) => (
              <div key={name} className="flex items-center gap-3">
                <span className="w-12 font-mono text-[10px] text-slate-600 font-semibold">{name}</span>
                <div className="h-1.5 flex-1 rounded-full bg-slate-100 overflow-hidden border border-slate-200/50">
                  <div
                    className="h-full rounded-full bg-sky-600 transition-all duration-500"
                    style={{ width: `${bar}%` }}
                  />
                </div>
                <span className="w-20 text-right font-mono text-[10px] tabular-nums text-slate-800 font-bold">
                  {val} {unit}
                </span>
              </div>
            ))}
          </div>
        </div>
      }
      icon={<Activity className="h-4 w-4 text-emerald-600" />}
      title="CPCB National Air Quality Index"
      description="Sub-index maximum aggregation calibrated across criteria pollutants against official CPCB standards."
    />
  )
}

// 4. Copernicus CAMS 48-Hour Forecast Card (Post 1 Light Palette)
export function ForecastChartCard({
  forecast,
}: {
  forecast?: AirQualityData['forecast_72h']
}) {
  const safeList = forecast || []
  const data = safeList.slice(0, 48).map((pt) => ({
    time: pt?.time ? (pt.time.split('T')[1] || pt.time) : '--:--',
    aqi: pt?.aqi ?? 0,
    smoke: pt?.wildfire_smoke_pm10 ?? 0,
  }))

  return (
    <BentoGridItem
      className="lg:col-span-2"
      spotlightColor="rgba(2, 132, 199, 0.05)"
      eyebrow="Copernicus CAMS 48-Hour Trajectory"
      action={
        <div className="flex items-center gap-3 text-[10px] font-mono">
          <span className="flex items-center gap-1.5 text-sky-700 font-semibold">
            <i className="h-1.5 w-1.5 rounded-full bg-sky-600" /> NAQI Trend
          </span>
          <span className="flex items-center gap-1.5 text-orange-700 font-semibold">
            <i className="h-1.5 w-1.5 rounded-full bg-orange-600" /> Smoke PM10
          </span>
        </div>
      }
      header={
        <div className="h-[220px] w-full pt-1">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={data} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
              <defs>
                <linearGradient id="aqiGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#0284c7" stopOpacity={0.25} />
                  <stop offset="95%" stopColor="#0284c7" stopOpacity={0.02} />
                </linearGradient>
                <linearGradient id="smokeGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#ea580c" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="#ea580c" stopOpacity={0.02} />
                </linearGradient>
              </defs>
              <CartesianGrid stroke="#e2e8f0" strokeDasharray="2 4" vertical={false} />
              <XAxis dataKey="time" stroke="#64748b" fontSize={9} tickLine={false} axisLine={false} />
              <YAxis stroke="#64748b" fontSize={9} tickLine={false} axisLine={false} />
              <Tooltip
                contentStyle={{
                  backgroundColor: '#ffffff',
                  borderColor: '#e2e8f0',
                  borderRadius: '0.75rem',
                  fontSize: '11px',
                  color: '#0f172a',
                  boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1)',
                }}
              />
              <Area
                type="monotone"
                dataKey="aqi"
                stroke="#0284c7"
                strokeWidth={2}
                fillOpacity={1}
                fill="url(#aqiGrad)"
              />
              <Area
                type="monotone"
                dataKey="smoke"
                stroke="#ea580c"
                strokeWidth={1.5}
                fillOpacity={1}
                fill="url(#smokeGrad)"
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      }
      icon={<Activity className="h-4 w-4 text-sky-600" />}
      title="Copernicus CAMS Chemical Trajectory"
      description="Supercomputer chemical transport simulation estimating particulate matter transport and optical smoke depth."
    />
  )
}

// 5. Emergency Action Directives & Hotlines Card (Post 1 Light Palette)
export function EmergencyCard({ prep }: { prep: CommunityPreparedness }) {
  const actions = prep?.recommended_actions || []
  const calls = [
    ['NDMA', '1078', 'Disaster helpline', 'bg-amber-500'],
    ['FIRE', '101', 'Fire response', 'bg-orange-600'],
    ['AMBULANCE', '108', 'Medical emergency', 'bg-rose-600'],
    ['NATIONAL', '112', 'Unified helpline', 'bg-emerald-600'],
  ] as const

  return (
    <BentoGridItem
      className="lg:col-span-3"
      spotlightColor="rgba(2, 132, 199, 0.05)"
      eyebrow="NDMA Actionable Preparedness // Emergency Directory"
      action={
        <span
          className={`rounded-full px-2.5 py-0.5 text-[10px] font-bold uppercase tracking-wider border ${
            prep?.status === 'alert'
              ? 'bg-red-50 text-red-700 border-red-200'
              : 'bg-emerald-50 text-emerald-700 border-emerald-200'
          }`}
        >
          {prep?.status === 'alert' ? 'Elevated Alert Active' : 'Normal Vigilance'}
        </span>
      }
      header={
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-12 py-1">
          {/* Recommended Actions */}
          <div className="lg:col-span-8 space-y-2">
            <span className="text-[9px] font-mono font-semibold uppercase tracking-[0.2em] text-slate-500">
              Community Health & Safety Protocols
            </span>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 mt-1">
              {actions.map((act, i) => (
                <div
                  key={i}
                  className="flex items-start gap-2.5 rounded-xl border border-slate-200 bg-slate-50/70 p-2.5 text-xs text-slate-700"
                >
                  <ShieldCheck className="h-4 w-4 text-sky-600 shrink-0 mt-0.5" />
                  <span>{act}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Speed-Dial Buttons */}
          <div className="lg:col-span-4">
            <span className="text-[9px] font-mono font-semibold uppercase tracking-[0.2em] text-slate-500">
              Emergency Speed-Dials
            </span>
            <div className="grid grid-cols-2 gap-2 mt-1">
              {calls.map(([label, number, sub, dot]) => (
                <a
                  href={`tel:${number}`}
                  key={number}
                  className="group rounded-xl border border-slate-200 bg-white p-2.5 transition hover:border-slate-300 hover:bg-slate-50 hover:shadow-sm"
                >
                  <div className="flex items-center gap-1.5">
                    <i className={`h-2 w-2 rounded-full ${dot}`} />
                    <span className="font-mono text-[9px] tracking-widest text-slate-500 font-semibold">
                      {label}
                    </span>
                  </div>
                  <div className="mt-2 flex items-center justify-between">
                    <span className="font-mono text-lg font-bold text-slate-900">
                      {number}
                    </span>
                    <ArrowUpRight className="h-3.5 w-3.5 text-slate-400 transition group-hover:text-slate-700" />
                  </div>
                  <p className="mt-0.5 text-[9px] text-slate-500 truncate">{sub}</p>
                </a>
              ))}
            </div>
          </div>
        </div>
      }
      icon={<ShieldCheck className="h-4 w-4 text-indigo-600" />}
      title="NDMA Action Directives & Speed-Dials"
      description="Standard operating procedures mapped to National Disaster Management Authority emergency triage framework."
    />
  )
}

// 6. State Badge Component (Post 1 Light Palette)
export function StateBadge({
  state,
}: {
  state: 'empty' | 'loading' | 'error' | 'partial' | 'populated'
}) {
  if (state === 'loading')
    return (
      <span className="font-mono text-[10px] uppercase tracking-widest text-slate-500 font-semibold">
        SYNCING TELEMETRY...
      </span>
    )
  if (state === 'error')
    return (
      <span className="inline-flex items-center gap-1.5 font-mono text-[10px] uppercase tracking-widest text-red-700 bg-red-50 border border-red-200 px-2 py-0.5 rounded-full font-semibold">
        <AlertTriangle className="h-3 w-3" />
        DATA LINK DEGRADED
      </span>
    )
  return (
    <span className="inline-flex items-center gap-2 font-mono text-[10px] uppercase tracking-widest text-emerald-700 bg-emerald-50 border border-emerald-200 px-2.5 py-1 rounded-full font-bold">
      <i className="h-2 w-2 animate-pulse rounded-full bg-emerald-600" />
      {state === 'partial' ? 'PARTIAL COVERAGE' : 'LIVE SYSTEMS ONLINE'}
    </span>
  )
}
