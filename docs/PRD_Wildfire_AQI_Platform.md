# Product Requirements Document (PRD)

## AI-Driven Wildfire Risk Assessment, Air Quality Monitoring, and Community Preparedness Platform (India)

**Version:** 2.0 (Updated for India)
**Date:** August 31, 2026
**Status:** Draft

---

## 1. Overview

### 1.1 Purpose
A web-based dashboard platform for India that predicts forest fire risk, monitors real-time air quality, and provides communities with preparedness information (evacuation routes, safety tips, alerts) — using publicly available Indian government data and free APIs, with no physical hardware required.

### 1.2 Problem Statement
India faces recurring forest fire seasons (especially in Uttarakhand, Himachal Pradesh, Odisha, Madhya Pradesh, and the Northeast) and severe air quality crises (especially in the Indo-Gangetic Plain — Delhi-NCR, Punjab, Haryana, UP). Existing information is fragmented across multiple government portals (FSI for fires, CPCB for AQI, IMD for weather), making it hard for residents and local authorities to get a single, predictive, actionable view of risk in their area.

### 1.3 Goals
- Predict forest fire risk at a district/region level using weather and historical fire data.
- Provide real-time air quality (AQI) monitoring and forecasting using the Indian National AQI standard.
- Give communities actionable preparedness guidance during high-risk periods (fire season and stubble-burning/smog season).
- Build entirely on free/open Indian government data sources and open-source tools (no proprietary hardware).

### 1.4 Non-Goals
- Not a replacement for official emergency alert systems (Forest Survey of India, National Disaster Management Authority/NDMA, State Pollution Control Boards).
- Not a real-time firefighting/operations tool for forest department field staff.
- Not intended to provide legally binding evacuation orders.

---

## 2. Target Users

| User Type | Needs |
|---|---|
| General public (Indian residents) | Simple risk level for their district/city, AQI today/forecast, safety tips |
| Local community organizers / NGOs | Preparedness checklists, evacuation route info |
| Researchers/students | Access to model outputs, historical trend data |
| (Stretch) Forest/pollution control officials | Aggregated risk view across multiple districts/states |

---

## 3. Key Features

### 3.1 Forest Fire Risk Prediction
- ML model predicts fire risk score (Low/Moderate/High/Extreme) per district using:
  - Weather (temperature, humidity, wind, rainfall) — IMD / Open-Meteo
  - Dryness/fuel moisture proxy — derived from weather + NDVI (Bhuvan/ISRO or Copernicus/Sentinel, optional)
  - Historical + near-real-time fire data — Forest Survey of India (FSI) Fire Alert System (MODIS/VIIRS-based), NASA FIRMS
- Output refreshed at least daily; ideally every few hours (FSI data updates ~6 times/day from satellite passes).

### 3.2 Real-Time Air Quality Monitoring
- Pull current AQI from CPCB's National Air Quality Index network via data.gov.in API, and SAFAR (IITM Pune) for Delhi-NCR forecasts.
- Short-term AQI forecast (next 24–48h) using a time-series model (e.g., Prophet).
- Color-coded AQI scale (Good/Satisfactory/Moderate/Poor/Very Poor/Severe) matching India's National AQI (CPCB) standard — different bands from the US/Canada scale.

### 3.3 Interactive Map Dashboard
- GIS map showing active fire hotspots (FSI/FIRMS), district risk zones, and CPCB AQI monitoring stations.
- Click a district/city to see current risk, AQI, and 7-day trend.

