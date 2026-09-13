import {
  ResponsiveContainer,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip
} from 'recharts'
import type {
  WildfireAssessment,
  WeatherData,
  AirQualityData,
  CommunityPreparedness
} from '../types'

export function WildfireRiskCard({ risk }: { risk: WildfireAssessment }) {
  return (
    <div className="flex flex-col justify-between rounded-2xl border border-zinc-800 bg-zinc-900/60 p-5 backdrop-blur-md">
      <div>
        <div className="flex items-center justify-between">
          <span className="text-xs font-medium uppercase tracking-wider text-zinc-400">
            Canadian FWI Fire Risk
          </span>
          <span
            className={`rounded-full px-2.5 py-0.5 text-xs font-semibold uppercase tracking-wider border ${risk.badge}`}
          >
            {risk.risk_level} Danger
          </span>
        </div>

        <div className="mt-4 flex items-baseline gap-3">
          <span className="text-4xl font-extrabold tracking-tight text-white">
            {risk.fwi_score}
          </span>
          <span className="text-xs text-zinc-400">
            FWI Index (0–100 scale)
          </span>
        </div>

        <div className="mt-3 grid grid-cols-2 gap-2 border-t border-zinc-800/80 pt-3 text-xs">
          <div className="rounded-lg bg-zinc-950/60 p-2">
            <span className="text-zinc-500">Fine Fuel Moisture (FFMC)</span>
            <p className="mt-0.5 font-semibold text-zinc-200">{risk.ffmc}</p>
          </div>
          <div className="rounded-lg bg-zinc-950/60 p-2">
            <span className="text-zinc-500">Initial Spread Rate (ISI)</span>
            <p className="mt-0.5 font-semibold text-zinc-200">{risk.isi}</p>
          </div>
        </div>

        <div className="mt-3">
          <span className="text-[11px] font-medium uppercase tracking-wider text-zinc-500">
            Primary Risk Factors
          </span>
          <ul className="mt-1.5 space-y-1 text-xs text-zinc-300">
            {risk.key_drivers.map((driver, idx) => (
              <li key={idx} className="flex items-start gap-1.5">
                <span className="mt-1 h-1 w-1 rounded-full bg-orange-400 shrink-0"></span>
                <span>{driver}</span>
              </li>
            ))}
          </ul>
        </div>
      </div>

      <div className="mt-4 rounded-xl border border-zinc-800 bg-zinc-950/80 p-3 text-xs flex items-center justify-between">
        <span className="text-zinc-400">Nearby Satellite Fires (50km)</span>
        <span className="font-bold text-orange-400">
          {risk.nearby_satellite_fires_50km > 0
            ? `${risk.nearby_satellite_fires_50km} Hotspots (${risk.closest_active_fire_km ?? 0} km away)`
            : '0 Active Fires within 50km'}
        </span>
      </div>
    </div>
  )
}

export function WeatherCard({ weather }: { weather: WeatherData }) {
  return (
    <div className="rounded-2xl border border-zinc-800 bg-zinc-900/60 p-5 backdrop-blur-md">
      <div className="flex items-center justify-between">
        <span className="text-xs font-medium uppercase tracking-wider text-zinc-400">
          Surface Meteorology (Open-Meteo)
        </span>
        <span className="text-[11px] text-zinc-500">Real-Time Ingestion</span>
      </div>

      <div className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-4">
        <div className="rounded-xl border border-zinc-800/80 bg-zinc-950/70 p-3">
          <span className="text-xs text-zinc-500">Temperature</span>
          <p className="mt-1 text-xl font-bold text-white">{weather.temperature}°C</p>
        </div>
        <div className="rounded-xl border border-zinc-800/80 bg-zinc-950/70 p-3">
          <span className="text-xs text-zinc-500">Relative Humidity</span>
          <p className="mt-1 text-xl font-bold text-white">{weather.humidity}%</p>
        </div>
        <div className="rounded-xl border border-zinc-800/80 bg-zinc-950/70 p-3">
          <span className="text-xs text-zinc-500">Wind Velocity</span>
          <p className="mt-1 text-xl font-bold text-white">{weather.wind_speed} km/h</p>
        </div>
        <div className="rounded-xl border border-zinc-800/80 bg-zinc-950/70 p-3">
          <span className="text-xs text-zinc-500">Precipitation (24h)</span>
          <p className="mt-1 text-xl font-bold text-white">{weather.precipitation} mm</p>
        </div>
      </div>
    </div>
  )
}

