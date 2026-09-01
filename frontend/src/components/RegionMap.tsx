import { useEffect, useRef } from 'react'
import * as maplibregl from 'maplibre-gl'
import 'maplibre-gl/dist/maplibre-gl.css'
import { useNavigate } from 'react-router-dom'
import type { Region } from '../types'

const RISK_COLOR: Record<string, string> = {
  Low: '#4A7C6E',
  Moderate: '#E8B341',
  High: '#C4622D',
  Extreme: '#8B2E1F',
}

export function RegionMap({ regions }: { regions: Region[] }) {
  const containerRef = useRef<HTMLDivElement>(null)
  const mapRef = useRef<maplibregl.Map | null>(null)
  const navigate = useNavigate()

  useEffect(() => {
    if (!containerRef.current || mapRef.current || regions.length === 0) return

    const map = new maplibregl.Map({
      container: containerRef.current,
      style: 'https://basemaps.cartocdn.com/gl/positron-gl-style/style.json',
      center: [regions[0].centroid.lon, regions[0].centroid.lat],
      zoom: 4,
    })
    mapRef.current = map
    map.addControl(new maplibregl.NavigationControl(), 'top-right')

    const bounds = new maplibregl.LngLatBounds()

    regions.forEach((r) => {
      const el = document.createElement('div')
      el.style.width = '18px'
      el.style.height = '18px'
      el.style.borderRadius = '50%'
      el.style.border = '2px solid white'
      el.style.boxShadow = '0 1px 4px rgba(0,0,0,0.4)'
      el.style.cursor = 'pointer'
      el.style.backgroundColor = RISK_COLOR[r.current_risk_level] ?? '#1B2E28'

      const popup = new maplibregl.Popup({ offset: 14, closeButton: false }).setHTML(
        `<strong>${r.name}</strong><br/>${r.current_risk_level} risk · AQI ${r.current_aqi}`
      )

      new maplibregl.Marker({ element: el })
        .setLngLat([r.centroid.lon, r.centroid.lat])
        .setPopup(popup)
        .addTo(map)

      el.addEventListener('click', () => navigate(`/region/${r.region_id}`))
      bounds.extend([r.centroid.lon, r.centroid.lat])
    })

    if (regions.length > 1) {
      map.fitBounds(bounds, { padding: 60, maxZoom: 7 })
    }

    return () => {
      map.remove()
      mapRef.current = null
    }
  }, [regions, navigate])

  return <div ref={containerRef} className="h-96 w-full rounded-xl" />
}
