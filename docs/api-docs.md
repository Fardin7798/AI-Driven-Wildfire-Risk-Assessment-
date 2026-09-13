# API Documentation — Wildfire Risk & AQI Monitoring Platform (India)

**Base URL (local dev):** `http://localhost:8000`
**Interactive Swagger UI:** `http://localhost:8000/docs`
**Format:** JSON
**Auth:** None required (Public Real-Time Environmental Engine)

---

## 1. System Health

### `GET /health`
Verifies backend operational status, district database coverage, and live UTC timestamp.

**Response 200:**
```json
{
  "status": "healthy",
  "service": "Wildfire Risk & Air Quality Engine (India)",
  "version": "1.0.0",
  "districts_loaded": 39,
  "timestamp": "2026-09-13T08:16:20.544944+00:00"
}
```

---

## 2. Indian Districts & Search Hubs

### `GET /api/v1/districts`
Returns list of pre-bundled Indian districts and major eco-zones for instant autocomplete.

**Query Parameters:**
| Param | Type | Required | Description |
|---|---|:---:|---|
| `search` | string | No | Filter by district or state name (e.g. `Jalgaon`, `Maharashtra`) |

**Response 200:**
```json
{
  "total": 39,
  "districts": [
    {
      "id": "mh-jalgaon",
      "name": "Jalgaon / Bhusawal",
      "state": "Maharashtra",
      "lat": 21.045,
      "lon": 75.7873,
      "zone": "Deccan Plateau"
    }
  ]
}
```

---

## 3. Unified Environmental Risk Search

### `GET /api/v1/search`
Primary production endpoint. Performs on-demand parallel fetch of live weather, calculates Canadian FWI wildfire danger, queries NASA FIRMS satellite active fire proximity, retrieves Copernicus CAMS 72-hour hourly AQI forecasts, and outputs dynamic community preparedness advisories.

**Query Parameters:**
| Param | Type | Required | Description |
|---|---|:---:|---|
| `query` | string | No | City or district name (e.g. `Bhusawal`, `Nainital`, `Delhi`, `Pune`) |
| `lat` | float | No | Latitude coordinate override |
| `lon` | float | No | Longitude coordinate override |

**Response 200:**
```json
{
  "location": {
    "name": "Jalgaon / Bhusawal",
    "state": "Maharashtra",
    "latitude": 21.045,
    "longitude": 75.7873,
    "eco_zone": "Deccan Plateau"
  },
  "weather": {
    "temperature": 28.5,
    "humidity": 81.0,
    "wind_speed": 11.5,
    "precipitation": 0.1,
    "weather_code": 95,
    "timestamp": "2026-09-13T13:45"
  },
  "wildfire_assessment": {
    "fwi_score": 7.3,
    "risk_level": "Moderate",
    "color": "#eab308",
    "badge": "bg-amber-500/10 text-amber-400 border-amber-500/20",
    "ffmc": 82.1,
    "isi": 4.2,
    "key_drivers": ["Stable meteorological conditions with adequate moisture content"],
    "nearby_satellite_fires_50km": 0,
    "closest_active_fire_km": null,
    "active_hotspots": []
  },
  "air_quality": {
    "cpcb_aqi": 13,
    "category": "Good",
    "color": "#22c55e",
    "badge": "bg-emerald-500/10 text-emerald-400 border-emerald-500/20",
    "pollutants": {
      "pm2_5": 7.9,
      "pm10": 8.0,
      "co": 132.0,
      "no2": 5.2,
      "so2": 10.3,
      "o3": 88.0
    },
    "forecast_72h": [
      {
        "time": "2026-09-13T00:00",
        "aqi": 24,
        "pm2_5": 14.7,
        "pm10": 16.2,
        "wildfire_smoke_pm10": 0.0
      }
    ]
  },
  "community_preparedness": {
    "status": "normal",
    "advisories": [],
    "recommended_actions": [
      "Environmental baseline is stable. Maintain standard fire safety consciousness."
    ],
    "emergency_contacts": [
      { "name": "National Emergency Number", "number": "112", "desc": "Unified emergency helpline" },
      { "name": "Fire Service Emergency", "number": "101", "desc": "Immediate local fire response" },
      { "name": "Disaster Management (NDMA)", "number": "1078", "desc": "National Disaster Management Helpline" }
    ]
  }
}
```

---

## 4. Active Satellite Fires (MapLibre Ready)

### `GET /api/v1/fires/active`
Returns NASA FIRMS VIIRS 375m active fire detections across India in standard GeoJSON format for direct consumption by MapLibre GL JS vector layers.

**Query Parameters:**
| Param | Type | Required | Description |
|---|---|:---:|---|
| `format` | string | No | `geojson` (default) or `list` |

**Response 200 (GeoJSON):**
```json
{
  "type": "FeatureCollection",
  "features": [
    {
      "type": "Feature",
      "geometry": {
        "type": "Point",
        "coordinates": [79.48, 29.42]
      },
      "properties": {
        "brightness": 335.2,
        "frp": 14.5,
        "confidence": "high",
        "acq_date": "Today",
        "acq_time": "11:30"
      }
    }
  ]
}
```
