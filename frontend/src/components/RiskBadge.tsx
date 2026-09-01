const LEVEL_STYLES: Record<string, string> = {
  Low: 'bg-sage/15 text-sage border-sage/30',
  Moderate: 'bg-amber/15 text-amber border-amber/40',
  High: 'bg-fire/15 text-fire border-fire/40',
  Extreme: 'bg-severe/15 text-severe border-severe/40',
}

export function RiskBadge({ level }: { level: string }) {
  const style = LEVEL_STYLES[level] ?? 'bg-charcoal/10 text-charcoal border-charcoal/20'
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full border px-3 py-1 text-sm font-medium ${style}`}
    >
      <span className="h-1.5 w-1.5 rounded-full bg-current" />
      {level}
    </span>
  )
}

export function aqiCategoryColor(category: string): string {
  const map: Record<string, string> = {
    Good: 'text-sage',
    Satisfactory: 'text-sage',
    Moderate: 'text-amber',
    Poor: 'text-fire',
    'Very Poor': 'text-fire-dark',
    Severe: 'text-severe',
  }
  return map[category] ?? 'text-charcoal'
}