export function AirQualityCard({ aqi }: { aqi: AirQualityData }) {
  return (
    <div className="flex flex-col justify-between rounded-2xl border border-zinc-800 bg-zinc-900/60 p-5 backdrop-blur-md">
      <div>
        <div className="flex items-center justify-between">
          <span className="text-xs font-medium uppercase tracking-wider text-zinc-400">
            CPCB National AQI Standard
          </span>
          <span
            className={`rounded-full px-2.5 py-0.5 text-xs font-semibold uppercase tracking-wider border ${aqi.badge}`}
          >
            {aqi.category}
          </span>
        </div>

        <div className="mt-4 flex items-baseline gap-3">
          <span className="text-4xl font-extrabold tracking-tight text-white">
            {aqi.cpcb_aqi}
          </span>
          <span className="text-xs text-zinc-400">
            NAQI Score (0–500 scale)
          </span>
        </div>

        <div className="mt-4 grid grid-cols-3 gap-2 text-xs">
          <div className="rounded-lg bg-zinc-950/60 p-2">
            <span className="text-zinc-500">PM2.5</span>
            <p className="mt-0.5 font-bold text-zinc-200">{aqi.pollutants.pm2_5} µg/m³</p>
          </div>
          <div className="rounded-lg bg-zinc-950/60 p-2">
            <span className="text-zinc-500">PM10</span>
            <p className="mt-0.5 font-bold text-zinc-200">{aqi.pollutants.pm10} µg/m³</p>
          </div>
          <div className="rounded-lg bg-zinc-950/60 p-2">
            <span className="text-zinc-500">Ozone (O3)</span>
            <p className="mt-0.5 font-bold text-zinc-200">{aqi.pollutants.o3} µg/m³</p>
          </div>
          <div className="rounded-lg bg-zinc-950/60 p-2">
            <span className="text-zinc-500">NO2</span>
            <p className="mt-0.5 font-bold text-zinc-200">{aqi.pollutants.no2} µg/m³</p>
          </div>
          <div className="rounded-lg bg-zinc-950/60 p-2">
            <span className="text-zinc-500">SO2</span>
            <p className="mt-0.5 font-bold text-zinc-200">{aqi.pollutants.so2} µg/m³</p>
          </div>
          <div className="rounded-lg bg-zinc-950/60 p-2">
            <span className="text-zinc-500">Carbon Monoxide</span>
            <p className="mt-0.5 font-bold text-zinc-200">{aqi.pollutants.co} µg/m³</p>
          </div>
        </div>
      </div>
      <div className="mt-4 text-[11px] text-zinc-500">
        Continuous atmospheric monitoring calibrated with CAMS Copernicus models.
      </div>
    </div>
  )
}

export function ForecastChartCard({ forecast }: { forecast: AirQualityData['forecast_72h'] }) {
  const chartData = forecast.slice(0, 48).map((pt) => ({
    time: pt.time.split('T')[1] || pt.time,
    aqi: pt.aqi,
    smoke: pt.wildfire_smoke_pm10
  }))

  return (
    <div className="rounded-2xl border border-zinc-800 bg-zinc-900/60 p-5 backdrop-blur-md">
      <div className="flex items-center justify-between">
        <div>
          <span className="text-xs font-medium uppercase tracking-wider text-zinc-400">
            Copernicus CAMS 48-Hour Atmospheric Forecast
          </span>
          <p className="text-xs text-zinc-500">Projected AQI trajectory & wildfire particulate contribution</p>
        </div>
        <div className="flex items-center gap-3 text-xs">
          <span className="flex items-center gap-1 text-cyan-400">
            <span className="h-2 w-2 rounded-full bg-cyan-400"></span> NAQI Trend
          </span>
          <span className="flex items-center gap-1 text-orange-400">
            <span className="h-2 w-2 rounded-full bg-orange-400"></span> Wildfire Smoke PM10
          </span>
        </div>
      </div>

      <div className="mt-4 h-56 w-full">
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
  )
}

export function PreparednessCard({ prep }: { prep: CommunityPreparedness }) {
  return (
    <div className="rounded-2xl border border-zinc-800 bg-zinc-900/60 p-5 backdrop-blur-md">
      <div className="flex items-center justify-between">
        <span className="text-xs font-medium uppercase tracking-wider text-zinc-400">
          Actionable Community Preparedness Advisory
        </span>
        <span
          className={`rounded-full px-2.5 py-0.5 text-xs font-semibold uppercase tracking-wider border ${
            prep.status === 'alert'
              ? 'bg-red-500/10 text-red-400 border-red-500/20'
              : 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20'
          }`}
        >
          {prep.status === 'alert' ? 'Elevated Alert Active' : 'Normal Vigilance'}
        </span>
      </div>

      <div className="mt-4 grid grid-cols-1 gap-4 lg:grid-cols-3">
        <div className="lg:col-span-2 space-y-2">
          <span className="text-[11px] font-medium uppercase tracking-wider text-zinc-500">
            Target Health & Safety Protocols
          </span>
          <div className="space-y-1.5">
            {prep.recommended_actions.map((act, i) => (
              <div key={i} className="flex items-start gap-2 rounded-lg bg-zinc-950/60 p-2.5 text-xs text-zinc-200">
                <span className="mt-0.5 text-cyan-400">✓</span>
                <span>{act}</span>
              </div>
            ))}
          </div>
        </div>

        <div>
          <span className="text-[11px] font-medium uppercase tracking-wider text-zinc-500">
            Emergency Speed-Dial Contacts
          </span>
          <div className="mt-2 space-y-2">
            {prep.emergency_contacts.map((contact, idx) => (
              <div
                key={idx}
                className="flex items-center justify-between rounded-xl border border-zinc-800/80 bg-zinc-950/80 p-2.5 text-xs"
              >
                <div>
                  <p className="font-semibold text-white">{contact.name}</p>
                  <p className="text-[10px] text-zinc-500">{contact.desc}</p>
                </div>
                <a
                  href={`tel:${contact.number}`}
                  className="rounded-lg bg-red-600/20 px-2.5 py-1 font-mono font-bold text-red-400 border border-red-500/30 hover:bg-red-600 hover:text-white transition-colors"
                >
                  {contact.number}
                </a>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}
