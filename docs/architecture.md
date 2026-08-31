# Architecture — Wildfire Risk & AQI Monitoring Platform (India)

## 1. High-Level Architecture Diagram (text form)

```
┌───────────────────────────────────────────────────────────────────┐
│                        EXTERNAL DATA SOURCES                       │
│  FSI Fire Alerts │ IMD/Open-Meteo │ CPCB (data.gov.in) │ SAFAR    │
│      (fire)          (weather)         (AQI)          (forecast) │
└───────────────────────────────┬─────────────────────────────────────┘
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
- **Responsibility:** Periodically pull data from external Indian government APIs, clean/normalize it, and write to the database.
- **Tech:** Python, `requests`, `APScheduler`
- **Jobs:**
  - `fetch_weather()` — every 15–60 min (IMD dataset if available on data.gov.in, else Open-Meteo)
  - `fetch_fire_detections()` — every few hours (FSI Fire Alert System, cross-checked with NASA FIRMS)
  - `fetch_aqi()` — hourly (CPCB via data.gov.in API, SAFAR for Delhi-NCR forecast)
  - `fetch_historical_fire_data()` — daily/on-demand (FSI historical fire records, if accessible)
- **Failure handling:** Log failed fetches; retry with backoff; keep last-known-good value if a source is temporarily down.
- **Note:** FSI's public site (fsiforestfire.gov.in) may not expose a clean REST API — verify early whether a data.gov.in dataset exists, or whether a lightweight scraper is needed for fire point data.

### 2.2 Database Layer
- **Tech:** PostgreSQL + PostGIS (for geospatial queries — e.g., "which district does this fire detection fall in").
- **Core tables:**
  - `regions` (id, name — district/city, state, geometry/polygon, centroid)
  - `raw_weather` (region_id, timestamp, temp, humidity, wind_speed, rainfall)
  - `raw_fire_detections` (lat, lon, confidence, frp, timestamp, source, state, district)
  - `raw_aqi` (station_id, region_id, timestamp, pollutant_id, pollutant_avg, aqi_value)
  - `risk_scores` (region_id, timestamp, risk_level, model_version)
  - `aqi_forecast` (region_id, timestamp, predicted_aqi, confidence_interval)

### 2.3 ML Layer
- **Fire Risk Model**
  - Input features: temperature, humidity, wind speed, rainfall (7-day), historical fire frequency (FSI), NDVI (Bhuvan/Sentinel, optional)
  - Model: XGBoost classifier → outputs Low/Moderate/High/Extreme
  - Retraining: periodic (e.g., weekly) as new historical data accumulates, especially ahead of fire season (Feb–June in most Indian states)
- **AQI Forecast Model**
  - Input: historical AQI time series per city/station (CPCB), cross-referenced with SAFAR forecasts for validation
  - Model: Prophet (or similar time-series model) → 24–48h forecast
  - Note: Should account for seasonal spikes (Oct–Nov stubble burning in Punjab/Haryana affecting Delhi-NCR)
- **Explainability (optional/stretch):** SHAP values to show top contributing features per prediction

### 2.4 Backend API
- **Tech:** FastAPI
- **Key endpoints:**
  | Endpoint | Description |
  |---|---|
  | `GET /regions` | List all monitored districts/cities with current status |
  | `GET /risk/{region_id}` | Current + historical fire risk score for a region |
  | `GET /aqi/{region_id}` | Current + forecasted AQI for a region (India National AQI scale) |
  | `GET /alerts` | Active high-risk/poor-AQI alerts |
  | `GET /trends/{region_id}` | Historical time-series data for charts |
  | `GET /preparedness/{region_id}` | Safety tips + evacuation info links |

### 2.5 Frontend Dashboard
- **Tech:** React + TypeScript + Vite
- **Key views:**
  - **Map view** — MapLibre GL, showing fire hotspots, district risk colors, CPCB AQI stations
  - **Region detail panel** — current risk/AQI + trend charts (Recharts)
  - **Alerts banner** — shown when a district enters High/Extreme fire risk or Poor+/Severe AQI
  - **Preparedness page** — static/curated safety content + evacuation links

---

## 3. Data Flow Summary

1. Ingestion service pulls data from external Indian government APIs on a schedule.
2. Raw data is normalized and stored in PostgreSQL, tagged by district/region (via PostGIS spatial join).
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
- No physical hardware or sensors required — all data comes from external Indian government APIs.

---

## 5. Scalability & Future Considerations
- Move ingestion scheduler to a proper job queue (e.g., Celery + Redis) if scaling to many districts/states.
- Add caching layer (Redis) for frequently accessed endpoints (e.g., `/regions`, `/alerts`).
- Add authentication if the platform later supports personalized alerts (e.g., email/SMS per user location).
- Consider a managed cloud database if moving beyond local/demo deployment.
- Consider state-wise pilot rollout (e.g., start with Uttarakhand for fire risk + Delhi-NCR for AQI) before expanding pan-India, given CPCB station density varies significantly by region.
