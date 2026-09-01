import { useEffect, useState } from 'react'
import { api } from '../lib/api'
import type { Region, Alert } from '../types'
import { Hero, AlertBanner, RegionCard } from '../components/DashboardBits'

export default function Home() {
  const [regions, setRegions] = useState<Region[] | null>(null)
  const [alerts, setAlerts] = useState<Alert[]>([])
  const [featuredScore, setFeaturedScore] = useState<number | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    Promise.all([api.regions(), api.alerts()])
      .then(([r, a]) => {
        setRegions(r)
        setAlerts(a)
        const featured = [...r].sort(
          (x, y) => riskWeight(y.current_risk_level) - riskWeight(x.current_risk_level)
        )[0]
        if (featured) {
          api.risk(featured.region_id).then((res) => setFeaturedScore(res.current.risk_score))
        }
      })
      .catch((e) => setError(e.message))
  }, [])

  if (error) {
    return (
      <div className="p-8">
        <p className="text-severe">Couldn't reach the API: {error}</p>
        <p className="mt-2 text-sm text-charcoal/60">
          The backend may be waking up from idle (free tier) — try refreshing in a moment.
        </p>
      </div>
    )
  }

  if (!regions) {
    return <div className="p-8 text-charcoal/50">Loading live data…</div>
  }

  const featured = [...regions].sort(
    (a, b) => riskWeight(b.current_risk_level) - riskWeight(a.current_risk_level)
  )[0]

  return (
    <div className="px-8 py-8">
      <Hero featured={featured} score={featuredScore} />
      {alerts.length > 0 && <AlertBanner alerts={alerts} />}
      <h2 className="mb-4 mt-10 font-display text-xl font-semibold text-charcoal">
        All regions
      </h2>
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {regions.map((r) => (
          <RegionCard key={r.region_id} region={r} />
        ))}
      </div>
    </div>
  )
}

function riskWeight(level: string) {
  return { Low: 0, Moderate: 1, High: 2, Extreme: 3 }[level] ?? 0
}
