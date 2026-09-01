export interface Region {
  region_id: string
  name: string
  state: string
  centroid: { lat: number; lon: number }
  current_risk_level: 'Low' | 'Moderate' | 'High' | 'Extreme'
  current_aqi: number
  last_updated: string
}

export interface RiskPoint {
  timestamp: string
  risk_level: string
  risk_score: number
}

export interface RiskResponse {
  region_id: string
  current: {
    risk_level: string
    risk_score: number
    timestamp: string
    model_version: string
  }
  history: RiskPoint[]
}

export interface AqiForecastPoint {
  timestamp: string
  predicted_aqi: number
  lower_bound: number
  upper_bound: number
}

export interface AqiResponse {
  region_id: string
  current_aqi: number
  category: string
  dominant_pollutant: string
  timestamp: string
  forecast: AqiForecastPoint[]
  forecast_note: string | null
}

export interface Alert {
  region_id: string
  alert_type: string
  severity: string
  message: string
  triggered_at: string
}

export interface TrendPoint {
  date: string
  risk_score?: number
  aqi?: number
}

export interface TrendsResponse {
  region_id: string
  data: TrendPoint[]
  note: string
}

export interface Preparedness {
  region_id: string
  current_risk_level: string
  tips: string[]
  evacuation_resources: { title: string; url: string }[]
}
