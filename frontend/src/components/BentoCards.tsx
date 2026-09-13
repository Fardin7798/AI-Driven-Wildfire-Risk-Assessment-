import {
  Flame,
  Wind,
  Droplets,
  Thermometer,
  CloudRain,
  ShieldCheck,
  PhoneCall,
  Activity,
  AlertTriangle,
  Compass
} from 'lucide-react'
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer
} from 'recharts'
import type {
  WildfireAssessment,
  WeatherData,
  AirQualityData,
  CommunityPreparedness
} from '../types'
import { FadeUp } from './FadeUp'

// 1. Wildfire Risk Card (Canadian Forest Fire Weather Index)
export function WildfireRiskCard({ risk }: { risk: WildfireAssessment }) {
  return (
    <FadeUp delay={0.1} className="flex h-full flex-col justify-between rounded-2xl border border-zinc-800 bg-zinc-900/60 p-5 backdrop-blur-md">
      <div>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Flame className="h-4 w-4 text-orange-500" />
            <span className="text-xs font-semibold uppercase tracking-wider text-zinc-400">
              Canadian FWI Risk Rating
            </span>
          </div>
          <span className={`rounded-full px-2.5 py-0.5 text-xs font-bold uppercase tracking-wider border ${risk.badge}`}>
            {risk.risk_level}
          </span>
        </div>

        <div className="mt-4 flex items-baseline gap-3">
          <span className="tabular-nums font-mono text-4xl font-black tracking-tight text-white">
            {risk.fwi_score}
          </span>
          <span className="text-xs text-zinc-400">
            Composite FWI Index
          </span>
        </div>

        {/* 5-Segment FWI Visual Danger Meter */}
        <div className="mt-3">
          <div className="flex justify-between text-[10px] text-zinc-500 font-mono mb-1">
            <span>LOW</span>
            <span>MODERATE</span>
            <span>HIGH</span>
            <span>VERY HIGH</span>
            <span>EXTREME</span>
          </div>
          <div className="h-2 w-full overflow-hidden rounded-full bg-zinc-950 flex gap-0.5">
            <div className={`h-full flex-1 transition-all ${risk.fwi_score >= 0 ? 'bg-emerald-500' : 'bg-zinc-800'}`}></div>
            <div className={`h-full flex-1 transition-all ${risk.fwi_score >= 5 ? 'bg-yellow-500' : 'bg-zinc-800'}`}></div>
            <div className={`h-full flex-1 transition-all ${risk.fwi_score >= 12 ? 'bg-orange-500' : 'bg-zinc-800'}`}></div>
            <div className={`h-full flex-1 transition-all ${risk.fwi_score >= 21 ? 'bg-red-500' : 'bg-zinc-800'}`}></div>
            <div className={`h-full flex-1 transition-all ${risk.fwi_score >= 32 ? 'bg-purple-600' : 'bg-zinc-800'}`}></div>
          </div>
        </div>

        {/* Scientific Sub-Indices */}
        <div className="mt-4 grid grid-cols-2 gap-2">
          <div className="rounded-xl border border-zinc-800/80 bg-zinc-950/60 p-3">
            <div className="flex items-center justify-between text-zinc-400 text-xs">
              <span>FFMC (Litter Moisture)</span>
              <Activity className="h-3.5 w-3.5 text-cyan-400" />
            </div>
            <p className="mt-1 tabular-nums font-mono text-xl font-bold text-zinc-100">{risk.ffmc}</p>
            <p className="text-[10px] text-zinc-500">Equilibrium surface dry state</p>
          </div>
          <div className="rounded-xl border border-zinc-800/80 bg-zinc-950/60 p-3">
            <div className="flex items-center justify-between text-zinc-400 text-xs">
              <span>ISI (Spread Velocity)</span>
              <Compass className="h-3.5 w-3.5 text-orange-400" />
            </div>
            <p className="mt-1 tabular-nums font-mono text-xl font-bold text-zinc-100">{risk.isi}</p>
            <p className="text-[10px] text-zinc-500">Wind-driven forward propagation</p>
          </div>
        </div>

        {/* Proximity Warning */}
        {risk.closest_active_fire_km !== null && (
          <div className="mt-3 flex items-center justify-between rounded-xl border border-orange-500/20 bg-orange-950/20 px-3 py-2 text-xs">
            <span className="flex items-center gap-1.5 text-orange-300">
              <AlertTriangle className="h-3.5 w-3.5 shrink-0" />
              Nearest NASA Hotspot:
            </span>
            <span className="tabular-nums font-mono font-bold text-orange-400">
              {risk.closest_active_fire_km < 900 ? `${risk.closest_active_fire_km.toFixed(1)} km away` : 'No fire in 50km'}
            </span>
          </div>
        )}
      </div>

      <div className="mt-3 space-y-1 border-t border-zinc-800/60 pt-3">
        {risk.key_drivers.map((driver, i) => (
          <div key={i} className="flex items-start gap-1.5 text-[11px] text-zinc-400">
            <span className="text-cyan-400">•</span>
            <span>{driver}</span>
          </div>
        ))}
      </div>
    </FadeUp>
  )
}

