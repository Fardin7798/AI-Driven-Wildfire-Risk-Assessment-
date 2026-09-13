import { useEffect, useRef } from 'react'
import * as maplibregl from 'maplibre-gl'
import 'maplibre-gl/dist/maplibre-gl.css'
import type { GeoJSONFeatureCollection } from '../types'

interface Props {
  selectedLocation?: { lat: number; lon: number; name: string }
  activeFires?: GeoJSONFeatureCollection
}

export function RegionMap({ selectedLocation, activeFires }: Props) {
  const containerRef = useRef<HTMLDivElement>(null)
  const mapRef = useRef<maplibregl.Map | null>(null)
  const markerRef = useRef<maplibregl.Marker | null>(null)

  useEffect(() => {
    if (!containerRef.current || mapRef.current) return

    const initialCenter = selectedLocation ? [selectedLocation.lon, selectedLocation.lat] : [78.9629, 20.5937]
    const initialZoom = selectedLocation ? 7 : 4.5

    const map = new maplibregl.Map({
      container: containerRef.current,
      style: 'https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json',
      center: initialCenter as [number, number],
      zoom: initialZoom,
      attributionControl: false
    })

    map.addControl(new maplibregl.NavigationControl(), 'top-right')

    map.on('load', () => {
      mapRef.current = map

      // Add NASA FIRMS Active Fires GeoJSON source
      if (activeFires && activeFires.features) {
        map.addSource('nasa-fires', {
          type: 'geojson',
          data: activeFires as any
        })

        // Glowing outer pulse
        map.addLayer({
          id: 'fires-glow',
          type: 'circle',
          source: 'nasa-fires',
          paint: {
            'circle-radius': 12,
            'circle-color': '#f97316',
            'circle-opacity': 0.25,
            'circle-blur': 0.8
          }
        })

        // Core satellite hotspot
        map.addLayer({
          id: 'fires-heat',
          type: 'circle',
          source: 'nasa-fires',
          paint: {
            'circle-radius': 5,
            'circle-color': '#ef4444',
            'circle-stroke-width': 1.5,
            'circle-stroke-color': '#ffffff'
          }
        })

        map.on('click', 'fires-heat', (e) => {
          if (!e.features || !e.features[0]) return
          const props = e.features[0].properties as any
          const coords = (e.features[0].geometry as any).coordinates.slice()
          new maplibregl.Popup({ offset: 10 })
            .setLngLat(coords)
            .setHTML(`
              <div class="p-1 text-xs text-zinc-900">
                <p class="font-bold text-red-600">NASA Active Fire Hotspot</p>
                <p>Brightness: ${props.brightness ?? 'N/A'} K</p>
                <p>Confidence: ${props.confidence ?? 'nominal'}</p>
                <p>Time: ${props.acq_time ?? 'N/A'}</p>
              </div>
            `)
            .addTo(map)
        })
      }
    })

    return () => {
      map.remove()
      mapRef.current = null
    }
  }, [])

  // Update active fires source dynamically
  useEffect(() => {
    if (!mapRef.current) return
    const source = mapRef.current.getSource('nasa-fires') as maplibregl.GeoJSONSource
    if (source && activeFires) {
      source.setData(activeFires as any)
    }
  }, [activeFires])

  // Fly to selected location and update pinpoint marker
  useEffect(() => {
    if (!mapRef.current || !selectedLocation) return

    mapRef.current.flyTo({
      center: [selectedLocation.lon, selectedLocation.lat],
      zoom: 8,
      speed: 1.2,
      curve: 1.4,
      essential: true
    })

    if (markerRef.current) {
      markerRef.current.remove()
    }

    const pinEl = document.createElement('div')
    pinEl.className = 'relative flex items-center justify-center'
    pinEl.innerHTML = `
      <div class="absolute h-8 w-8 rounded-full bg-cyan-500/20 animate-ping"></div>
      <div class="h-4 w-4 rounded-full border-2 border-white bg-cyan-400 shadow-lg shadow-cyan-500/50"></div>
    `

    const popup = new maplibregl.Popup({ offset: 15, closeButton: false }).setHTML(`
      <div class="text-xs font-semibold px-1 text-zinc-900">${selectedLocation.name}</div>
    `)

    markerRef.current = new maplibregl.Marker({ element: pinEl })
      .setLngLat([selectedLocation.lon, selectedLocation.lat])
      .setPopup(popup)
      .addTo(mapRef.current)

  }, [selectedLocation])

  return (
    <div className="relative h-full w-full overflow-hidden rounded-2xl border border-zinc-800 bg-zinc-950">
      <div ref={containerRef} className="h-full w-full min-h-[380px]" />
      <div className="absolute bottom-3 left-3 z-10 flex items-center gap-3 rounded-lg border border-zinc-800/80 bg-zinc-900/80 px-3 py-1.5 text-[11px] text-zinc-300 backdrop-blur-md">
        <span className="flex items-center gap-1.5">
          <span className="h-2.5 w-2.5 rounded-full bg-red-500 shadow-sm shadow-red-500/80 animate-pulse"></span>
          NASA Active Fire
        </span>
        <span className="h-3 w-[1px] bg-zinc-700"></span>
        <span className="flex items-center gap-1.5">
          <span className="h-2.5 w-2.5 rounded-full bg-cyan-400"></span>
          District Centroid
        </span>
      </div>
    </div>
  )
}
