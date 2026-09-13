import { useEffect, useRef } from 'react'
import * as maplibregl from 'maplibre-gl'
import 'maplibre-gl/dist/maplibre-gl.css'
import type { GeoJSONFeatureCollection } from '../types'

interface Props {
  selectedLocation?: { lat: number; lon: number; name: string }
  activeFires?: GeoJSONFeatureCollection
}

// Generate circular polygon GeoJSON for 50km buffer around a centroid
function createGeoJSONCircle(center: [number, number], radiusInKm: number, points = 64) {
  const coords = {
    latitude: center[1],
    longitude: center[0]
  }
  const km = radiusInKm
  const ret: [number, number][] = []
  const distanceX = km / (111.32 * Math.cos((coords.latitude * Math.PI) / 180))
  const distanceY = km / 110.574

  let theta: number
  let x: number
  let y: number
  for (let i = 0; i < points; i++) {
    theta = (i / points) * (2 * Math.PI)
    x = distanceX * Math.cos(theta)
    y = distanceY * Math.sin(theta)
    ret.push([coords.longitude + x, coords.latitude + y])
  }
  ret.push(ret[0])
  return {
    type: 'Feature' as const,
    geometry: {
      type: 'Polygon' as const,
      coordinates: [ret]
    },
    properties: {}
  }
}

