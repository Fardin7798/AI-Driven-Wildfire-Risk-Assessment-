import { useEffect, useState } from 'react'
import { api } from '../lib/api'
import type { Region, Preparedness } from '../types'
import { RiskBadge } from '../components/RiskBadge'

export default function PreparednessPage() {
  const [regions, setRegions] = useState<Region[] | null>(null)
  const [selected, setSelected] = useState<string | null>(null)
  const [prep, setPrep] = useState<Preparedness | null>(null)

  useEffect(() => {
    api.regions().then((r) => {
      setRegions(r)
      if (r.length > 0) setSelected(r[0].region_id)
    })
  }, [])

  useEffect(() => {
    if (selected) api.preparedness(selected).then(setPrep)
  }, [selected])

  if (!regions) return <div className="p-8 text-charcoal/50">Loading…</div>

  return (
    <div className="px-8 py-8">
      <h1 className="font-display text-3xl font-semibold text-charcoal">
        Preparedness
      </h1>
      <p className="mt-1 text-sm text-charcoal/60">
        Safety guidance and evacuation resources by region.
      </p>

      <div className="mt-6 flex gap-2">
        {regions.map((r) => (
          <button
            key={r.region_id}
            onClick={() => setSelected(r.region_id)}
            className={`rounded-full border px-4 py-1.5 text-sm font-medium transition-colors ${
              selected === r.region_id
                ? 'border-charcoal bg-charcoal text-paper'
                : 'border-charcoal/20 text-charcoal/70 hover:border-charcoal/40'
            }`}
          >
            {r.name}
          </button>
        ))}
      </div>

      {prep && (
        <div className="mt-8 max-w-2xl">
          <div className="mb-6 flex items-center gap-3">
            <span className="text-sm text-charcoal/60">Current risk:</span>
            <RiskBadge level={prep.current_risk_level} />
          </div>

          <h2 className="font-display text-lg font-semibold text-charcoal">
            Safety tips
          </h2>
          <ul className="mt-3 space-y-2">
            {prep.tips.map((tip, i) => (
              <li key={i} className="flex gap-2 text-sm text-charcoal/80">
                <span className="text-fire">•</span>
                {tip}
              </li>
            ))}
          </ul>

          <h2 className="mt-8 font-display text-lg font-semibold text-charcoal">
            Resources
          </h2>
          <ul className="mt-3 space-y-2">
            {prep.evacuation_resources.map((res, i) => (
              <li key={i}>
                <a
                  href={res.url}
                  target="_blank"
                  rel="noreferrer"
                  className="text-sm font-medium text-fire hover:underline"
                >
                  {res.title}
                </a>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  )
}
