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
- `GET /air-quality/latest?state=`: Latest stored observation per row (CPCB NAQI `aqi`, `aqi_category`, pollutant concentrations); averaging below.
- `GET /air-quality/{region_id}`: Latest observation for one district (PM2.5, PM10, NO2, SO2 µg/m³, CO mg/m³, O3 µg/m³, `aqi`, `aqi_category`); fetched from Open-Meteo on demand when none is stored. 404 when none can be had.
  - Current AQI averaging (CAMS rows, `provider: copernicus_cams_cpcb_avg`), per CPCB "How is AQI calculated?" (https://airquality.cpcb.gov.in/ccr_docs/How_AQI_Calculated.pdf): trailing 24 h of hourly CAMS values ending at the latest whole UTC hour (`observed_at_utc` = window end). PM2.5, PM10, NO2, SO2 = 24-h mean, only with >= 16 valid hours. CO, O3 = only with >= 16 valid hours in the 24-h window (CPCB minimum for any sub-index), then maximum 8-h running mean inside the window, each 8-h window valid with >= 6 hours (common convention, not a CPCB rule). A pollutant without enough hours is `null` (never filled). `aqi` = max sub-index, `null` unless >= 3 pollutants incl. PM2.5 or PM10 (CPCB).
  - `averaging`: `{window_start_utc, window_end_utc, window_hours, methods{pollutant: rule}, aqi_rule, reference}` on averaged CAMS rows; `null` on other rows (CPCB station rows, and older `copernicus_cams` rows which were instantaneous values).
- `GET /air-quality/forecast`: Latest AQI model-B forecast for every district (each district's latest origin day for the active model version), plus `counts` {forecast, skipped}.
- `GET /air-quality/{region_id}/forecast`: One district: `origin_date`, `model_version`, `source`, `extrapolated` and `forecasts` [{horizon, target_date, pm25_si_pred, category}] (PM2.5 sub-index, days +1..+3), or `status: skipped` with `skip_reason` and no values. 404 when nothing is recorded.

### 6. Atmospheric Weather
- `GET /weather/{region_id}?days=7`: Daily ECMWF IFS (Open-Meteo) weather metrics (temp, humidity, wind, precipitation).

### 7. Models & Science
- `GET /models/current`: Models actually served (read from deployed artifacts); metrics only when a real evaluation exists. The AQI entry (`aqi_station_xgb_v3`) carries test MAE h1..h3, raw-CAMS MAE on the same rows and the test disclosure, read from the model's evaluation and metadata files.
- `GET /models/comparison`: Served wildfire model vs FWI, climatology and persistence on test year 2025, read from `models/<model>/<model>_evaluation.json`; `not_available` if that file is missing.

### 8. Preparedness & Meta
- `GET /preparedness?hazard=&stage=&audience=`: Community safety protocols and civil defense speed-dials.
- `GET /meta/sources`: Formal data source attributions, licensing, and update cadences.
- `GET /meta/disclaimer`: Full legal academic disclaimer.

### 9. Internal Operational Endpoints (Restricted)
- `POST /internal/jobs/{job_name}`: Trigger background ingestion/forecasting job. Requires header `X-Job-Token: <JOB_TOKEN>`.
