# API Specification (v1)

Base URL: `/api/v1`
Format: JSON (`application/json`)
OpenAPI Docs: Enabled only in `ENV=development` at `/docs`.

## Global Conventions
- All risk and air quality endpoints return `as_of` (UTC & IST) and `disclaimer_short`.
- RFC 9457 Problem Details error schema for 4xx/5xx responses:
  `{"type": "string", "title": "string", "status": int, "detail": "string", "instance": "string"}`
- Rate Limit: 60 requests/minute per client IP (429 Too Many Requests on breach).

## Endpoints

### 1. System Health
- `GET /health`: Minimal probe returning `{"status":"ok","version":"2.0.0"}` without infrastructure details.

### 2. Geographic Regions
- `GET /regions?country=IN&state=`: List districts with administrative metadata and centroids.
- `GET /regions/{id}`: District profile including land cover fractions and boundary geometry.
- `GET /regions/by-coordinates?lat=&lon=`: Resolve GPS coordinates to parent district.
- `GET /geo/cities?q=`: Query Indian cities, towns, and settlements directly via OpenStreetMap Nominatim.

### 3. Wildfire Risk
- `GET /risk/map?date=&state=`: GeoJSON FeatureCollection with simplified geometries and daily risk categories; districts without data have `has_prediction: false`.
- `GET /risk/latest?state=&limit=`: Paginated recent risk assessments across regions.
- `GET /risk/{region_id}?date=`: Single district risk score, probability, risk class, FWI value, and top 3 SHAP drivers.
- `GET /risk/{region_id}/history?days=30`: Temporal risk trend and historical fire occurrences.

### 4. Active Satellite Fires
- `GET /fires/recent?hours=24&bbox=`: NASA FIRMS thermal detections with confidence, FRP, and satellite source.
- `GET /fires/stats?days=7`: Fire count, radiative power, high-confidence count, breakdown by source and state, and detections outside any district.

### 5. Air Quality
- `GET /air-quality/latest?state=`: Current CPCB NAQI values and prominent pollutants per region.
- `GET /air-quality/{region_id}`: Comprehensive criteria pollutant concentrations (PM2.5, PM10, NO2, SO2, CO, O3) and sub-indices.
- `GET /air-quality/{region_id}/forecast`: 1 to 3 day AQI predictions with confidence bounds.

### 6. Atmospheric Weather
- `GET /weather/{region_id}?days=7`: Live weather and daily ERA5/forecast metrics (temp, humidity, wind, precipitation).

### 7. Models & Science
- `GET /models/current`: Models actually served (read from deployed artifacts); metrics only when a real evaluation exists.
- `GET /models/comparison`: `not_available` until a real evaluation file is deployed; never hand-written numbers.

### 8. Preparedness & Meta
- `GET /preparedness?hazard=&stage=&audience=`: Community safety protocols and civil defense speed-dials.
- `GET /meta/sources`: Formal data source attributions, licensing, and update cadences.
- `GET /meta/disclaimer`: Full legal academic disclaimer.

### 9. Internal Operational Endpoints (Restricted)
- `POST /internal/jobs/{job_name}`: Trigger background ingestion/forecasting job. Requires header `X-Job-Token: <JOB_TOKEN>`.
