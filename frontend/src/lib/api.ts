import type {
  Region,
  RiskResponse,
  AqiResponse,
  Alert,
  TrendsResponse,
  Preparedness,
  SearchResult,
} from '../types'

// In dev, Vite proxies /api -> the live Render backend (see vite.config.ts).
// In production build, set VITE_API_BASE to the backend URL directly.
const BASE = import.meta.env.VITE_API_BASE ?? '/api'

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`)
  if (!res.ok) {
    throw new Error(`API error ${res.status} on ${path}`)
  }
  return res.json()
}

export const api = {
  regions: () => get<Region[]>('/regions'),
  region: (id: string) => get<Region & { geometry: string }>(`/regions/${id}`),
  risk: (id: string) => get<RiskResponse>(`/risk/${id}`),
  aqi: (id: string) => get<AqiResponse>(`/aqi/${id}`),
  alerts: () => get<Alert[]>('/alerts'),
  trends: (id: string, days = 30) =>
    get<TrendsResponse>(`/trends/${id}?days=${days}`),
  preparedness: (id: string) => get<Preparedness>(`/preparedness/${id}`),
  search: (city: string) => get<SearchResult>(`/search?city=${encodeURIComponent(city)}`),
}
