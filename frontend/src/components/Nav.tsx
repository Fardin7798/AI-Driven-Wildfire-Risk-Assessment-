import { NavLink } from 'react-router-dom'

export function Nav() {
  const linkClass = ({ isActive }: { isActive: boolean }) =>
    `block rounded-lg px-3 py-2 text-sm font-medium transition-colors ${
      isActive
        ? 'bg-charcoal text-paper'
        : 'text-charcoal/70 hover:bg-charcoal/5 hover:text-charcoal'
    }`

  return (
    <nav className="flex h-full flex-col border-r border-charcoal/10 bg-paper px-4 py-6">
      <div className="mb-8 px-3">
        <h1 className="font-display text-lg font-semibold leading-tight text-charcoal">
          Wildfire &amp; AQI
        </h1>
        <p className="text-xs text-charcoal/50">India — live monitoring</p>
      </div>
      <div className="flex flex-col gap-1">
        <NavLink to="/" end className={linkClass}>
          Dashboard
        </NavLink>
        <NavLink to="/preparedness" className={linkClass}>
          Preparedness
        </NavLink>
      </div>
    </nav>
  )
}
