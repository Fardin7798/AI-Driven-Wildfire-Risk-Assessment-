import { useEffect, useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import {
  LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid,
} from 'recharts'
import { api } from '../lib/api'
import type { Region, RiskResponse, AqiResponse, TrendsResponse } from '../types'
import { RiskBadge } from '../components/RiskBadge'
import { Card, CardContent } from '../components/ui/card'

export default function RegionDetail() {
  const { id } = useParams<{ id: string }>()
  const [region, setRegion] = useState<Region | null>(null)
  const [risk, setRisk] = useState<RiskResponse | null>(null)
  const [aqi, setAqi] = useState<AqiResponse | null>(null)
  const [trends, setTrends] = useState<TrendsResponse | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!id) return
    Promise.all([api.region(id), api.risk(id), api.aqi(id), api.trends(id)])
      .then(([r, risk, aqi, trends]) => {
        setRegion(r)
        setRisk(risk)
        setAqi(aqi)
        setTrends(trends)
      })
      .catch((e) => setError(e.message))
  }, [id])

  if (error) return <div className="p-8 text-severe">{error}</div>
  if (!region || !risk || !aqi || !trends) {
    return <div className="p-8 text-charcoal/50">Loading…</div>
  }

  return (
    <div className="px-8 py-8">
      <Link to="/" className="text-sm text-charcoal/50 hover:text-charcoal">
        ← Back to dashboard
      </Link>
      <div className="mt-2 flex items-center justify-between">
        <div>
          <h1 className="font-display text-3xl font-semibold text-charcoal">
            {region.name}, {region.state}
          </h1>
          <p className="text-sm text-charcoal/50">
            Updated {new Date(region.last_updated).toLocaleString('en-IN')}
          </p>
        </div>
        <RiskBadge level={risk.current.risk_level} />
      </div>

      <div className="mt-8 grid grid-cols-1 gap-4 md:grid-cols-3">
        <StatCard label="Fire risk score" value={risk.current.risk_score.toFixed(3)} sub={risk.current.model_version} />
        <StatCard label="Current AQI" value={String(aqi.current_aqi)} sub={aqi.category} />
        <StatCard label="Dominant pollutant" value={aqi.dominant_pollutant} sub="" />
      </div>

      {aqi.forecast.length > 0 && (
        <section className="mt-8">
          <h2 className="mb-3 font-display text-lg font-semibold text-charcoal">
            AQI forecast (next {aqi.forecast.length} days)
          </h2>
          <p className="mb-3 text-xs text-charcoal/50">{aqi.forecast_note}</p>
          <div className="rounded-xl border border-charcoal/10 bg-white/40 p-4">
            <ForecastChart forecast={aqi.forecast} />
          </div>
        </section>
      )}

      <section className="mt-8">
        <h2 className="mb-3 font-display text-lg font-semibold text-charcoal">
          Historical trend
        </h2>
        <p className="mb-3 text-xs text-charcoal/50">{trends.note}</p>
        <div className="rounded-xl border border-charcoal/10 bg-white/40 p-4">
          <TrendChart data={trends.data} />
        </div>
      </section>
    </div>
  )
}

function StatCard({ label, value, sub }: { label: string; value: string; sub: string }) {
  return (
    <Card>
      <CardContent>
        <p className="text-xs font-medium uppercase tracking-wide text-charcoal/40">
          {label}
        </p>
        <p className="mt-1 font-display text-2xl font-semibold text-charcoal">{value}</p>
        {sub && <p className="text-xs text-charcoal/50">{sub}</p>}
      </CardContent>
    </Card>
  )
}

function ForecastChart({ forecast }: { forecast: AqiResponse['forecast'] }) {
  const data = forecast.map((f) => ({
    date: new Date(f.timestamp).toLocaleDateString('en-IN', { month: 'short', day: 'numeric' }),
    predicted: f.predicted_aqi,
    lower: f.lower_bound,
    upper: f.upper_bound,
  }))
  return (
    <ResponsiveContainer width="100%" height={220}>
      <LineChart data={data}>
        <CartesianGrid strokeDasharray="3 3" stroke="#1B2E2815" />
        <XAxis dataKey="date" stroke="#1B2E2860" fontSize={12} />
        <YAxis stroke="#1B2E2860" fontSize={12} />
        <Tooltip />
        <Line type="monotone" dataKey="upper" stroke="#E8B341" strokeDasharray="4 4" dot={false} />
        <Line type="monotone" dataKey="predicted" stroke="#C4622D" strokeWidth={2} />
        <Line type="monotone" dataKey="lower" stroke="#4A7C6E" strokeDasharray="4 4" dot={false} />
      </LineChart>
    </ResponsiveContainer>
  )
}

function TrendChart({ data }: { data: TrendsResponse['data'] }) {
  if (data.length === 0) {
    return (
      <p className="py-8 text-center text-sm text-charcoal/40">
        No historical data yet — the pipeline just started collecting.
      </p>
    )
  }
  return (
    <ResponsiveContainer width="100%" height={220}>
      <LineChart data={data}>
        <CartesianGrid strokeDasharray="3 3" stroke="#1B2E2815" />
        <XAxis dataKey="date" stroke="#1B2E2860" fontSize={12} />
        <YAxis yAxisId="aqi" stroke="#C4622D" fontSize={12} />
        <YAxis yAxisId="risk" orientation="right" domain={[0, 1]} stroke="#4A7C6E" fontSize={12} />
        <Tooltip />
        {data.some((d) => d.aqi !== undefined) && (
          <Line yAxisId="aqi" type="monotone" dataKey="aqi" stroke="#C4622D" strokeWidth={2} name="AQI" />
        )}
        {data.some((d) => d.risk_score !== undefined) && (
          <Line yAxisId="risk" type="monotone" dataKey="risk_score" stroke="#4A7C6E" strokeWidth={2} name="Risk score" />
        )}
      </LineChart>
    </ResponsiveContainer>
  )
}
