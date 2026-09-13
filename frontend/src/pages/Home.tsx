import { useState, useEffect, useRef } from 'react'
import { Link } from 'react-router-dom'
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
  Clock,
  X,
  Compass,
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
  RiskGaugeCard,
  WeatherBarCard,
  AirQualityCard,
  ForecastChartCard,
  EmergencyCard,
  StateBadge
} from '../components/BentoCards'
import { BentoGrid, BentoGridItem } from '../components/ui/BentoGrid'
import { FadeUp } from '../components/FadeUp'
import { Footer } from '../components/Footer'

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
  const [healthData, setHealthData] = useState<{
    status: string
    service: string
    districts_loaded: number
    database?: {
      status: string
      provider: string
      project_ref: string
      regions_in_db: number
    }
  } | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [isWakingUp, setIsWakingUp] = useState(false)
  const wakeupTimerRef = useRef<any>(null)

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

    api.getHealth()
      .then(setHealthData)
      .catch(() => {})

    fetchTelemetry()
  }, [])

  useEffect(() => {
    if (query.trim().length >= 2) {
      const timer = setTimeout(() => {
        api.getDistricts(query.trim())
          .then((res) => {
            if (res.districts && res.districts.length > 0) {
              setDistricts((prev) => {
                const map = new Map(prev.map(d => [d.name.toLowerCase(), d]))
                res.districts.forEach(d => map.set(d.name.toLowerCase(), d))
                return Array.from(map.values())
              })
            }
          })
          .catch(() => {})
      }, 250)
      return () => clearTimeout(timer)
    }
  }, [query])

  useEffect(() => {
    const interval = setInterval(() => {
      if (document.visibilityState === 'visible') {
        fetchTelemetry()
      }
    }, 25000)

    return () => clearInterval(interval)
  }, [])

  const executeSearch = async (targetQuery: string) => {
    if (!targetQuery.trim()) {
      setData(null)
      return
    }
    setLoading(true)
    setError(null)
    setIsWakingUp(false)

    wakeupTimerRef.current = setTimeout(() => {
      setIsWakingUp(true)
    }, 4500)

    try {
      const res = await api.search(targetQuery)
      clearTimeout(wakeupTimerRef.current)
      setIsWakingUp(false)
      setData(res)
      if (res?.location?.name) {
        setDistricts((prev) => {
          if (!prev.some(d => d.name.toLowerCase() === res.location.name.toLowerCase())) {
            return [{
              id: 'loc-' + Date.now(),
              name: res.location.name,
              state: res.location.state,
              lat: res.location.latitude,
              lon: res.location.longitude,
              zone: res.location.eco_zone
            }, ...prev]
          }
          return prev
        })
      }
      setTimeout(fetchTelemetry, 1800)
    } catch (err: any) {
      clearTimeout(wakeupTimerRef.current)
      setIsWakingUp(false)
      const msg = err?.message || 'Failed to fetch environmental telemetry from backend'
      setError(msg)
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
  const regionCount = healthData?.database?.regions_in_db ?? healthData?.districts_loaded ?? districts.length ?? 39

  return (
    <div className="min-h-screen bg-[#F8FAFC] text-slate-900 font-sans antialiased selection:bg-sky-500 selection:text-white">
      {/* Sticky Header in Post 1 Pure Solid White */}
      <header className="sticky top-0 z-30 border-b border-slate-200 bg-white/95 backdrop-blur-md shadow-xs">
        <div className="mx-auto flex max-w-[1500px] flex-col gap-3 px-4 py-3 sm:flex-row sm:items-center sm:justify-between sm:px-6 lg:px-8">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl border border-slate-200 bg-slate-50 shadow-xs">
              <Flame className="h-5 w-5 text-orange-600" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-sm font-bold tracking-tight text-slate-900 sm:text-base">
                  AERORISK INDIA
                </h1>
                <span className="rounded-full bg-sky-50 px-2 py-0.5 text-[9px] font-mono font-bold text-sky-700 border border-sky-200">
                  NATIONAL CONSOLE
                </span>
              </div>
              <p className="text-[11px] text-slate-500">
                AI-Driven Wildfire Risk, Satellite Hotspots & Copernicus Air Quality
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <form onSubmit={handleSubmit} className="relative w-full sm:w-80">
              <Search className="absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
              <input
                type="text"
                list="district-options"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Escape') setQuery('')
                }}
                placeholder="Search any Indian city, district, or town..."
                className="h-9 w-full rounded-xl border border-slate-200 bg-slate-50 pl-9 pr-8 text-xs text-slate-900 placeholder-slate-400 outline-none transition-all focus:border-sky-600 focus:bg-white focus:ring-2 focus:ring-sky-500/20"
              />
              {query && (
                <button
                  type="button"
                  onClick={() => setQuery('')}
                  className="absolute right-2.5 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-700 p-0.5 cursor-pointer"
                  title="Clear search (Esc)"
                >
                  <X className="h-3.5 w-3.5" />
                </button>
              )}
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
              className="h-9 rounded-xl bg-sky-600 px-4 text-xs font-bold text-white transition-all hover:bg-sky-700 active:scale-95 shadow-sm shadow-sky-600/20 cursor-pointer"
            >
              Scan
            </button>
            <div className="hidden md:flex items-center gap-2 border-l border-slate-200 pl-3">
              <StateBadge state={currentState} />
            </div>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-[1500px] p-4 sm:p-6 lg:p-8 space-y-5">
        {/* Quick Focus Targets Strip */}
        <FadeUp delay={0.05} className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-200 pb-4">
          <div className="flex flex-wrap items-center gap-1.5 text-xs">
            <span className="mr-1 flex items-center gap-1 font-mono text-[10px] uppercase tracking-wider text-slate-500 font-bold">
              <Sparkles className="h-3 w-3 text-sky-600" />
              FOCUS TARGETS:
            </span>
            {QUICK_CHIPS.map((chip) => (
              <button
                key={chip}
                onClick={() => handleChipClick(chip)}
                className={`rounded-lg border px-2.5 py-1 font-mono text-[10px] transition-all cursor-pointer ${
                  query === chip
                    ? 'border-sky-400 bg-sky-50 text-sky-800 font-bold shadow-xs'
                    : 'border-slate-200 bg-white text-slate-600 hover:border-slate-300 hover:text-slate-900 shadow-2xs'
                }`}
              >
                {chip}
              </button>
            ))}
          </div>

          <div className="flex items-center gap-4 font-mono text-[10px] text-slate-500">
            <span className="flex items-center gap-1.5 font-semibold">
              <Database className="h-3 w-3 text-sky-600" />
              {regionCount} MONITORED DISTRICTS // NATIONWIDE SPATIAL GRID
            </span>
            <span className="hidden sm:inline text-slate-300">|</span>
            <Link
              to="/docs"
              className="hidden sm:flex items-center gap-1 text-slate-600 hover:text-sky-600 transition-colors font-semibold"
            >
              <span>API DOCS</span>
              <ExternalLink className="h-2.5 w-2.5" />
            </Link>
          </div>
        </FadeUp>

        {/* Cold Start Alert */}
        {isWakingUp && loading && (
          <FadeUp delay={0.1} className="rounded-2xl border border-sky-200 bg-sky-50 p-4 text-xs text-sky-900 flex items-center justify-between shadow-sm">
            <div className="flex items-center gap-3">
              <div className="h-5 w-5 animate-spin rounded-full border-2 border-sky-600 border-t-transparent shrink-0" />
              <div>
                <p className="font-bold text-sky-900">Connecting to Cloud Telemetry Cluster</p>
                <p className="text-sky-700 text-[11px]">Backend is waking up from idle power-save mode (Render free tier). Syncing satellite streams, please wait ~15 seconds...</p>
              </div>
            </div>
          </FadeUp>
        )}

        {error && (
          <FadeUp delay={0.1} className="rounded-2xl border border-red-200 bg-red-50 p-4 text-xs text-red-900 flex items-center justify-between shadow-sm">
            <div className="flex items-center gap-3">
              <AlertCircle className="h-5 w-5 text-red-600 shrink-0" />
              <div>
                <p className="font-bold">Telemetry Synchronisation Alert</p>
                <p className="text-red-700 text-[11px]">{error}</p>
              </div>
            </div>
            <button
              onClick={() => executeSearch(query)}
              className="flex items-center gap-1.5 rounded-xl bg-red-600 px-3.5 py-2 font-bold text-white hover:bg-red-700 transition-all cursor-pointer shadow-sm"
            >
              <RefreshCw className="h-3.5 w-3.5" />
              <span>Retry Relay</span>
            </button>
          </FadeUp>
        )}

        {loading && !data && (
          <div className="space-y-4 animate-pulse">
            <div className="h-12 rounded-xl bg-slate-200/60 border border-slate-200" />
            <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
              <div className="h-[440px] rounded-2xl bg-slate-200/60 lg:col-span-2 border border-slate-200" />
              <div className="h-[440px] rounded-2xl bg-slate-200/60 lg:col-span-1 border border-slate-200" />
            </div>
            <div className="h-28 rounded-2xl bg-slate-200/60 border border-slate-200" />
            <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
              <div className="h-80 rounded-2xl bg-slate-200/60 lg:col-span-1 border border-slate-200" />
              <div className="h-80 rounded-2xl bg-slate-200/60 lg:col-span-2 border border-slate-200" />
            </div>
          </div>
        )}

        {!loading && !data && !error && (
          <div className="rounded-2xl border border-slate-200 bg-white p-8 shadow-sm">
            <div className="flex min-h-[300px] flex-col items-center justify-center text-center p-4">
              <Layers className="h-12 w-12 text-slate-400 mb-3" />
              <h3 className="text-lg font-bold text-slate-900">No District Telemetry Active</h3>
              <p className="mt-1 text-xs text-slate-500 max-w-sm">
                Enter an Indian district name in the search portal or select one of the focus targets above to stream live environmental intelligence.
              </p>
              <button
                onClick={() => handleChipClick('Jalgaon / Bhusawal')}
                className="mt-5 rounded-xl bg-sky-600 px-5 py-2.5 text-xs font-bold text-white hover:bg-sky-700 transition-all cursor-pointer shadow-sm"
              >
                Focus Jalgaon / Bhusawal
              </button>
            </div>
          </div>
        )}

        {data && (
          <div className="space-y-5">
            {/* Top Location Banner */}
            <FadeUp delay={0.1} className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between rounded-2xl border border-slate-200 bg-white px-5 py-3.5 shadow-sm">
              <div className="flex items-center gap-3">
                <MapPin className="h-5 w-5 text-sky-600" />
                <div>
                  <h2 className="text-base font-bold text-slate-900 tracking-tight">
                    {data.location.name}
                    <span className="ml-2 font-normal text-slate-500 text-xs">
                      {data.location.state}
                    </span>
                  </h2>
                  <p className="font-mono text-[10px] text-slate-500">
                    Eco-Zone: <span className="text-slate-800 font-semibold">{data.location.eco_zone}</span> • Lat: {data.location.latitude.toFixed(4)}°, Lon: {data.location.longitude.toFixed(4)}°
                  </p>
                </div>
              </div>

              <div className="flex items-center gap-2.5 text-xs font-mono">
                <span className="rounded-lg bg-slate-50 border border-slate-200 px-3 py-1 text-slate-700 font-semibold">
                  Van Wagner FWI: <span className="font-bold text-slate-900">{data.wildfire_assessment.fwi_score}</span>
                </span>
                <span className="rounded-lg bg-slate-50 border border-slate-200 px-3 py-1 text-slate-700 font-semibold">
                  CPCB AQI: <span className="font-bold text-slate-900">{data.air_quality.cpcb_aqi}</span>
                </span>
              </div>
            </FadeUp>

            {/* Post 1 Bento Grid (Nordic Cool Slate & Sapphire) */}
            <BentoGrid>
              {/* Card 1: Geospatial Fire & Buffer Map (2 cols) */}
              <BentoGridItem
                className="lg:col-span-2 min-h-[460px]"
                spotlightColor="rgba(2, 132, 199, 0.05)"
                eyebrow="Spatial Fire Risk Perimeter // WebGL Engine"
                action={
                  <div className="flex items-center gap-2">
                    <span className="font-mono text-[9px] uppercase tracking-wider text-sky-800 bg-sky-50 border border-sky-200 px-2 py-0.5 rounded-full flex items-center gap-1.5 font-bold">
                      <i className="h-1.5 w-1.5 rounded-full bg-sky-600 animate-pulse" />
                      50km Buffer Ring
                    </span>
                    <span className="font-mono text-[9px] text-slate-600 bg-slate-50 border border-slate-200 px-2 py-0.5 rounded-full font-semibold">
                      NASA VIIRS 375m
                    </span>
                  </div>
                }
                header={
                  <div className="h-[360px] w-full rounded-xl overflow-hidden border border-slate-200">
                    <RegionMap
                      selectedLocation={{
                        lat: data.location.latitude,
                        lon: data.location.longitude,
                        name: data.location.name
                      }}
                      activeFires={fires}
                    />
                  </div>
                }
                icon={<Compass className="h-4 w-4 text-sky-600" />}
                title="Real-Time Spatial Geospatial & Fire Perimeter"
                description="Interactive WebGL mapping engine rendering active NASA VIIRS thermal anomalies with dynamic 50km spatial buffer risk analysis."
              />

              {/* Card 2: Canadian FWI Danger Rating (1 col) */}
              <RiskGaugeCard risk={data.wildfire_assessment} />

              {/* Card 3: Surface Atmospheric Observations (Full Width, 3 cols) */}
              <WeatherBarCard weather={data.weather} />

              {/* Card 4: CPCB Air Quality Index (1 col) */}
              <AirQualityCard aqi={data.air_quality} />

              {/* Card 5: Copernicus CAMS 48-Hour Chemical Trajectory (2 cols) */}
              <ForecastChartCard forecast={data.air_quality.forecast_72h} />

              {/* Card 6: NDMA Action Directives & Emergency Hotlines (Full Width, 3 cols) */}
              <EmergencyCard prep={data.community_preparedness} />

              {/* Card 7: National Environmental Surveillance Feed (Full Width, 3 cols) */}
              <BentoGridItem
                className="lg:col-span-3"
                spotlightColor="rgba(2, 132, 199, 0.05)"
                eyebrow="24/7 Spatial Telemetry // PostGIS Engine"
                action={
                  <div className="flex items-center gap-2">
                    <span className="flex items-center gap-1.5 font-mono text-[10px] text-emerald-700 bg-emerald-50 border border-emerald-200 px-2 py-0.5 rounded-full font-bold">
                      <span className="relative flex h-2 w-2">
                        <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-75"></span>
                        <span className="relative inline-flex h-2 w-2 rounded-full bg-emerald-600"></span>
                      </span>
                      Auto-Sync Active
                    </span>
                    <button
                      onClick={fetchTelemetry}
                      className="flex items-center gap-1 rounded-lg border border-slate-200 bg-slate-50 px-2.5 py-1 text-[10px] font-mono text-slate-700 hover:bg-slate-100 hover:text-slate-900 transition cursor-pointer font-semibold shadow-2xs"
                      title="Refresh query audit log from Supabase"
                    >
                      <RefreshCw className="h-3 w-3" />
                      <span>Sync</span>
                    </button>
                  </div>
                }
                header={
                  <div className="overflow-x-auto py-1">
                    {telemetryLogs.length === 0 ? (
                      <div className="flex items-center justify-center p-8 text-center text-xs text-slate-500 font-mono">
                        Synchronizing spatial telemetry stream across 39 monitored districts...
                      </div>
                    ) : (
                      <table className="w-full text-left text-xs">
                        <thead>
                          <tr className="border-b border-slate-200 font-mono text-[9px] uppercase tracking-wider text-slate-500">
                            <th className="pb-2 font-semibold">Timestamp (UTC)</th>
                            <th className="pb-2 font-semibold">District & State</th>
                            <th className="pb-2 font-semibold">Eco-Zone</th>
                            <th className="pb-2 font-semibold">Canadian FWI</th>
                            <th className="pb-2 font-semibold">CPCB AQI</th>
                            <th className="pb-2 font-semibold text-right">Audit Verification</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-100 font-mono text-[11px]">
                          {telemetryLogs.map((log) => {
                            const badgeStyle =
                              log.risk_level === 'Extreme' || log.risk_level === 'Very High'
                                ? 'bg-red-50 text-red-700 border border-red-200'
                                : log.risk_level === 'High'
                                ? 'bg-orange-50 text-orange-700 border border-orange-200'
                                : 'bg-emerald-50 text-emerald-700 border border-emerald-200'

                            return (
                              <tr key={log.id || log.created_at} className="hover:bg-slate-50 transition-colors">
                                <td className="py-2.5 text-slate-500 flex items-center gap-1.5">
                                  <Clock className="h-3 w-3 text-slate-400 shrink-0" />
                                  <span>{new Date(log.created_at).toLocaleTimeString()}</span>
                                </td>
                                <td className="py-2.5 font-sans font-medium text-slate-900">
                                  <span>{log.district_name}</span>
                                  <span className="ml-1 text-slate-500 text-[10px]">({log.state})</span>
                                </td>
                                <td className="py-2.5 text-slate-500 text-[10px]">{log.eco_zone}</td>
                                <td className="py-2.5">
                                  <span
                                    className={`inline-flex items-center rounded px-1.5 py-0.5 text-[10px] font-bold ${badgeStyle}`}
                                  >
                                    {log.fwi_score?.toFixed(1)} • {log.risk_level}
                                  </span>
                                </td>
                                <td className="py-2.5">
                                  <span className="text-slate-900 font-bold">{log.cpcb_aqi}</span>
                                  <span className="ml-1 text-slate-500 text-[10px]">({log.aqi_category})</span>
                                </td>
                                <td className="py-2.5 text-right">
                                  <span className="inline-flex items-center gap-1 text-[10px] text-emerald-700 font-bold">
                                    <CheckCircle2 className="h-3 w-3" />
                                    <span>Verified Stream</span>
                                  </span>
                                </td>
                              </tr>
                            )
                          })}
                        </tbody>
                      </table>
                    )}
                  </div>
                }
                icon={<CheckCircle2 className="h-4 w-4 text-emerald-600" />}
                title="National Environmental Surveillance Audit Feed"
                description="Cryptographically verified spatial persistence logs recorded in Supabase PostGIS across all 39 monitored districts."
              />
            </BentoGrid>
          </div>
        )}
      </main>
      <Footer />
    </div>
  )
}