// 2. Weather Telemetry Card
export function WeatherCard({ weather }: { weather: WeatherData }) {
  return (
    <FadeUp delay={0.15} className="rounded-2xl border border-zinc-800 bg-zinc-900/60 p-4 backdrop-blur-md">
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <div className="flex items-center gap-3 rounded-xl border border-zinc-800/80 bg-zinc-950/60 p-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-orange-500/10 text-orange-400 shrink-0">
            <Thermometer className="h-5 w-5" />
          </div>
          <div>
            <span className="text-[11px] text-zinc-400">Surface Temp</span>
            <p className="tabular-nums font-mono text-lg font-bold text-white">{weather.temperature}°C</p>
          </div>
        </div>

        <div className="flex items-center gap-3 rounded-xl border border-zinc-800/80 bg-zinc-950/60 p-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-cyan-500/10 text-cyan-400 shrink-0">
            <Droplets className="h-5 w-5" />
          </div>
          <div>
            <span className="text-[11px] text-zinc-400">Relative Humidity</span>
            <p className="tabular-nums font-mono text-lg font-bold text-white">{weather.humidity}%</p>
          </div>
        </div>

        <div className="flex items-center gap-3 rounded-xl border border-zinc-800/80 bg-zinc-950/60 p-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-emerald-500/10 text-emerald-400 shrink-0">
            <Wind className="h-5 w-5" />
          </div>
          <div>
            <span className="text-[11px] text-zinc-400">Wind Velocity</span>
            <p className="tabular-nums font-mono text-lg font-bold text-white">{weather.wind_speed} km/h</p>
          </div>
        </div>

        <div className="flex items-center gap-3 rounded-xl border border-zinc-800/80 bg-zinc-950/60 p-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-blue-500/10 text-blue-400 shrink-0">
            <CloudRain className="h-5 w-5" />
          </div>
          <div>
            <span className="text-[11px] text-zinc-400">Precipitation (24h)</span>
            <p className="tabular-nums font-mono text-lg font-bold text-white">{weather.precipitation} mm</p>
          </div>
        </div>
      </div>
    </FadeUp>
  )
}

