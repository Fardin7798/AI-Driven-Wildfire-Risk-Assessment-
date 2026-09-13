import { useState, useEffect } from 'react'
import { Search, AlertCircle, RefreshCw, MapPin, Sparkles } from 'lucide-react'
import { api } from '../lib/api'
import type {
  UnifiedSearchResponse,
  GeoJSONFeatureCollection,
  District
} from '../types'
import { RegionMap } from '../components/RegionMap'
import {
  WildfireRiskCard,
  WeatherCard,
  AirQualityCard,
  ForecastChartCard,
  PreparednessCard
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
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    api.getDistricts()
      .then((res) => setDistricts(res.districts))
      .catch(() => {})

    api.getActiveFires()
      .then((geo) => setFires(geo))
      .catch(() => {})
  }, [])

  const executeSearch = async (targetQuery: string) => {
    setLoading(true)
    setError(null)
    try {
      const res = await api.search(targetQuery)
      setData(res)
    } catch (err: any) {
      setError(err?.message || 'Failed to fetch environmental intelligence')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    executeSearch(query)
  }, [])

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (query.trim()) {
      executeSearch(query.trim())
    }
  }

  const handleChipClick = (city: string) => {
    setQuery(city)
    executeSearch(city)
  }

  return (
    <div className="min-h-screen bg-zinc-950 text-zinc-100 p-4 sm:p-6 lg:p-8">
      {/* 1. Header & Search Portal */}
      <FadeUp as="header" delay={0.05} className="mb-6 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between border-b border-zinc-800/80 pb-5">
        <div>
          <div className="flex items-center gap-2">
            <span className="relative flex h-2 w-2">
              <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-75"></span>
              <span className="relative inline-flex h-2 w-2 rounded-full bg-emerald-400"></span>
            </span>
            <span className="text-[11px] font-mono font-semibold uppercase tracking-widest text-emerald-400">
              TELEMETRY SYNCHRONIZED // NASA FIRMS & CAMS
            </span>
          </div>
          <h1 className="mt-1 text-2xl font-black tracking-tight text-white sm:text-3xl">
            AERORISK <span className="text-zinc-600 font-light">// INDIA</span>
          </h1>
          <p className="text-xs text-zinc-400">
            Canadian FWI Fire Danger, NASA Satellite Hotspots & CPCB Air Quality Intelligence
          </p>
        </div>

        {/* Search Bar with Datalist Autocomplete */}
        <form onSubmit={handleSubmit} className="flex items-center gap-2 w-full sm:w-auto">
          <div className="relative w-full sm:w-80">
            <Search className="absolute left-3.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-zinc-500" />
            <input
              type="text"
              list="district-options"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search Indian District (e.g. Bhusawal, Nainital)..."
              className="w-full rounded-xl border border-zinc-800 bg-zinc-900/90 pl-9 pr-4 py-2.5 text-xs text-white placeholder-zinc-500 focus:border-cyan-500 focus:outline-none focus:ring-1 focus:ring-cyan-500 transition-all"
            />
            <datalist id="district-options">
              {districts.map((d) => (
                <option key={d.id} value={d.name}>
                  {d.state} ({d.zone})
                </option>
              ))}
            </datalist>
          </div>
          <button
            type="submit"
            className="rounded-xl bg-cyan-500 px-5 py-2.5 text-xs font-bold text-zinc-950 hover:bg-cyan-400 transition-all shadow-sm shadow-cyan-500/20 shrink-0 cursor-pointer"
          >
            Analyze
          </button>
        </form>
      </FadeUp>

      {/* 2. Quick Focus District Chips */}
      <FadeUp delay={0.1} className="mb-6 flex flex-wrap items-center gap-2 text-xs">
        <span className="flex items-center gap-1 text-zinc-500 text-[11px] font-mono">
          <Sparkles className="h-3 w-3 text-cyan-400" />
          QUICK FOCUS:
        </span>
        {QUICK_CHIPS.map((chip) => (
          <button
            key={chip}
            onClick={() => handleChipClick(chip)}
            className={`rounded-lg border px-3 py-1 text-xs transition-all cursor-pointer ${
              query === chip
                ? 'border-cyan-500/50 bg-cyan-500/10 text-cyan-300 font-semibold shadow-sm shadow-cyan-500/20'
                : 'border-zinc-800/80 bg-zinc-900/60 text-zinc-400 hover:border-zinc-700 hover:text-zinc-200'
            }`}
          >
            {chip}
          </button>
        ))}
      </FadeUp>

      {/* 3. Mandatory State: Error State */}
      {error && (
        <FadeUp delay={0.1} className="mb-6 rounded-2xl border border-red-500/30 bg-red-950/20 p-4 text-xs text-red-300 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <AlertCircle className="h-4 w-4 text-red-400 shrink-0" />
            <span>Telemetry Error: {error}</span>
          </div>
          <button
            onClick={() => executeSearch(query)}
            className="flex items-center gap-1.5 rounded-lg bg-red-600 px-3 py-1.5 font-bold text-white hover:bg-red-500 transition-colors cursor-pointer"
          >
            <RefreshCw className="h-3 w-3" />
            <span>Retry</span>
          </button>
        </FadeUp>
      )}

      {/* 4. Mandatory State: Skeleton Loading State */}
      {loading && !data && (
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-12 animate-pulse">
          <div className="h-96 rounded-2xl bg-zinc-900/60 lg:col-span-7"></div>
          <div className="h-96 rounded-2xl bg-zinc-900/60 lg:col-span-5"></div>
          <div className="h-24 rounded-2xl bg-zinc-900/60 lg:col-span-12"></div>
          <div className="h-80 rounded-2xl bg-zinc-900/60 lg:col-span-5"></div>
          <div className="h-80 rounded-2xl bg-zinc-900/60 lg:col-span-7"></div>
        </div>
      )}

      {/* 5. Mandatory State: Populated High-Density Bento Grid */}
      {data && (
        <div className="space-y-4">
          {/* Active Target Info Header */}
          <FadeUp delay={0.12} className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-zinc-800/80 bg-zinc-900/40 px-4 py-2.5 text-xs text-zinc-400 backdrop-blur-md">
            <div className="flex items-center gap-2">
              <MapPin className="h-3.5 w-3.5 text-cyan-400" />
              <span className="font-bold text-white text-sm">{data.location.name}</span>
              <span className="text-zinc-400">({data.location.state})</span>
              <span className="rounded-md border border-zinc-800 bg-zinc-800/80 px-2 py-0.5 text-[10px] font-mono text-zinc-300">
                {data.location.eco_zone}
              </span>
            </div>
            <div className="flex items-center gap-4 text-[11px] font-mono">
              <span>LAT {data.location.latitude.toFixed(2)}° N / LON {data.location.longitude.toFixed(2)}° E</span>
              <span className="text-zinc-500">FEED SYNC: {new Date(data.metadata.timestamp).toLocaleTimeString()}</span>
            </div>
          </FadeUp>

          {/* Row 1: 60fps Vector Map (7 cols) + Wildfire Risk Card (5 cols) */}
          <div className="grid grid-cols-1 gap-4 lg:grid-cols-12">
            <FadeUp delay={0.15} className="h-[430px] lg:col-span-7">
              <RegionMap
                selectedLocation={{
                  lat: data.location.latitude,
                  lon: data.location.longitude,
                  name: data.location.name
                }}
                activeFires={fires}
              />
            </FadeUp>
            <div className="lg:col-span-5">
              <WildfireRiskCard risk={data.wildfire_assessment} />
            </div>
          </div>

          {/* Row 2: Live Weather Meteorology Bar */}
          <WeatherCard weather={data.weather} />

          {/* Row 3: Air Quality (5 cols) + 48h Forecast Chart (7 cols) */}
          <div className="grid grid-cols-1 gap-4 lg:grid-cols-12">
            <div className="lg:col-span-5">
              <AirQualityCard aqi={data.air_quality} />
            </div>
            <div className="lg:col-span-7">
              <ForecastChartCard forecast={data.air_quality.forecast_72h} />
            </div>
          </div>

          {/* Row 4: Community Preparedness & Emergency Directory */}
          <PreparednessCard prep={data.community_preparedness} />
        </div>
      )}
    </div>
  )
}
