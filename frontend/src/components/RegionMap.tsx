import { useEffect, useRef } from 'react'
import * as maplibregl from 'maplibre-gl'
import 'maplibre-gl/dist/maplibre-gl.css'
import type { GeoJSONFeatureCollection } from '../types'

interface Props {
  selectedLocation?: { lat: number; lon: number; name: string }
  activeFires?: GeoJSONFeatureCollection
}

const ESRI_LIGHT_GRAY_STYLE: any = {
  version: 8,
  sources: {
    'esri-light-base': {
      type: 'raster',
      tiles: [
        'https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Light_Gray_Base/MapServer/tile/{z}/{y}/{x}'
      ],
      tileSize: 256,
      attribution: 'Esri, DeLorme, NAVTEQ, TomTom'
    },
    'esri-light-reference': {
      type: 'raster',
      tiles: [
        'https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Light_Gray_Reference/MapServer/tile/{z}/{y}/{x}'
      ],
      tileSize: 256
    }
  },
  layers: [
    {
      id: 'esri-light-base-layer',
      type: 'raster',
      source: 'esri-light-base',
      minzoom: 0,
      maxzoom: 16
    }
  ]
}

function createGeoJSONCircle(center: [number, number], radiusInKm: number, points = 64) {
  const coords = {
    latitude: center[1],
    longitude: center[0]
  }
  const km = radiusInKm
  const ret: [number, number][] = []
  const distanceX = km / (111.32 * Math.cos((coords.latitude * Math.PI) / 180))
  const distanceY = km / 110.574

  for (let i = 0; i < points; i++) {
    const theta = (i / points) * (2 * Math.PI)
    const x = distanceX * Math.cos(theta)
    const y = distanceY * Math.sin(theta)
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
      style: ESRI_LIGHT_GRAY_STYLE,
      center: initialCenter as [number, number],
      zoom: initialZoom,
      attributionControl: false
    })

    map.addControl(new maplibregl.NavigationControl({ showCompass: false }), 'top-right')

    const resizeObserver = new ResizeObserver(() => {
      map.resize()
    })
    resizeObserver.observe(containerRef.current)

    map.on('load', () => {
      mapRef.current = map

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
          'fill-color': '#0284c7',
          'fill-opacity': 0.08
        }
      })

      map.addLayer({
        id: 'proximity-buffer-line',
        type: 'line',
        source: 'proximity-buffer',
        paint: {
          'line-color': '#0284c7',
          'line-width': 1.5,
          'line-dasharray': [2, 2],
          'line-opacity': 0.8
        }
      })

      map.addSource('nasa-fires', {
        type: 'geojson',
        data: (activeFires && activeFires.features) ? activeFires as any : { type: 'FeatureCollection', features: [] }
      })

      map.addLayer({
        id: 'fires-glow',
        type: 'circle',
        source: 'nasa-fires',
        paint: {
          'circle-radius': 14,
          'circle-color': '#f97316',
          'circle-opacity': 0.25,
          'circle-blur': 0.8
        }
      })

      map.addLayer({
        id: 'fires-heat',
        type: 'circle',
        source: 'nasa-fires',
        paint: {
          'circle-radius': 5.5,
          'circle-color': '#ef4444',
          'circle-stroke-width': 1.5,
          'circle-stroke-color': '#ffffff'
        }
      })

      // Reference labels layer positioned on top of buffers
      map.addLayer({
        id: 'esri-light-reference-layer',
        type: 'raster',
        source: 'esri-light-reference',
        minzoom: 0,
        maxzoom: 16
      })

      map.on('click', 'fires-heat', (e) => {
        if (!e.features || !e.features[0]) return
        const props = e.features[0].properties as any
        const coords = (e.features[0].geometry as any).coordinates.slice()
        const kelvin = Number(props.brightness) || 300
        const celsius = (kelvin - 273.15).toFixed(1)
        const heatLevel = Number(celsius) > 55 ? 'Intense Thermal Anomaly' : Number(celsius) > 40 ? 'Active Surface Fire' : 'Elevated Heat Signature'
        const cert = props.confidence === 'high' ? 'High Satellite Certainty' : props.confidence === 'nominal' ? 'Verified Anomaly' : 'Preliminary'

        new maplibregl.Popup({ offset: 12, className: 'custom-light-popup' })
          .setLngLat(coords)
          .setHTML(`
            <div style="background:#ffffff; color:#0f172a; padding:10px 12px; border-radius:10px; border:1px solid #e2e8f0; font-family:sans-serif; font-size:11px; min-width:180px; box-shadow:0 10px 25px -5px rgba(0,0,0,0.1);">
              <div style="display:flex; align-items:center; gap:6px; margin-bottom:6px;">
                <span style="font-size:13px;">🔥</span>
                <strong style="color:#ef4444; font-size:12px;">NASA VIIRS Hotspot</strong>
              </div>
              <p style="margin:2px 0; color:#334155;">Radiant Heat: <strong style="color:#0284c7;">${celsius}°C</strong> <span style="color:#64748b; font-size:10px;">(${kelvin.toFixed(1)} K)</span></p>
              <p style="margin:2px 0; font-size:10px; color:#d97706; font-weight:600;">${heatLevel}</p>
              <p style="margin:2px 0; color:#475569; font-size:10px;">Confidence: <span style="color:#059669; font-weight:600;">${cert}</span></p>
              <p style="color:#94a3b8; font-size:9px; margin-top:5px; border-top:1px solid #e2e8f0; padding-top:4px;">Orbit: ${props.acq_date ?? 'Recent'} ${props.acq_time ?? ''} UTC</p>
            </div>
          `)
          .addTo(map)
      })

      map.on('mouseenter', 'fires-heat', () => {
        map.getCanvas().style.cursor = 'pointer'
      })
      map.on('mouseleave', 'fires-heat', () => {
        map.getCanvas().style.cursor = ''
      })

      map.resize()
    })

    return () => {
      resizeObserver.disconnect()
      map.remove()
      mapRef.current = null
    }
  }, [])

  useEffect(() => {
    if (!mapRef.current) return
    const source = mapRef.current.getSource('nasa-fires') as maplibregl.GeoJSONSource
    if (source && activeFires) {
      source.setData(activeFires as any)
    }
  }, [activeFires])

  useEffect(() => {
    if (!mapRef.current || !selectedLocation) return

    mapRef.current.flyTo({
      center: [selectedLocation.lon, selectedLocation.lat],
      zoom: 8,
      speed: 1.2,
      curve: 1.4,
      essential: true
    })

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
      <div class="absolute h-9 w-9 rounded-full bg-sky-500/20 animate-ping"></div>
      <div class="h-4 w-4 rounded-full border-2 border-white bg-sky-600 shadow-md shadow-sky-600/30"></div>
    `

    markerRef.current = new maplibregl.Marker({ element: pinEl })
      .setLngLat([selectedLocation.lon, selectedLocation.lat])
      .addTo(mapRef.current)

  }, [selectedLocation])

  return (
    <div className="relative h-full w-full min-h-[300px]">
      <div ref={containerRef} className="absolute inset-0 h-full w-full rounded-xl overflow-hidden" />
    </div>
  )
}