// 3. Air Quality Card (CPCB NAQI)
export function AirQualityCard({ aqi }: { aqi: AirQualityData }) {
  const aqiPercentage = Math.min(Math.round((aqi.cpcb_aqi / 500) * 100), 100)

  return (
    <FadeUp delay={0.2} className="flex h-full flex-col justify-between rounded-2xl border border-zinc-800 bg-zinc-900/60 p-5 backdrop-blur-md">
      <div>
        <div className="flex items-center justify-between">
          <span className="text-xs font-semibold uppercase tracking-wider text-zinc-400">
            CPCB National AQI Standard
          </span>
          <span className={`rounded-full px-2.5 py-0.5 text-xs font-bold uppercase tracking-wider border ${aqi.badge}`}>
            {aqi.category}
          </span>
        </div>

        <div className="mt-4 flex items-baseline gap-3">
          <span className="tabular-nums font-mono text-4xl font-black tracking-tight text-white">
            {aqi.cpcb_aqi}
          </span>
          <span className="text-xs text-zinc-400">
            NAQI Score (0–500 Scale)
          </span>
        </div>

        {/* Linear NAQI Progress Bar */}
        <div className="mt-3">
          <div className="flex justify-between text-[10px] text-zinc-500 font-mono mb-1">
            <span>0 Good</span>
            <span>100 Mod</span>
            <span>250 Poor</span>
            <span>500 Severe</span>
          </div>
          <div className="h-2 w-full overflow-hidden rounded-full bg-zinc-950">
            <div
              className="h-full rounded-full transition-all duration-500"
              style={{
                width: `${aqiPercentage}%`,
                backgroundColor: aqi.color
              }}
            ></div>
          </div>
        </div>

        {/* 6-Pollutant Telemetry Grid */}
        <div className="mt-4 grid grid-cols-3 gap-2 text-xs">
          <div className="rounded-xl border border-zinc-800/80 bg-zinc-950/60 p-2.5">
            <span className="text-zinc-500 text-[10px] uppercase font-mono">PM2.5</span>
            <p className="mt-0.5 tabular-nums font-mono font-bold text-zinc-100">{aqi.pollutants.pm2_5} <span className="text-[9px] text-zinc-500">µg/m³</span></p>
          </div>
          <div className="rounded-xl border border-zinc-800/80 bg-zinc-950/60 p-2.5">
            <span className="text-zinc-500 text-[10px] uppercase font-mono">PM10</span>
            <p className="mt-0.5 tabular-nums font-mono font-bold text-zinc-100">{aqi.pollutants.pm10} <span className="text-[9px] text-zinc-500">µg/m³</span></p>
          </div>
          <div className="rounded-xl border border-zinc-800/80 bg-zinc-950/60 p-2.5">
            <span className="text-zinc-500 text-[10px] uppercase font-mono">Ozone (O3)</span>
            <p className="mt-0.5 tabular-nums font-mono font-bold text-zinc-100">{aqi.pollutants.o3} <span className="text-[9px] text-zinc-500">µg/m³</span></p>
          </div>
          <div className="rounded-xl border border-zinc-800/80 bg-zinc-950/60 p-2.5">
            <span className="text-zinc-500 text-[10px] uppercase font-mono">NO2</span>
            <p className="mt-0.5 tabular-nums font-mono font-bold text-zinc-100">{aqi.pollutants.no2} <span className="text-[9px] text-zinc-500">µg/m³</span></p>
          </div>
          <div className="rounded-xl border border-zinc-800/80 bg-zinc-950/60 p-2.5">
            <span className="text-zinc-500 text-[10px] uppercase font-mono">SO2</span>
            <p className="mt-0.5 tabular-nums font-mono font-bold text-zinc-100">{aqi.pollutants.so2} <span className="text-[9px] text-zinc-500">µg/m³</span></p>
          </div>
          <div className="rounded-xl border border-zinc-800/80 bg-zinc-950/60 p-2.5">
            <span className="text-zinc-500 text-[10px] uppercase font-mono">CO</span>
            <p className="mt-0.5 tabular-nums font-mono font-bold text-zinc-100">{aqi.pollutants.co} <span className="text-[9px] text-zinc-500">µg/m³</span></p>
          </div>
        </div>
      </div>
      <div className="mt-3 text-[10px] text-zinc-500">
        Calibrated with Copernicus CAMS European atmospheric reanalysis models.
      </div>
    </FadeUp>
  )
}