### 3.4 Community Preparedness Module
- Static/curated safety tips (what to do at each risk level — fire evacuation, smog/AQI health precautions).
- Evacuation route information (linked to official State Forest Department / NDMA resources; platform aggregates/displays, doesn't generate new routes).
- Alert banner when a district crosses into High/Extreme fire risk or Poor+/Severe AQI.

### 3.5 Historical Trends & Analytics
- Charts showing risk score and AQI trends over time per district/city.
- Simple explainability (e.g., "risk is high mainly due to low humidity + high wind" or "AQI spike linked to stubble burning season").

---

## 4. User Stories

1. As a resident, I want to see today's forest fire risk and AQI for my city/district, so I can decide if outdoor activity is safe.
2. As a resident, I want to receive a visible alert when risk becomes High/Extreme or AQI becomes Poor/Severe in my area.
3. As a community organizer, I want to access preparedness tips and evacuation info in one place.
4. As a researcher, I want to view historical risk/AQI trends to study patterns (e.g., stubble-burning season spikes, summer fire season in Uttarakhand).

---

## 5. Technical Requirements

### 5.1 Data Sources (all free/public — India-specific)
| Source | Data | Update Frequency |
|---|---|---|
| Forest Survey of India (FSI) Fire Alert System | Near real-time forest fire hotspots (MODIS/VIIRS) | ~6x/day (satellite passes) |
| NASA FIRMS | Active fire detections (supplementary/cross-check) | Near real-time |
| IMD / Open-Meteo | Weather (temp, humidity, wind, rain) | 15 min–hourly |
| CPCB (via data.gov.in API) | Real-time National AQI from monitoring stations | Hourly |
| SAFAR (IITM Pune) | AQI forecast for Delhi-NCR and select metro cities | Daily |
| Bhuvan (ISRO) / Copernicus-Sentinel (optional) | NDVI vegetation dryness index | Weekly |

### 5.2 Architecture
```
Data Sources (APIs) → Ingestion Service (Python, APScheduler)
   → PostgreSQL + PostGIS (storage)
   → ML Layer (XGBoost for risk, Prophet for AQI forecast)
   → FastAPI (backend REST API)
   → React + TypeScript frontend (MapLibre GL / Leaflet + Recharts)
```

### 5.3 Tech Stack
- **Backend:** Python, FastAPI, APScheduler
- **Database:** PostgreSQL + PostGIS
- **ML:** XGBoost / Random Forest (fire risk classification), Prophet (AQI time-series forecast), SHAP (explainability — stretch goal)
- **Frontend:** React, TypeScript, Vite, MapLibre GL / Leaflet, Recharts
- **Deployment:** Docker Compose (local/demo); no cloud dependency required for MVP

### 5.4 Hardware
- None required. Entire system runs on standard laptop/cloud VM using public Indian government APIs.

### 5.5 API Access Requirements
- **data.gov.in API key** — free, required for CPCB real-time AQI data (sign up at data.gov.in).
- **FSI Fire Alert data** — publicly viewable at fsiforestfire.gov.in; may require scraping/parsing if no direct API is available (verify during implementation — check for a data.gov.in dataset or NRSC/Bhuvan API alternative).
- **IMD data** — check data.gov.in for IMD weather datasets, or use Open-Meteo as a free global fallback with good India coverage.

---

## 6. Success Metrics

- Model accuracy: fire risk classification F1-score benchmarked against historical FSI fire occurrence data.
- AQI forecast error (MAE) within acceptable range for 24h forecast, benchmarked against CPCB actuals.
- Dashboard load time < 3 seconds for map + current risk view.
- (If user testing possible) Usability feedback from a small group of test users.

---

## 7. Scope & Milestones (suggested)

| Phase | Deliverable | Est. Duration |
|---|---|---|
| 1 | Data ingestion pipeline (IMD/weather, FSI fire, CPCB AQI APIs) | 2–3 weeks |
| 2 | Fire risk ML model (training + validation) | 3 weeks |
| 3 | AQI forecasting model | 2 weeks |
| 4 | Backend API (FastAPI) | 2 weeks |
| 5 | Frontend dashboard + map | 3 weeks |
| 6 | Preparedness content + alerts | 1 week |
| 7 | Testing, polish, documentation | 2 weeks |

---

## 8. Risks & Limitations

- Public API rate limits or downtime could affect data freshness (data.gov.in API keys have rate limits on free tier).
- Fire risk prediction accuracy depends on quality/resolution of historical data available for the chosen Indian states/districts.
- FSI fire alert data may need scraping/parsing since a clean public API isn't confirmed yet — needs verification early in implementation.
- Model outputs are a decision-support estimate, not an official emergency warning — must be clearly disclaimed in the UI.
- NDVI/satellite data may have gaps due to cloud cover (especially during monsoon season).
- CPCB monitoring stations are concentrated in cities — rural/forest-fire-prone district coverage may be sparse.

---

## 9. Open Questions (Resolved — Aug 31, 2026)

- ~~Which specific Indian states/districts will be covered in the MVP~~ → Still open, but Uttarakhand (fire) + Delhi-NCR (AQI) remains the recommended pilot per section 8.
- ~~Will FSI fire data be accessed via an official API/dataset, or scraped~~ → **Resolved: FSI has no public API** (verified — access restricted to State Forest Departments). **NASA FIRMS is the primary fire data source instead**, live-verified working with a personal MAP_KEY (118 real detections returned across India).
- Will evacuation route data be sourced from NDMA/state disaster management resources, or manually curated/linked? — still open.
- Is real-user testing in scope, or is this an academic/demo-only deliverable? — still open.

**API verification status (live-tested Aug 31, 2026):**
| Source | Status |
|---|---|
| Open-Meteo (weather) | ✅ Verified — no key needed |
| CPCB / data.gov.in (AQI) | ✅ Verified — personal API key tested, real nationwide data confirmed |
| NASA FIRMS (fire) | ✅ Verified — personal MAP_KEY tested, real fire detections confirmed |
| FSI Fire Alert | ❌ No public API — demoted to reference only |
| SAFAR (IITM Pune) | ❌ No public API — static site only, skipped |
| Bhuvan NDVI | ❌ No NDVI-specific endpoint — skip or use Copernicus Sentinel Hub instead (optional, not yet verified) |

**All 3 core MVP data sources (weather, AQI, fire) are confirmed working — implementation can begin.**