export function RegionMap({ selectedLocation, activeFires }: Props) {
  const containerRef = useRef<HTMLDivElement>(null)
  const mapRef = useRef<maplibregl.Map | null>(null)
  const markerRef = useRef<maplibregl.Marker | null>(null)

  useEffect(() => {
    if (!containerRef.current || mapRef.current) return

    const initialCenter = selectedLocation ? [selectedLocation.lon, selectedLocation.lat] : [78.9629, 20.5937]
    const initialZoom = selectedLocation ? 7.5 : 4.5

    const map = new maplibregl.Map({
      container: containerRef.current,
      style: 'https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json',
      center: initialCenter as [number, number],
      zoom: initialZoom,
      attributionControl: false
    })

    map.addControl(new maplibregl.NavigationControl({ showCompass: false }), 'top-right')

    map.on('load', () => {
      mapRef.current = map

      // 1. Setup 50km proximity radius buffer layer
      const circleData = selectedLocation
        ? createGeoJSONCircle([selectedLocation.lon, selectedLocation.lat], 50)
        : { type: 'Feature', geometry: { type: 'Polygon', coordinates: [] }, properties: {} }

      map.addSource('proximity-buffer', {
        type: 'geojson',
        data: circleData as any
      })

      map.addLayer({
        id: 'proximity-buffer-fill',
        type: 'fill',
        source: 'proximity-buffer',
        paint: {
          'fill-color': '#06b6d4',
          'fill-opacity': 0.08
        }
      })

      map.addLayer({
        id: 'proximity-buffer-line',
        type: 'line',
        source: 'proximity-buffer',
        paint: {
          'line-color': '#06b6d4',
          'line-width': 1.5,
          'line-dasharray': [2, 2],
          'line-opacity': 0.6
        }
      })

      // 2. Setup NASA FIRMS Active Fires Layer
      if (activeFires && activeFires.features) {
        map.addSource('nasa-fires', {
          type: 'geojson',
          data: activeFires as any
        })

        // Glowing outer halo
        map.addLayer({
          id: 'fires-glow',
          type: 'circle',
          source: 'nasa-fires',
          paint: {
            'circle-radius': 14,
            'circle-color': '#f97316',
            'circle-opacity': 0.3,
            'circle-blur': 0.8
          }
        })

        // Intense thermal core
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

        // Click popup on fire hotspot
        map.on('click', 'fires-heat', (e) => {
          if (!e.features || !e.features[0]) return
          const props = e.features[0].properties as any
          const coords = (e.features[0].geometry as any).coordinates.slice()
          new maplibregl.Popup({ offset: 12, className: 'custom-dark-popup' })
            .setLngLat(coords)
            .setHTML(`
              <div style="background:#18181b; color:#f4f4f5; padding:8px 10px; border-radius:8px; border:1px solid #27272a; font-family:monospace; font-size:11px;">
                <p style="color:#ef4444; font-weight:bold; margin-bottom:4px;">🔥 NASA VIIRS Hotspot</p>
                <p>Brightness: <span style="color:#38bdf8;">${props.brightness ?? 'N/A'} K</span></p>
                <p>Confidence: <span style="color:#4ade80;">${props.confidence ?? 'nominal'}</span></p>
                <p style="color:#71717a; font-size:10px; margin-top:2px;">Acquired: ${props.acq_date ?? ''} ${props.acq_time ?? ''} UTC</p>
              </div>
            `)
            .addTo(map)
        })

        // Change cursor on hover
        map.on('mouseenter', 'fires-heat', () => {
          map.getCanvas().style.cursor = 'pointer'
        })
        map.on('mouseleave', 'fires-heat', () => {
          map.getCanvas().style.cursor = ''
        })
      }
    })

    return () => {
      map.remove()
      mapRef.current = null
    }
  }, [])

  // Dynamically update active fires GeoJSON source
  useEffect(() => {
    if (!mapRef.current) return
    const source = mapRef.current.getSource('nasa-fires') as maplibregl.GeoJSONSource
    if (source && activeFires) {
      source.setData(activeFires as any)
    }
  }, [activeFires])

  // Fly to selected location, update proximity circle & pin
  useEffect(() => {
    if (!mapRef.current || !selectedLocation) return

    mapRef.current.flyTo({
      center: [selectedLocation.lon, selectedLocation.lat],
      zoom: 8,
      speed: 1.2,
      curve: 1.4,
      essential: true
    })

    // Update 50km buffer source
    const bufferSource = mapRef.current.getSource('proximity-buffer') as maplibregl.GeoJSONSource
    if (bufferSource) {
      const circleData = createGeoJSONCircle([selectedLocation.lon, selectedLocation.lat], 50)
      bufferSource.setData(circleData as any)
    }

    if (markerRef.current) {
      markerRef.current.remove()
    }

    const pinEl = document.createElement('div')
    pinEl.className = 'relative flex items-center justify-center'
    pinEl.innerHTML = `
      <div class="absolute h-9 w-9 rounded-full bg-cyan-400/20 animate-ping"></div>
      <div class="h-4 w-4 rounded-full border-2 border-white bg-cyan-400 shadow-md shadow-cyan-400"></div>
    `

    markerRef.current = new maplibregl.Marker({ element: pinEl })
      .setLngLat([selectedLocation.lon, selectedLocation.lat])
      .addTo(mapRef.current)

  }, [selectedLocation])

  return (
    <div className="relative h-full w-full overflow-hidden rounded-2xl border border-zinc-800 bg-zinc-950">
      <div ref={containerRef} className="h-full w-full min-h-[380px]" />
      
      {/* Legend Widget Overlay */}
      <div className="absolute bottom-3 left-3 z-10 flex flex-wrap items-center gap-3 rounded-xl border border-zinc-800/90 bg-zinc-900/80 px-3.5 py-2 text-[11px] text-zinc-300 backdrop-blur-md">
        <span className="flex items-center gap-1.5 font-medium">
          <span className="relative flex h-2 w-2">
            <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-red-400 opacity-75"></span>
            <span className="relative inline-flex h-2 w-2 rounded-full bg-red-500"></span>
          </span>
          Active Fire (VIIRS 375m)
        </span>
        <span className="h-3 w-[1px] bg-zinc-700"></span>
        <span className="flex items-center gap-1.5 font-medium">
          <span className="h-2 w-2 rounded-full bg-cyan-400"></span>
          District Centroid
        </span>
        <span className="h-3 w-[1px] bg-zinc-700"></span>
        <span className="flex items-center gap-1.5 font-mono text-[10px] text-zinc-400">
          <span className="h-2 w-2 rounded-full border border-cyan-400 border-dashed"></span>
          50km Perimeter
        </span>
      </div>
    </div>
  )
}
