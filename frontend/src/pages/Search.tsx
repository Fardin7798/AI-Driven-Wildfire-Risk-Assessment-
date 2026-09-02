import { useState, type FormEvent } from 'react'
import { api } from '../lib/api'
import type { SearchResult } from '../types'
import { RiskBadge } from '../components/RiskBadge'
import { Card, CardContent } from '../components/ui/card'

export default function SearchPage() {
  const [query, setQuery] = useState('')
  const [result, setResult] = useState<SearchResult | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function handleSearch(e: FormEvent) {
    e.preventDefault()
    if (!query.trim()) return
    setLoading(true)
    setError(null)
    setResult(null)
    try {
      const r = await api.search(query.trim())
      setResult(r)
    } catch {
      setError(`Couldn't find "${query}" — check the spelling, or try a bigger nearby city.`)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="px-8 py-8">
      <h1 className="font-display text-3xl font-semibold text-charcoal">
        Search any city in India
      </h1>
      <p className="mt-1 text-sm text-charcoal/60">
        Live fire-risk and AQI lookup for any Indian city — not just the
        tracked regions on the dashboard.
      </p>

      <form onSubmit={handleSearch} className="mt-6 flex max-w-md gap-2">
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="e.g. Jaipur, Nagpur, Mumbai…"
          className="flex-1 rounded-lg border border-charcoal/20 bg-white/60 px-4 py-2 text-sm text-charcoal placeholder:text-charcoal/40 focus:border-fire focus:outline-none"
        />
        <button
          type="submit"
          disabled={loading}
          className="rounded-lg bg-charcoal px-5 py-2 text-sm font-medium text-paper hover:bg-charcoal/90 disabled:opacity-50"
        >
          {loading ? 'Searching…' : 'Search'}
        </button>
      </form>

      {error && <p className="mt-6 text-sm text-severe">{error}</p>}

      {result && <SearchResultCard result={result} />}
    </div>
  )
}

function SearchResultCard({ result }: { result: SearchResult }) {
  const scorePct = result.risk_score !== null ? Math.round(result.risk_score * 100) : null
  return (
    <div className="mt-8 max-w-2xl">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="font-display text-2xl font-semibold text-charcoal">
            {result.resolved_location.name}, {result.resolved_location.state}
          </h2>
          <p className="text-xs text-charcoal/50">
            {result.resolved_location.lat.toFixed(3)}, {result.resolved_location.lon.toFixed(3)}
          </p>
        </div>
        {result.risk_level && <RiskBadge level={result.risk_level} />}
      </div>

      <div className="mt-5 grid grid-cols-2 gap-4 sm:grid-cols-4">
        <Card>
          <CardContent>
            <p className="text-xs font-medium uppercase tracking-wide text-charcoal/40">Risk score</p>
            <p className="mt-1 font-display text-xl font-semibold text-charcoal">
              {scorePct !== null ? scorePct : '—'}
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardContent>
            <p className="text-xs font-medium uppercase tracking-wide text-charcoal/40">AQI</p>
            <p className="mt-1 font-display text-xl font-semibold text-charcoal">
              {result.aqi ? result.aqi.current_aqi : '—'}
            </p>
            {result.aqi && <p className="text-xs text-charcoal/50">{result.aqi.category}</p>}
          </CardContent>
        </Card>
        <Card>
          <CardContent>
            <p className="text-xs font-medium uppercase tracking-wide text-charcoal/40">Temp</p>
            <p className="mt-1 font-display text-xl font-semibold text-charcoal">
              {result.weather.temp}°C
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardContent>
            <p className="text-xs font-medium uppercase tracking-wide text-charcoal/40">Humidity</p>
            <p className="mt-1 font-display text-xl font-semibold text-charcoal">
              {result.weather.humidity}%
            </p>
          </CardContent>
        </Card>
      </div>

      {!result.aqi && (
        <p className="mt-4 text-xs text-charcoal/50">
          No CPCB monitoring station found near {result.resolved_location.name} —
          AQI isn't available for this location.
        </p>
      )}

      <p className="mt-6 text-xs text-charcoal/40">{result.note}</p>
    </div>
  )
}
