# API Documentation — Wildfire Risk & AQI Monitoring Platform (India)

**Base URL (local dev):** `http://localhost:8000`
**Base URL (production):** `https://wildfire-aqi-backend.onrender.com` (deployed on Render, free tier — ⚠️ currently serving seed/mock data shaped exactly like the responses below; real data ingestion not yet wired in)
**Format:** JSON
**Auth:** None required for MVP (all endpoints public/read-only)

---

## 1. Regions

### `GET /regions`
Returns a list of all monitored regions (districts/cities) with their current status summary.

**Response 200:**
```json
[
  {
    "region_id": "uk-nainital",
    "name": "Nainital",
    "state": "Uttarakhand",
    "centroid": { "lat": 29.3803, "lon": 79.4636 },
    "current_risk_level": "High",
    "current_aqi": 112,
    "last_updated": "2026-08-30T14:00:00Z"
  }
]
```

---

### `GET /regions/{region_id}`
Returns detailed info for a single region.

**Path params:**
| Param | Type | Description |
|---|---|---|
| region_id | string | Unique region identifier (e.g., `uk-nainital`, `dl-delhi`) |

**Response 200:**
```json
{
  "region_id": "uk-nainital",
  "name": "Nainital",
  "state": "Uttarakhand",
  "geometry": "GeoJSON Polygon",
  "current_risk_level": "High",
  "current_aqi": 112,
  "last_updated": "2026-08-30T14:00:00Z"
}
```

**Response 404:** Region not found.

---

## 2. Forest Fire Risk

### `GET /risk/{region_id}`
Returns current and recent risk score history for a region.

⚠️ **`model_version: "rule-based-v1"` — not ML yet.** Real weather + real nearby-fire-detection inputs, run through a simplified fire-danger formula (humidity/wind/temp/fire-count weighted). Honest interim until enough historical data accumulates to train a real ML model (see roadmap in CONTEXT.md). `history` will be empty until the hourly ingestion job has run more than once for a region.

**Query params:**
| Param | Type | Default | Description |
|---|---|---|---|
| days | int | 7 | Number of past days of history to return |

**Response 200 (current production shape):**
```json
{
  "region_id": "uk-nainital",
  "current": {
    "risk_level": "Low",
    "risk_score": 0.03,
    "timestamp": "2026-08-31T20:44:12Z",
    "model_version": "rule-based-v1"
  },
  "history": []
}
```

**Risk levels:** `Low` | `Moderate` | `High` | `Extreme`

---

## 3. Air Quality

### `GET /aqi/{region_id}`
Returns current AQI for a region, using India's National AQI standard (CPCB). Forecast is not yet implemented — see note below.

**Response 200 (current production shape):**
```json
{
  "region_id": "dl-delhi",
  "current_aqi": 56,
  "category": "Satisfactory",
  "dominant_pollutant": "PM2.5",
  "timestamp": "2026-08-31T11:23:44Z",
  "forecast": [],
  "forecast_note": "Forecasting model not yet built — needs several weeks of accumulated historical data first. current_aqi above is real (live CPCB data)."
}
```

⚠️ **`forecast` is intentionally empty for now.** `current_aqi` is real, live CPCB data — but the forecast array will only be populated once a real forecasting model exists (needs historical data the ingestion pipeline hasn't accumulated yet, started Aug 31, 2026). Do not hardcode a fake forecast on the frontend to fill this gap — show "forecast coming soon" instead.

**AQI categories (India National AQI — CPCB):** `Good (0–50)` | `Satisfactory (51–100)` | `Moderate (101–200)` | `Poor (201–300)` | `Very Poor (301–400)` | `Severe (401–500)`

---

## 4. Alerts

### `GET /alerts`
Returns all currently active alerts across regions (High/Extreme fire risk or Poor+/Severe AQI).

**Response 200:**
```json
[
  {
    "region_id": "uk-nainital",
    "alert_type": "forest_fire_risk",
    "severity": "High",
    "message": "High forest fire risk due to low humidity and high wind speed.",
    "triggered_at": "2026-08-30T14:00:00Z"
  },
  {
    "region_id": "dl-delhi",
    "alert_type": "air_quality",
    "severity": "Very Poor",
    "message": "AQI has reached Very Poor levels, likely linked to stubble burning.",
    "triggered_at": "2026-08-30T13:00:00Z"
  }
]
```

---

## 5. Trends

### `GET /trends/{region_id}`
Returns historical time-series data for charting (risk score + AQI combined).

**Query params:**
| Param | Type | Default | Description |
|---|---|---|---|
| days | int | 30 | Number of past days to return |
| metric | string | "both" | `risk` \| `aqi` \| `both` |

**Response 200:**
```json
{
  "region_id": "uk-nainital",
  "data": [
    { "date": "2026-08-01", "risk_score": 0.35, "aqi": 45 },
    { "date": "2026-08-02", "risk_score": 0.40, "aqi": 52 }
  ]
}
```

---

## 6. Preparedness

### `GET /preparedness/{region_id}`
Returns safety tips and evacuation resource links relevant to the region's current risk level.

**Response 200:**
```json
{
  "region_id": "uk-nainital",
  "current_risk_level": "High",
  "tips": [
    "Keep an emergency go-bag ready.",
    "Monitor official Forest Survey of India (FSI) and State Forest Department updates.",
    "Avoid outdoor burning and report smoke/fire sightings to the nearest forest office."
  ],
  "evacuation_resources": [
    { "title": "Forest Survey of India — Fire Alerts", "url": "https://fsiforestfire.gov.in/" },
    { "title": "National Disaster Management Authority (NDMA)", "url": "https://ndma.gov.in/" }
  ]
}
```

---

## 7. Error Format (all endpoints)

```json
{
  "error": "Region not found",
  "status_code": 404
}
```

| Status Code | Meaning |
|---|---|
| 200 | Success |
| 404 | Resource not found |
| 422 | Invalid query/path parameters |
| 500 | Internal server error (e.g., data source temporarily unavailable) |

---

## 8. Notes
- All timestamps are in UTC (ISO 8601 format) internally; display in IST (UTC+5:30) on the frontend.
- Data freshness depends on ingestion schedule (weather: ~15–60 min, fire: every few hours per FSI satellite pass, AQI: hourly).
- CPCB AQI data requires a free data.gov.in API key — stored server-side, never exposed to the frontend.
- No authentication required for MVP; add API keys/rate-limiting before any public deployment.
