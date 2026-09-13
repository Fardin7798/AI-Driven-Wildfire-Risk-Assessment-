import { useState, useEffect } from "react"
import { api } from "../lib/api"
import type {
  UnifiedSearchResponse,
  GeoJSONFeatureCollection,
  District
} from "../types"
import { RegionMap } from "../components/RegionMap"
import {
  WildfireRiskCard,
  WeatherCard,
  AirQualityCard,
  ForecastChartCard,
  PreparednessCard
} from "../components/BentoCards"

const QUICK_CHIPS = [
  "Jalgaon / Bhusawal",
  "Nainital",
  "Delhi-NCR",
  "Pune",
  "Shimla",
  "Mayurbhanj (Similipal)",
  "Balaghat"
]

export default function Home() {
  const [query, setQuery] = useState("Jalgaon / Bhusawal")
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
      setError(err?.message || "Failed to fetch environmental intelligence")
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
      {/* Top Header */}
      <header className="mb-6 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between border-b border-zinc-800/80 pb-5">
        <div>
          <div className="flex items-center gap-2">
            <span className="h-2 w-2 rounded-full bg-emerald-400 animate-pulse"></span>
            <span className="text-[11px] font-mono uppercase tracking-widest text-emerald-400">
              SYSTEM ONLINE // NASA FIRMS & CAMS SYNCED
            </span>
          </div>
          <h1 className="mt-1 text-2xl font-black tracking-tight text-white sm:text-3xl">
            AERORISK <span className="text-zinc-500 font-light">// INDIA</span>
          </h1>
          <p className="text-xs text-zinc-400">
            AI-Driven Wildfire Danger Assessment, Satellite Hotspots & CPCB Air Quality Intelligence
          </p>
        </div>

        {/* Search Bar with Datalist Autocomplete */}
        <form onSubmit={handleSubmit} className="flex items-center gap-2 w-full sm:w-auto">
          <div className="relative w-full sm:w-80">
            <input
              type="text"
              list="district-options"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search Indian District (e.g. Bhusawal, Nainital)..."
              className="w-full rounded-xl border border-zinc-800 bg-zinc-900/90 px-4 py-2 text-xs text-white placeholder-zinc-500 focus:border-cyan-500 focus:outline-none focus:ring-1 focus:ring-cyan-500"
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
            className="rounded-xl bg-cyan-500 px-4 py-2 text-xs font-semibold text-zinc-950 hover:bg-cyan-400 transition-colors shrink-0 cursor-pointer"
          >
            Analyze
          </button>
        </form>
      </header>

      {/* Quick Select Chips */}
      <div className="mb-6 flex flex-wrap items-center gap-2 text-xs">
        <span className="text-zinc-500">Quick Focus:</span>
        {QUICK_CHIPS.map((chip) => (
          <button
            key={chip}
            onClick={() => handleChipClick(chip)}
            className={`rounded-lg border px-2.5 py-1 transition-colors cursor-pointer ${
              query === chip
                ? "border-cyan-500/50 bg-cyan-500/10 text-cyan-300 font-medium"
                : "border-zinc-800 bg-zinc-900/60 text-zinc-400 hover:border-zinc-700 hover:text-zinc-200"
            }`}
          >
            {chip}
          </button>
        ))}
      </div>

      {/* State 1: Error State */}
      {error && (
        <div className="mb-6 rounded-xl border border-red-500/30 bg-red-500/10 p-4 text-xs text-red-300 flex items-center justify-between">
          <span>Error connecting to backend services: {error}</span>
          <button
            onClick={() => executeSearch(query)}
            className="rounded-lg bg-red-600 px-3 py-1 font-semibold text-white hover:bg-red-500 cursor-pointer"
          >
            Retry
          </button>
        </div>
      )}

      {/* State 2: Loading Skeleton */}
      {loading && !data && (
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-12 animate-pulse">
          <div className="h-96 rounded-2xl bg-zinc-900 lg:col-span-7"></div>
          <div className="h-96 rounded-2xl bg-zinc-900 lg:col-span-5"></div>
          <div className="h-44 rounded-2xl bg-zinc-900 lg:col-span-12"></div>
        </div>
      )}

      {/* State 3: Populated High-Density Bento Grid */}
      {data && (
        <div className="space-y-4">
          {/* Active Target Info Header */}
          <div className="flex flex-wrap items-center justify-between rounded-xl border border-zinc-800/80 bg-zinc-900/40 px-4 py-2.5 text-xs text-zinc-400">
            <div className="flex items-center gap-2">
              <span className="font-bold text-white text-sm">{data.location.name}</span>
              <span>({data.location.state})</span>
              <span className="rounded bg-zinc-800 px-1.5 py-0.5 text-[10px] text-zinc-300">
                {data.location.eco_zone}
              </span>
            </div>
            <div className="flex items-center gap-4 text-[11px]">
              <span>Lat: {data.location.latitude}° N, Lon: {data.location.longitude}° E</span>
              <span className="text-zinc-500">Updated: {new Date(data.metadata.timestamp).toLocaleTimeString()}</span>
            </div>
          </div>

          {/* Row 1: Map (7 cols) + Wildfire Risk Card (5 cols) */}
          <div className="grid grid-cols-1 gap-4 lg:grid-cols-12">
            <div className="h-[420px] lg:col-span-7">
              <RegionMap
                selectedLocation={{
                  lat: data.location.latitude,
                  lon: data.location.longitude,
                  name: data.location.name
                }}
                activeFires={fires}
              />
            </div>
            <div className="lg:col-span-5">
              <WildfireRiskCard risk={data.wildfire_assessment} />
            </div>
          </div>

          {/* Row 2: Live Weather Bar */}
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
