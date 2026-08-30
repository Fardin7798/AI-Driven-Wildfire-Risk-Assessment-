# API Documentation — Wildfire Risk & AQI Monitoring Platform (BC)

**Base URL (local dev):** `http://localhost:8000`
**Format:** JSON
**Auth:** None required for MVP (all endpoints public/read-only)

---

## 1. Regions

### `GET /regions`
Returns a list of all monitored regions with their current status summary.

**Response 200:**
```json
[
  {
    "region_id": "bc-kelowna",
    "name": "Kelowna",
    "centroid": { "lat": 49.8880, "lon": -119.4960 },
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
| region_id | string | Unique region identifier (e.g., `bc-kelowna`) |

**Response 200:**
```json
{
  "region_id": "bc-kelowna",
  "name": "Kelowna",
  "geometry": "GeoJSON Polygon",
  "current_risk_level": "High",
  "current_aqi": 112,
  "last_updated": "2026-08-30T14:00:00Z"
}
```

**Response 404:** Region not found.

---

## 2. Wildfire Risk

### `GET /risk/{region_id}`
Returns current and recent risk score history for a region.

**Query params:**
| Param | Type | Default | Description |
|---|---|---|---|
| days | int | 7 | Number of past days of history to return |

**Response 200:**
```json
{
  "region_id": "bc-kelowna",
  "current": {
    "risk_level": "High",
    "risk_score": 0.78,
    "timestamp": "2026-08-30T14:00:00Z",
    "model_version": "v1.2"
  },
  "history": [
    { "timestamp": "2026-08-29T14:00:00Z", "risk_level": "Moderate", "risk_score": 0.55 },
    { "timestamp": "2026-08-28T14:00:00Z", "risk_level": "Moderate", "risk_score": 0.51 }
  ]
}
```

**Risk levels:** `Low` | `Moderate` | `High` | `Extreme`

---

## 3. Air Quality

### `GET /aqi/{region_id}`
Returns current AQI and short-term forecast for a region.

**Response 200:**
```json
{
  "region_id": "bc-kelowna",
  "current_aqi": 112,
  "category": "Unhealthy for Sensitive Groups",
  "timestamp": "2026-08-30T14:00:00Z",
  "forecast": [
    { "timestamp": "2026-08-30T18:00:00Z", "predicted_aqi": 120, "lower_bound": 100, "upper_bound": 140 },
    { "timestamp": "2026-08-31T00:00:00Z", "predicted_aqi": 95, "lower_bound": 80, "upper_bound": 110 }
  ]
}
```

**AQI categories:** `Good` | `Moderate` | `Unhealthy for Sensitive Groups` | `Unhealthy` | `Very Unhealthy` | `Hazardous`

---

## 4. Alerts

### `GET /alerts`
Returns all currently active alerts across regions (High/Extreme fire risk or Unhealthy+ AQI).

**Response 200:**
```json
[
  {
    "region_id": "bc-kelowna",
    "alert_type": "wildfire_risk",
    "severity": "High",
    "message": "High wildfire risk due to low humidity and high wind speed.",
    "triggered_at": "2026-08-30T14:00:00Z"
  },
  {
    "region_id": "bc-kamloops",
    "alert_type": "air_quality",
    "severity": "Unhealthy",
    "message": "AQI has reached Unhealthy levels due to nearby smoke.",
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
  "region_id": "bc-kelowna",
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
  "region_id": "bc-kelowna",
  "current_risk_level": "High",
  "tips": [
    "Keep an emergency go-bag ready.",
    "Monitor local news and official BC Wildfire Service updates.",
    "Avoid outdoor burning and report smoke sightings."
  ],
  "evacuation_resources": [
    { "title": "BC Wildfire Service — Current Situation", "url": "https://wildfiresituation.nrs.gov.bc.ca/" },
    { "title": "Emergency Management BC", "url": "https://www.emergencyinfobc.gov.bc.ca/" }
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
- All timestamps are in UTC (ISO 8601 format).
- Data freshness depends on ingestion schedule (weather: ~15–60 min, fire: few hours, AQI: hourly).
- No authentication required for MVP; add API keys/rate-limiting before any public deployment.
