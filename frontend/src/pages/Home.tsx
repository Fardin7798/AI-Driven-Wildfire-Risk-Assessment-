import { useState, useEffect } from 'react'
import {
  Search,
  AlertCircle,
  RefreshCw,
  MapPin,
  Sparkles,
  Flame,
  Layers,
  Database,
  ExternalLink,
  CheckCircle2,
  Clock
} from 'lucide-react'
import { api } from '../lib/api'
import type {
  UnifiedSearchResponse,
  GeoJSONFeatureCollection,
  District,
  TelemetryLog
} from '../types'
import { RegionMap } from '../components/RegionMap'
import {
  Panel,
  RiskGauge,
  WeatherBar,
  AirQuality,
  ForecastChart,
  EmergencyCards,
  StateBadge
} from '../components/BentoCards'
import { FadeUp } from '../components/FadeUp'

const QUICK_CHIPS = [
  'Jalgaon / Bhusawal',
  'Nainital',
  'Delhi-NCR',
  'Pune',
  'Shimla',
  'Mayurbhanj (Similipal)',
  'Balaghat'
]

export default function Home() {
  const [query, setQuery] = useState('Jalgaon / Bhusawal')
  const [districts, setDistricts] = useState<District[]>([])
  const [data, setData] = useState<UnifiedSearchResponse | null>(null)
  const [fires, setFires] = useState<GeoJSONFeatureCollection | undefined>(undefined)
  const [telemetryLogs, setTelemetryLogs] = useState<TelemetryLog[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const fetchTelemetry = () => {
    api.getRecentTelemetry(6)
      .then((res) => {
        if (res?.logs) setTelemetryLogs(res.logs)
      })
      .catch(() => {})
  }

  useEffect(() => {
    api.getDistricts()
      .then((res) => setDistricts(res.districts))
      .catch(() => {})

    api.getActiveFires()
      .then((geo) => setFires(geo))
      .catch(() => {})

    fetchTelemetry()
  }, [])

  const executeSearch = async (targetQuery: string) => {
    if (!targetQuery.trim()) {
      setData(null)
      return
    }
    setLoading(true)
    setError(null)
    try {
      const res = await api.search(targetQuery)
      setData(res)
      setTimeout(fetchTelemetry, 1800)
    } catch (err: any) {
      setError(err?.message || 'Failed to fetch environmental telemetry from backend')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    executeSearch('Jalgaon / Bhusawal')
  }, [])

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (query.trim()) {
      executeSearch(query.trim())
    }
  }

  const handleChipClick = (chip: string) => {
    setQuery(chip)
    executeSearch(chip)
  }

  const currentState = error ? 'error' : loading ? 'loading' : !data ? 'empty' : 'populated'

  return (
    <div className="min-h-screen bg-[#090A0C] text-zinc-100 font-sans antialiased selection:bg-cyan-500 selection:text-black">
      <header className="sticky top-0 z-30 border-b border-white/[0.08] bg-[#090A0C]/90 backdrop-blur-xl">
        <div className="mx-auto flex max-w-[1500px] flex-col gap-3 px-4 py-3 sm:flex-row sm:items-center sm:justify-between sm:px-6 lg:px-8">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl border border-white/[0.1] bg-white/[0.03] shadow-inner">
              <Flame className="h-5 w-5 text-amber-400" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="font-mono text-xs font-bold tracking-wider text-cyan-400">AERORISK</span>
                <span className="rounded bg-white/[0.06] px-1.5 py-0.2 font-mono text-[9px] text-zinc-400">v1.0</span>
                <span className="flex items-center gap-1 rounded border border-emerald-500/20 bg-emerald-500/10 px-1.5 py-0.2 font-mono text-[9px] text-emerald-400">
                  <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 animate-pulse" />
                  SUPABASE POSTGRES
                </span>
              </div>
              <h1 className="text-base font-bold text-white tracking-tight">
                National Wildfire Risk & AQI Engine
              </h1>
            </div>
          </div>

          <div className="flex items-center gap-2 w-full sm:w-auto">
            <form onSubmit={handleSubmit} className="relative flex-1 sm:w-80">
              <Search className="absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-zinc-500" />
              <input
                type="text"
                list="district-options"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Search district, state, city..."
                className="h-9 w-full rounded-xl border border-white/[0.1] bg-white/[0.04] pl-9 pr-4 text-xs text-white placeholder-zinc-500 outline-none transition-all focus:border-cyan-400 focus:bg-white/[0.06] focus:ring-2 focus:ring-cyan-400/20"
              />
              <datalist id="district-options">
                {districts.map((d) => (
                  <option key={d.id} value={d.name}>
                    {d.state} ({d.zone})
                  </option>
                ))}
              </datalist>
            </form>
            <button
              type="button"
              onClick={() => executeSearch(query)}
              className="h-9 rounded-xl bg-cyan-400 px-4 text-xs font-bold text-black transition-all hover:bg-cyan-300 active:scale-95 shadow-md shadow-cyan-400/20 cursor-pointer"
            >
              Scan
            </button>
            <div className="hidden md:flex items-center gap-2 border-l border-white/[0.08] pl-3">
              <StateBadge state={currentState} />
            </div>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-[1500px] p-4 sm:p-6 lg:p-8 space-y-5">
        <FadeUp delay={0.05} className="flex flex-wrap items-center justify-between gap-3 border-b border-white/[0.06] pb-4">
          <div className="flex flex-wrap items-center gap-1.5 text-xs">
            <span className="mr-1 flex items-center gap-1 font-mono text-[10px] uppercase tracking-wider text-zinc-500">
              <Sparkles className="h-3 w-3 text-cyan-400" />
              FOCUS TARGETS:
            </span>
            {QUICK_CHIPS.map((chip) => (
              <button
                key={chip}
                onClick={() => handleChipClick(chip)}
                className={`rounded-lg border px-2.5 py-1 font-mono text-[10px] transition-all cursor-pointer ${
                  query === chip
                    ? 'border-cyan-400/50 bg-cyan-400/10 text-cyan-300 font-bold shadow-sm shadow-cyan-400/20'
                    : 'border-white/[0.08] bg-white/[0.02] text-zinc-400 hover:border-white/20 hover:text-zinc-200'
                }`}
              >
                {chip}
              </button>
            ))}
          </div>

          <div className="flex items-center gap-4 font-mono text-[10px] text-zinc-500">
            <span className="flex items-center gap-1.5">
              <Database className="h-3 w-3 text-cyan-400" />
              SUPABASE POSTGIS: 39 DISTRICTS
            </span>
            <span className="hidden sm:inline text-zinc-600">|</span>
            <a
              href="http://127.0.0.1:8000/docs"
              target="_blank"
              rel="noreferrer"
              className="hidden sm:flex items-center gap-1 text-zinc-400 hover:text-cyan-400 transition-colors"
            >
              <span>API DOCS</span>
              <ExternalLink className="h-2.5 w-2.5" />
            </a>
          </div>
        </FadeUp>

        {error && (
          <FadeUp delay={0.1} className="rounded-2xl border border-red-500/30 bg-red-950/20 p-4 text-xs text-red-200 flex items-center justify-between shadow-xl shadow-red-950/30">
            <div className="flex items-center gap-3">
              <AlertCircle className="h-5 w-5 text-red-400 shrink-0" />
              <div>
                <p className="font-bold">Telemetry Synchronisation Alert</p>
                <p className="text-red-300/80 text-[11px]">{error}</p>
              </div>
            </div>
            <button
              onClick={() => executeSearch(query)}
              className="flex items-center gap-1.5 rounded-xl bg-red-500 px-3.5 py-2 font-bold text-black hover:bg-red-400 transition-all cursor-pointer"
            >
              <RefreshCw className="h-3.5 w-3.5" />
              <span>Retry Relay</span>
            </button>
          </FadeUp>
        )}

        {loading && !data && (
          <div className="space-y-4 animate-pulse">
            <div className="h-12 rounded-xl bg-white/[0.04] border border-white/[0.06]" />
            <div className="grid grid-cols-1 gap-4 lg:grid-cols-12">
              <div className="h-[440px] rounded-2xl bg-white/[0.04] lg:col-span-7 border border-white/[0.06]" />
              <div className="h-[440px] rounded-2xl bg-white/[0.04] lg:col-span-5 border border-white/[0.06]" />
            </div>
            <div className="h-28 rounded-2xl bg-white/[0.04] border border-white/[0.06]" />
            <div className="grid grid-cols-1 gap-4 lg:grid-cols-12">
              <div className="h-80 rounded-2xl bg-white/[0.04] lg:col-span-5 border border-white/[0.06]" />
              <div className="h-80 rounded-2xl bg-white/[0.04] lg:col-span-7 border border-white/[0.06]" />
            </div>
          </div>
        )}

        {!loading && !data && !error && (
          <Panel title="Target Selection Required" eyebrow="Command Portal">
            <div className="flex min-h-[300px] flex-col items-center justify-center text-center p-8">
              <Layers className="h-12 w-12 text-zinc-600 mb-3" />
              <h3 className="text-lg font-bold text-white">No District Telemetry Active</h3>
              <p className="mt-1 text-xs text-zinc-400 max-w-sm">
                Enter an Indian district name in the search portal or select one of the focus targets above to stream live environmental intelligence.
              </p>
              <button
                onClick={() => handleChipClick('Jalgaon / Bhusawal')}
                className="mt-5 rounded-xl bg-cyan-400 px-5 py-2.5 text-xs font-bold text-black hover:bg-cyan-300 transition-all cursor-pointer"
              >
                Scan Bhusawal (Maharashtra)
              </button>
            </div>
          </Panel>
        )}

        {data && (
          <div className="space-y-4">
            <FadeUp delay={0.08} className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-white/[0.08] bg-[#111214] px-4 py-3 text-xs text-zinc-400 shadow-xl backdrop-blur-md">
              <div className="flex flex-wrap items-center gap-2.5">
                <MapPin className="h-4 w-4 text-cyan-400" />
                <span className="font-bold text-white text-sm">{data.location.name}</span>
                <span className="text-zinc-400 font-medium">({data.location.state})</span>
                <span className="rounded-md border border-cyan-500/30 bg-cyan-500/10 px-2 py-0.5 font-mono text-[10px] font-bold text-cyan-300">
                  {data.location.eco_zone}
                </span>
                <span className="rounded-md border border-white/[0.08] bg-white/[0.04] px-2 py-0.5 font-mono text-[10px] text-zinc-400">
                  ZONE: {data.location.eco_zone}
                </span>
              </div>
              <div className="flex items-center gap-4 font-mono text-[11px] text-zinc-400">
                <span>LAT {data.location.latitude.toFixed(4)}° N</span>
                <span>LON {data.location.longitude.toFixed(4)}° E</span>
                <span className="text-cyan-400 font-bold">SYNC: {new Date(data.metadata.timestamp).toLocaleTimeString()}</span>
              </div>
            </FadeUp>

            <div className="grid grid-cols-1 gap-4 lg:grid-cols-12">
              <FadeUp delay={0.1} className="h-[440px] lg:col-span-7">
                <RegionMap
                  selectedLocation={{
                    lat: data.location.latitude,
                    lon: data.location.longitude,
                    name: data.location.name
                  }}
                  activeFires={fires}
                />
              </FadeUp>
              <FadeUp delay={0.12} className="lg:col-span-5">
                <RiskGauge risk={data.wildfire_assessment} />
              </FadeUp>
            </div>

            <FadeUp delay={0.14}>
              <WeatherBar weather={data.weather} />
            </FadeUp>

            <div className="grid grid-cols-1 gap-4 lg:grid-cols-12">
              <FadeUp delay={0.16} className="lg:col-span-5">
                <AirQuality aqi={data.air_quality} />
              </FadeUp>
              <FadeUp delay={0.18} className="lg:col-span-7">
                <ForecastChart forecast={data.air_quality.forecast_72h} />
              </FadeUp>
            </div>

            <FadeUp delay={0.2}>
              <EmergencyCards prep={data.community_preparedness} />
            </FadeUp>

            {/* Supabase Persistent Telemetry Audit Trail */}
            <FadeUp delay={0.22}>
              <Panel
                title="Supabase PostgreSQL Audit Trail"
                eyebrow="Real-Time Data Persistence"
                action={
                  <button
                    onClick={fetchTelemetry}
                    className="flex items-center gap-1.5 rounded-lg border border-white/[0.08] bg-white/[0.04] px-2.5 py-1 text-[11px] font-medium text-zinc-400 hover:text-cyan-300 hover:border-cyan-500/30 transition-all cursor-pointer"
                  >
                    <RefreshCw className="h-3 w-3" />
                    <span>Refresh Logs</span>
                  </button>
                }
              >
                <div className="space-y-3">
                  <div className="flex flex-wrap items-center justify-between gap-2 border-b border-white/[0.06] pb-3 text-xs text-zinc-400">
                    <div className="flex items-center gap-2">
                      <span className="flex h-2 w-2 rounded-full bg-emerald-400 animate-ping" />
                      <span className="font-mono text-emerald-400 font-bold">CONNECTED</span>
                      <span className="text-zinc-500">•</span>
                      <span>Project: <code className="text-cyan-400 font-mono">laasumeyzxskujxrxpcx</code> (ap-south-1)</span>
                      <span className="text-zinc-500">•</span>
                      <span>39 Seeded PostGIS Districts</span>
                    </div>
                    <span className="font-mono text-[11px] text-zinc-500">Table: telemetry_logs</span>
                  </div>

                  {telemetryLogs.length === 0 ? (
                    <div className="py-6 text-center text-xs text-zinc-500">
                      No recent telemetry logs retrieved yet. Execute a district scan to trigger Supabase persistence.
                    </div>
                  ) : (
                    <div className="overflow-x-auto">
                      <table className="w-full text-left text-xs">
                        <thead>
                          <tr className="border-b border-white/[0.06] font-mono text-[10px] uppercase tracking-wider text-zinc-500">
                            <th className="pb-2 font-medium">Timestamp (UTC)</th>
                            <th className="pb-2 font-medium">District & State</th>
                            <th className="pb-2 font-medium">Eco-Zone</th>
                            <th className="pb-2 font-medium">Canadian FWI</th>
                            <th className="pb-2 font-medium">CPCB AQI</th>
                            <th className="pb-2 font-medium text-right">Supabase Status</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-white/[0.04] font-mono text-[11px]">
                          {telemetryLogs.map((log) => (
                            <tr key={log.id || log.created_at} className="hover:bg-white/[0.02] transition-colors">
                              <td className="py-2.5 text-zinc-400 flex items-center gap-1.5">
                                <Clock className="h-3 w-3 text-zinc-600 shrink-0" />
                                <span>{new Date(log.created_at).toLocaleTimeString()}</span>
                              </td>
                              <td className="py-2.5 font-sans font-medium text-white">
                                <span>{log.district_name}</span>
                                <span className="ml-1 text-zinc-500 text-[10px]">({log.state})</span>
                              </td>
                              <td className="py-2.5 text-zinc-400 text-[10px]">{log.eco_zone}</td>
                              <td className="py-2.5">
                                <span
                                  className={`inline-flex items-center rounded px-1.5 py-0.5 text-[10px] font-bold ${
                                    log.risk_level === 'Extreme' || log.risk_level === 'Very High'
                                      ? 'bg-red-500/20 text-red-400 border border-red-500/30'
                                      : log.risk_level === 'High'
                                      ? 'bg-amber-500/20 text-amber-400 border border-amber-500/30'
                                      : 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
                                  }`}
                                >
                                  {log.fwi_score?.toFixed(1)} • {log.risk_level}
                                </span>
                              </td>
                              <td className="py-2.5">
                                <span className="text-zinc-300 font-bold">{log.cpcb_aqi}</span>
                                <span className="ml-1 text-zinc-500 text-[10px]">({log.aqi_category})</span>
                              </td>
                              <td className="py-2.5 text-right">
                                <span className="inline-flex items-center gap-1 text-[10px] text-emerald-400">
                                  <CheckCircle2 className="h-3 w-3" />
                                  <span>Synced</span>
                                </span>
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}
                </div>
              </Panel>
            </FadeUp>
          </div>
        )}
      </main>
    </div>
  )
}