// 4. 48-Hour Forecast Chart Card
export function ForecastChartCard({ forecast }: { forecast: AirQualityData['forecast_72h'] }) {
  const chartData = forecast.slice(0, 48).map((pt) => ({
    time: pt.time.split('T')[1] || pt.time,
    aqi: pt.aqi,
    smoke: pt.wildfire_smoke_pm10
  }))

  return (
    <FadeUp delay={0.25} className="flex h-full flex-col justify-between rounded-2xl border border-zinc-800 bg-zinc-900/60 p-5 backdrop-blur-md">
      <div>
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div>
            <span className="text-xs font-semibold uppercase tracking-wider text-zinc-400">
              Copernicus CAMS 48-Hour Atmospheric Trajectory
            </span>
            <p className="text-xs text-zinc-500">Hourly NAQI progression & wildfire smoke particulate impact</p>
          </div>
          <div className="flex items-center gap-3 text-xs">
            <span className="flex items-center gap-1.5 text-cyan-400 font-medium">
              <span className="h-2 w-2 rounded-full bg-cyan-400"></span> NAQI Trend
            </span>
            <span className="flex items-center gap-1.5 text-orange-400 font-medium">
              <span className="h-2 w-2 rounded-full bg-orange-400"></span> Wildfire Smoke PM10
            </span>
          </div>
        </div>

        <div className="mt-4 h-60 w-full">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={chartData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
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
              <XAxis dataKey="time" stroke="#71717a" fontSize={10} tickLine={false} />
              <YAxis stroke="#71717a" fontSize={10} tickLine={false} />
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
      </div>
    </FadeUp>
  )
}

// 5. Community Preparedness & Emergency Card
export function PreparednessCard({ prep }: { prep: CommunityPreparedness }) {
  return (
    <FadeUp delay={0.3} className="rounded-2xl border border-zinc-800 bg-zinc-900/60 p-5 backdrop-blur-md">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <ShieldCheck className="h-4 w-4 text-emerald-400" />
          <span className="text-xs font-semibold uppercase tracking-wider text-zinc-400">
            Actionable Community Preparedness Advisory
          </span>
        </div>
        <span
          className={`rounded-full px-3 py-0.5 text-xs font-bold uppercase tracking-wider border ${
            prep.status === 'alert'
              ? 'bg-red-500/10 text-red-400 border-red-500/20'
              : 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20'
          }`}
        >
          {prep.status === 'alert' ? 'Elevated Alert Active' : 'Normal Vigilance'}
        </span>
      </div>

      <div className="mt-4 grid grid-cols-1 gap-5 lg:grid-cols-12">
        {/* Safety Actions */}
        <div className="lg:col-span-8 space-y-2">
          <span className="text-[11px] font-semibold uppercase tracking-wider text-zinc-500">
            Target Health & Safety Directives
          </span>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
            {prep.recommended_actions.map((act, i) => (
              <div key={i} className="flex items-start gap-2.5 rounded-xl border border-zinc-800/80 bg-zinc-950/60 p-3 text-xs text-zinc-200">
                <span className="mt-0.5 text-cyan-400 font-bold">✓</span>
                <span>{act}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Emergency Speed-Dial Contacts */}
        <div className="lg:col-span-4">
          <span className="text-[11px] font-semibold uppercase tracking-wider text-zinc-500">
            Official Emergency Speed-Dials
          </span>
          <div className="mt-2 space-y-2">
            {prep.emergency_contacts.map((contact, idx) => (
              <div
                key={idx}
                className="flex items-center justify-between rounded-xl border border-zinc-800/80 bg-zinc-950/80 p-2.5 text-xs hover:border-zinc-700 transition-colors"
              >
                <div>
                  <p className="font-semibold text-white">{contact.name}</p>
                  <p className="text-[10px] text-zinc-500">{contact.desc}</p>
                </div>
                <a
                  href={`tel:${contact.number}`}
                  className="flex items-center gap-1.5 rounded-lg bg-red-600/20 px-3 py-1.5 font-mono font-bold text-red-400 border border-red-500/30 hover:bg-red-600 hover:text-white transition-all cursor-pointer"
                >
                  <PhoneCall className="h-3 w-3" />
                  <span>{contact.number}</span>
                </a>
              </div>
            ))}
          </div>
        </div>
      </div>
    </FadeUp>
  )
}
