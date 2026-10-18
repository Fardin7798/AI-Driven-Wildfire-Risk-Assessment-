import type {
  District,
  UnifiedSearchResponse,
  GeoJSONFeatureCollection,
} from '../types'

export const API_BASE =
  import.meta.env.VITE_API_BASE ||
  (import.meta.env.DEV ? 'http://localhost:8000' : 'https://wildfire-aqi-backend.onrender.com')

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`)
  if (!res.ok) {
    throw new Error(`API error ${res.status}: ${res.statusText}`)
  }
  return res.json()
}

export const api = {
  getDistricts: (search?: string) =>
    get<{ total: number; districts: District[] }>(
      search ? `/api/v1/districts?search=${encodeURIComponent(search)}` : '/api/v1/districts'
    ),
  search: (query?: string, lat?: number, lon?: number) => {
    const params = new URLSearchParams()
    if (query) params.append('query', query)
    if (lat !== undefined) params.append('lat', String(lat))
    if (lon !== undefined) params.append('lon', String(lon))
    return get<UnifiedSearchResponse>(`/api/v1/search?${params.toString()}`)
  },
  getActiveFires: () =>
    get<GeoJSONFeatureCollection>('/api/v1/fires/active?format=geojson'),
  getHealth: () =>
    get<{
      status: string
      service: string
      districts_loaded: number
      database?: {
        status: string
        provider: string
        project_ref: string
        regions_in_db: number
      }
    }>('/health'),
}
