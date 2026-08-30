# Architecture — Wildfire Risk & AQI Monitoring Platform (BC)

## 1. High-Level Architecture Diagram (text form)

```
┌─────────────────────────────────────────────────────────────────┐
│                        EXTERNAL DATA SOURCES                     │
│  NASA FIRMS │ Open-Meteo/NOAA │ BC Wildfire Service │ PurpleAir  │
│              (fire)      (weather)      (historical)   (AQI)     │
└───────────────────────────────┬───────────────────────────────────┘
                                 │  (scheduled API calls)
                                 ▼
                  ┌───────────────────────────────┐
                  │   INGESTION SERVICE (Python)   │
                  │   APScheduler jobs, per-source │
                  │   fetch → validate → normalize │
                  └───────────────┬─────────────────┘
                                 │
                                 ▼
                  ┌───────────────────────────────┐
                  │   DATABASE (PostgreSQL+PostGIS) │
                  │   raw_weather, raw_fire,        │
                  │   raw_aqi, regions (geo)         │
                  └───────────────┬─────────────────┘
                                 │
                 ┌───────────────┼────────────────┐
                 ▼                                ▼
      ┌───────────────────┐            ┌───────────────────────┐
      │  ML LAYER          │            │  ML LAYER              │
      │  Fire Risk Model   │            │  AQI Forecast Model    │
      │  (XGBoost)         │            │  (Prophet)              │
      └─────────┬──────────┘            └───────────┬─────────────┘
                 │                                    │
                 ▼                                    ▼
                 └───────────────┬────────────────────┘
                                 ▼
                  ┌───────────────────────────────┐
                  │   BACKEND API (FastAPI)         │
                  │   /risk, /aqi, /alerts,         │
                  │   /regions, /trends              │
                  └───────────────┬─────────────────┘
                                 │  (REST/JSON)
                                 ▼
                  ┌───────────────────────────────┐
                  │   FRONTEND (React + TS)         │
                  │   MapLibre GL map, Recharts,    │
                  │   Alert banners, Prep content   │
                  └───────────────────────────────┘
                                 │
                                 ▼
                            End User (Browser)
```

---

## 2. Component Breakdown

### 2.1 Ingestion Service
- **Responsibility:** Periodically pull data from external APIs, clean/normalize it, and write to the database.
- **Tech:** Python, `requests`, `APScheduler`
- **Jobs:**
  - `fetch_weather()` — every 15–60 min (Open-Meteo/NOAA)
  - `fetch_fire_detections()` — every few hours (NASA FIRMS)
  - `fetch_aqi()` — hourly (PurpleAir/govt feeds)
  - `fetch_historical_fire_data()` — daily/on-demand (BC Wildfire Service)
- **Failure handling:** Log failed fetches; retry with backoff; keep last-known-good value if a source is temporarily down.

### 2.2 Database Layer
- **Tech:** PostgreSQL + PostGIS (for geospatial queries — e.g., "which region does this fire detection fall in").
- **Core tables:**
  - `regions` (id, name, geometry/polygon, centroid)
  - `raw_weather` (region_id, timestamp, temp, humidity, wind_speed, rainfall)
  - `raw_fire_detections` (lat, lon, confidence, frp, timestamp, source)
  - `raw_aqi` (station_id, region_id, timestamp, pm2_5, aqi_value)
  - `risk_scores` (region_id, timestamp, risk_level, model_version)
  - `aqi_forecast` (region_id, timestamp, predicted_aqi, confidence_interval)

### 2.3 ML Layer
- **Fire Risk Model**
  - Input features: temperature, humidity, wind speed, rainfall (7-day), historical fire frequency, NDVI (optional)
  - Model: XGBoost classifier → outputs Low/Moderate/High/Extreme
  - Retraining: periodic (e.g., weekly) as new historical data accumulates
- **AQI Forecast Model**
  - Input: historical AQI time series per region/station
  - Model: Prophet (or similar time-series model) → 24–48h forecast
- **Explainability (optional/stretch):** SHAP values to show top contributing features per prediction

### 2.4 Backend API
- **Tech:** FastAPI
- **Key endpoints:**
  | Endpoint | Description |
  |---|---|
  | `GET /regions` | List all monitored regions with current status |
  | `GET /risk/{region_id}` | Current + historical risk score for a region |
  | `GET /aqi/{region_id}` | Current + forecasted AQI for a region |
  | `GET /alerts` | Active high-risk/unhealthy-AQI alerts |
  | `GET /trends/{region_id}` | Historical time-series data for charts |
  | `GET /preparedness/{region_id}` | Safety tips + evacuation info links |

### 2.5 Frontend Dashboard
- **Tech:** React + TypeScript + Vite
- **Key views:**
  - **Map view** — MapLibre GL, showing fire detections, region risk colors, AQI stations
  - **Region detail panel** — current risk/AQI + trend charts (Recharts)
  - **Alerts banner** — shown when a region enters High/Extreme risk or Unhealthy AQI
  - **Preparedness page** — static/curated safety content + evacuation links

---

## 3. Data Flow Summary

1. Ingestion service pulls data from external APIs on a schedule.
2. Raw data is normalized and stored in PostgreSQL, tagged by region (via PostGIS spatial join).
3. ML models run on the latest data to produce risk scores and AQI forecasts, stored in dedicated tables.
4. FastAPI backend serves this processed data via REST endpoints.
5. React frontend fetches from the API and renders the map, charts, and alerts.
6. Alerts are triggered in the frontend (or backend, if push notifications are added later) when thresholds are crossed.

---

## 4. Deployment Architecture (MVP)

```
Docker Compose
 ├── postgres (PostGIS-enabled)
 ├── backend (FastAPI + ingestion scheduler)
 └── frontend (React, served via Vite/nginx)
```

- Single-machine deployment is sufficient for MVP/demo — no distributed infrastructure needed.
- No physical hardware or sensors required — all data comes from external APIs.

---

## 5. Scalability & Future Considerations
- Move ingestion scheduler to a proper job queue (e.g., Celery + Redis) if scaling to many regions.
- Add caching layer (Redis) for frequently accessed endpoints (e.g., `/regions`, `/alerts`).
- Add authentication if the platform later supports personalized alerts (e.g., email/SMS per user location).
- Consider a managed cloud database if moving beyond local/demo deployment.
