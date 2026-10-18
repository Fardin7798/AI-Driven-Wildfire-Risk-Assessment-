import { useState, useEffect, useRef } from 'react'
import {
  Search,
  AlertCircle,
  RefreshCw,
  MapPin,
  Sparkles,
  Flame,
  Layers,
  X,
  Compass,
} from 'lucide-react'
import { api } from '../lib/api'
import type {
  UnifiedSearchResponse,
  GeoJSONFeatureCollection,
  District
} from '../types'
import { RegionMap } from '../components/RegionMap'
import {
  RiskGaugeCard,
  WeatherBarCard,
  AirQualityCard,
  ForecastChartCard,
  EmergencyCard
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
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [isWakingUp, setIsWakingUp] = useState(false)
  const wakeupTimerRef = useRef<any>(null)

  useEffect(() => {
    api.getDistricts()
      .then((res) => setDistricts(res.districts))
      .catch(() => {})

    api.getActiveFires()
      .then((geo) => setFires(geo))
      .catch(() => {})

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
    } catch (err: any) {
      clearTimeout(wakeupTimerRef.current)
      setIsWakingUp(false)
      const msg = err?.message || 'Something went wrong. Please try again.'
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
                  AeroRisk India
                </h1>
              </div>
              <p className="text-[11px] text-slate-500">
                Wildfire risk, air quality and safety tips for your area
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
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-[1500px] p-4 sm:p-6 lg:p-8 space-y-5">
        {/* Quick Focus Targets Strip */}
        <FadeUp delay={0.05} className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-200 pb-4">
          <div className="flex flex-wrap items-center gap-1.5 text-xs">
            <span className="mr-1 flex items-center gap-1 font-mono text-[10px] uppercase tracking-wider text-slate-500 font-bold">
              <Sparkles className="h-3 w-3 text-sky-600" />
              Popular places:
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

        </FadeUp>

        {/* Cold Start Alert */}
        {isWakingUp && loading && (
          <FadeUp delay={0.1} className="rounded-2xl border border-sky-200 bg-sky-50 p-4 text-xs text-sky-900 flex items-center justify-between shadow-sm">
            <div className="flex items-center gap-3">
              <div className="h-5 w-5 animate-spin rounded-full border-2 border-sky-600 border-t-transparent shrink-0" />
              <div>
                <p className="font-bold text-sky-900">Loading latest data</p>
                <p className="text-sky-700 text-[11px]">Fetching fire, weather and air quality for your area. This can take up to 30 seconds the first time.</p>
              </div>
            </div>
          </FadeUp>
        )}

        {error && (
          <FadeUp delay={0.1} className="rounded-2xl border border-red-200 bg-red-50 p-4 text-xs text-red-900 flex items-center justify-between shadow-sm">
            <div className="flex items-center gap-3">
              <AlertCircle className="h-5 w-5 text-red-600 shrink-0" />
              <div>
                <p className="font-bold">Couldn't load data</p>
                <p className="text-red-700 text-[11px]">{error}</p>
              </div>
            </div>
            <button
              onClick={() => executeSearch(query)}
              className="flex items-center gap-1.5 rounded-xl bg-red-600 px-3.5 py-2 font-bold text-white hover:bg-red-700 transition-all cursor-pointer shadow-sm"
            >
              <RefreshCw className="h-3.5 w-3.5" />
              <span>Try again</span>
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
              <h3 className="text-lg font-bold text-slate-900">Search a place to get started</h3>
              <p className="mt-1 text-xs text-slate-500 max-w-sm">
                Type any Indian city or district, or pick a popular place above.
              </p>
              <button
                onClick={() => handleChipClick('Jalgaon / Bhusawal')}
                className="mt-5 rounded-xl bg-sky-600 px-5 py-2.5 text-xs font-bold text-white hover:bg-sky-700 transition-all cursor-pointer shadow-sm"
              >
                Show Jalgaon / Bhusawal
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
                    Area type: <span className="text-slate-800 font-semibold">{data.location.eco_zone}</span>
                  </p>
                </div>
              </div>

              <div className="flex items-center gap-2.5 text-xs font-mono">
                <span className="rounded-lg bg-slate-50 border border-slate-200 px-3 py-1 text-slate-700 font-semibold">
                  Fire danger: <span className="font-bold text-slate-900">{data.wildfire_assessment.fwi_score}</span>
                </span>
                <span className="rounded-lg bg-slate-50 border border-slate-200 px-3 py-1 text-slate-700 font-semibold">
                  AQI: <span className="font-bold text-slate-900">{data.air_quality.cpcb_aqi}</span>
                </span>
              </div>
            </FadeUp>

            {/* Post 1 Bento Grid (Nordic Cool Slate & Sapphire) */}
            <BentoGrid>
              {/* Card 1: Geospatial Fire & Buffer Map (2 cols) */}
              <BentoGridItem
                className="lg:col-span-2 min-h-[460px]"
                spotlightColor="rgba(2, 132, 199, 0.05)"
                eyebrow="Nearby fires"
                action={
                  <div className="flex items-center gap-2">
                    <span className="font-mono text-[9px] uppercase tracking-wider text-sky-800 bg-sky-50 border border-sky-200 px-2 py-0.5 rounded-full flex items-center gap-1.5 font-bold">
                      <i className="h-1.5 w-1.5 rounded-full bg-sky-600 animate-pulse" />
                      50 km area
                    </span>
                    <span className="font-mono text-[9px] text-slate-600 bg-slate-50 border border-slate-200 px-2 py-0.5 rounded-full font-semibold">
                      NASA satellite
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
                title="Fires near you"
                description="Active fires detected by satellite, with a 50 km circle around your location."
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

            </BentoGrid>
          </div>
        )}
      </main>
      <Footer />
    </div>
  )
}
