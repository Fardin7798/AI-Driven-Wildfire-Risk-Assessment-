export interface District {
  id: string
  name: string
  state: string
  lat: number
  lon: number
  zone: string
}

export interface WeatherData {
  temperature: number
  humidity: number
  wind_speed: number
  precipitation: number
  weather_code: number
  timestamp: string
}

export interface Hotspot {
  lat: number
  lon: number
  brightness: number
  frp: number
  confidence: string
  acq_date: string
  acq_time: string
  daynight: string
  distance_km?: number
}

export interface WildfireAssessment {
  fwi_score: number
  risk_level: 'Low' | 'Moderate' | 'High' | 'Very High' | 'Extreme'
  color: string
  badge: string
  ffmc: number
  isi: number
  key_drivers: string[]
  nearby_satellite_fires_50km: number
  closest_active_fire_km: number | null
  active_hotspots: Hotspot[]
}

export interface ForecastPoint {
  time: string
  aqi: number
  pm2_5: number
  pm10: number
  wildfire_smoke_pm10: number
}

export interface AirQualityData {
  cpcb_aqi: number
  category: 'Good' | 'Satisfactory' | 'Moderate' | 'Poor' | 'Very Poor' | 'Severe'
  color: string
  badge: string
  pollutants: {
    pm2_5: number
    pm10: number
    co: number
    no2: number
    so2: number
    o3: number
  }
  forecast_72h: ForecastPoint[]
}

export interface AdvisoryItem {
  type: string
  title: string
  message: string
  urgency: 'critical' | 'warning' | 'danger'
}

export interface EmergencyContact {
  name: string
  number: string
  desc: string
}

export interface CommunityPreparedness {
  status: 'normal' | 'alert'
  advisories: AdvisoryItem[]
  recommended_actions: string[]
  emergency_contacts: EmergencyContact[]
}

export interface UnifiedSearchResponse {
  location: {
    name: string
    state: string
    latitude: number
    longitude: number
    eco_zone: string
  }
  weather: WeatherData
  wildfire_assessment: WildfireAssessment
  air_quality: AirQualityData
  community_preparedness: CommunityPreparedness
  metadata: {
    standards: string[]
    timestamp: string
    database_sync?: string
  }
}

export interface GeoJSONFeature {
  type: 'Feature'
  geometry: {
    type: 'Point'
    coordinates: [number, number]
  }
  properties: {
    brightness: number
    frp: number
    confidence: string
    acq_date: string
    acq_time: string
  }
}

export interface GeoJSONFeatureCollection {
  type: 'FeatureCollection'
  features: GeoJSONFeature[]
}

export interface TelemetryLog {
  id: string
  district_name: string
  state: string
  lat: number
  lon: number
  eco_zone: string
  fwi_score: number
  risk_level: string
  cpcb_aqi: number
  aqi_category: string
  nearby_fires_50km: number
  closest_fire_km: number | null
  temperature: number
  humidity: number
  wind_speed: number
  created_at: string
}
