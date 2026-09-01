import { Link } from 'react-router-dom'
import type { Region, Alert } from '../types'
import { RiskBadge } from './RiskBadge'
import { Card, CardContent } from './ui/card'

export function Hero({ featured, score }: { featured: Region; score: number | null }) {
  const scorePct = score !== null ? Math.round(score * 100) : null
  return (
    <div className="grid grid-cols-1 items-center gap-8 rounded-2xl border border-charcoal/10 bg-white/40 p-8 md:grid-cols-[1.2fr_1fr]">
      <div>
        <p className="text-xs font-medium uppercase tracking-wide text-charcoal/40">
          Highest current risk
        </p>
        <h2 className="mt-2 font-display text-3xl font-semibold text-charcoal">
          {featured.name}, {featured.state}
        </h2>
        <div className="mt-4 flex items-center gap-3">
          <span className="font-display text-6xl font-semibold text-fire">
            {scorePct !== null ? scorePct : '—'}
          </span>
          <div>
            <RiskBadge level={featured.current_risk_level} />
            <p className="mt-1 text-xs text-charcoal/50">
              Updated {new Date(featured.last_updated).toLocaleString('en-IN')}
            </p>
          </div>
        </div>
        <Link
          to={`/region/${featured.region_id}`}
          className="mt-6 inline-block rounded-lg bg-charcoal px-4 py-2 text-sm font-medium text-paper hover:bg-charcoal/90"
        >
          View region detail
        </Link>
      </div>
      <div
        className="h-48 rounded-xl md:h-full"
        style={{
          background:
            'radial-gradient(circle at 30% 30%, var(--color-fire) 0%, var(--color-fire-dark) 45%, var(--color-charcoal) 100%)',
        }}
      />
    </div>
  )
}

export function AlertBanner({ alerts }: { alerts: Alert[] }) {
  return (
    <div className="mt-6 rounded-xl border border-fire/30 bg-fire/10 p-4">
      <p className="text-sm font-medium text-fire-dark">
        {alerts.length} active alert{alerts.length > 1 ? 's' : ''}
      </p>
      <ul className="mt-2 space-y-1">
        {alerts.map((a, i) => (
          <li key={i} className="text-sm text-charcoal/80">
            <span className="font-medium">{a.region_id}:</span> {a.message}
          </li>
        ))}
      </ul>
    </div>
  )
}

export function RegionCard({ region }: { region: Region }) {
  return (
    <Link to={`/region/${region.region_id}`}>
      <Card className="transition-colors hover:border-charcoal/25">
        <CardContent>
          <div className="flex items-start justify-between">
            <div>
              <h3 className="font-display text-lg font-semibold text-charcoal">
                {region.name}
              </h3>
              <p className="text-xs text-charcoal/50">{region.state}</p>
            </div>
            <RiskBadge level={region.current_risk_level} />
          </div>
          <div className="mt-4 flex items-baseline gap-1.5">
            <span className="font-display text-2xl font-semibold text-charcoal">
              {region.current_aqi}
            </span>
            <span className="text-xs text-charcoal/50">AQI</span>
          </div>
        </CardContent>
      </Card>
    </Link>
  )
}
