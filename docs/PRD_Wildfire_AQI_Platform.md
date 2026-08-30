# Product Requirements Document (PRD)

## AI-Driven Wildfire Risk Assessment, Air Quality Monitoring, and Community Preparedness Platform (BC)

**Version:** 1.0
**Date:** August 30, 2026
**Status:** Draft

---

## 1. Overview

### 1.1 Purpose
A web-based dashboard platform for British Columbia (BC) that predicts wildfire risk, monitors real-time air quality, and provides communities with preparedness information (evacuation routes, safety tips, alerts) — using publicly available data and free APIs, with no physical hardware required.

### 1.2 Problem Statement
BC faces recurring wildfire seasons that threaten lives, property, and air quality across large regions. Existing information is fragmented across multiple government sites (weather, fire, AQI), making it hard for residents and local authorities to get a single, predictive, actionable view of risk in their area.

### 1.3 Goals
- Predict wildfire risk at a regional/station level using weather and historical fire data.
- Provide real-time air quality (AQI) monitoring and forecasting.
- Give communities actionable preparedness guidance during high-risk periods.
- Build entirely on free/open data sources and open-source tools (no proprietary hardware).

### 1.4 Non-Goals
- Not a replacement for official emergency alert systems (BC Wildfire Service, Emergency Management BC).
- Not a real-time firefighting/operations tool for first responders.
- Not intended to provide legally binding evacuation orders.

---

## 2. Target Users

| User Type | Needs |
|---|---|
| General public (BC residents) | Simple risk level for their area, AQI today/forecast, safety tips |
| Local community organizers | Preparedness checklists, evacuation route info |
| Researchers/students | Access to model outputs, historical trend data |
| (Stretch) Local authorities | Aggregated risk view across multiple regions |

---

## 3. Key Features

### 3.1 Wildfire Risk Prediction
- ML model predicts fire risk score (Low/Moderate/High/Extreme) per region using:
  - Weather (temperature, humidity, wind, rainfall) — Open-Meteo / NOAA
  - Dryness/fuel moisture proxy — derived from weather + NDVI (Copernicus/Sentinel, optional)
  - Historical fire data — NASA FIRMS, BC Wildfire Service open data
- Output refreshed at least daily; ideally every few hours.

### 3.2 Real-Time Air Quality Monitoring
- Pull current AQI from public stations/APIs (e.g., PurpleAir, government AQI feeds).
- Short-term AQI forecast (next 24–48h) using a time-series model (e.g., Prophet).
- Color-coded AQI scale (Good/Moderate/Unhealthy/Hazardous) matching Canadian AQHI conventions.

### 3.3 Interactive Map Dashboard
- GIS map showing active fire detections, risk zones, and AQI stations.
- Click a region to see current risk, AQI, and 7-day trend.

### 3.4 Community Preparedness Module
- Static/curated safety tips (what to do at each risk level).
- Evacuation route information (linked to official BC resources; platform aggregates/displays, doesn't generate new routes).
- Alert banner when a region crosses into High/Extreme risk or Unhealthy AQI.

### 3.5 Historical Trends & Analytics
- Charts showing risk score and AQI trends over time per region.
- Simple explainability (e.g., "risk is high mainly due to low humidity + high wind").

---

## 4. User Stories

1. As a resident, I want to see today's wildfire risk and AQI for my town, so I can decide if outdoor activity is safe.
2. As a resident, I want to receive a visible alert when risk becomes High/Extreme in my area.
3. As a community organizer, I want to access preparedness tips and evacuation info in one place.
4. As a researcher, I want to view historical risk/AQI trends to study patterns.

---

## 5. Technical Requirements

### 5.1 Data Sources (all free/public)
| Source | Data | Update Frequency |
|---|---|---|
| NASA FIRMS | Active fire detections (VIIRS/MODIS) | Near real-time |
| Open-Meteo / NOAA HRRR | Weather (temp, humidity, wind, rain) | 15 min–hourly |
| BC Wildfire Service | Historical fire records, current situation | Daily |
| PurpleAir / Govt AQI feeds | Air quality index | Hourly |
| Copernicus/Sentinel (optional) | NDVI vegetation dryness | Weekly |

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
- None required. Entire system runs on standard laptop/cloud VM using public APIs.

---

## 6. Success Metrics

- Model accuracy: fire risk classification F1-score benchmarked against historical fire occurrence data.
- AQI forecast error (MAE) within acceptable range for 24h forecast.
- Dashboard load time < 3 seconds for map + current risk view.
- (If user testing possible) Usability feedback from a small group of test users.

---

## 7. Scope & Milestones (suggested)

| Phase | Deliverable | Est. Duration |
|---|---|---|
| 1 | Data ingestion pipeline (weather, fire, AQI APIs) | 2–3 weeks |
| 2 | Fire risk ML model (training + validation) | 3 weeks |
| 3 | AQI forecasting model | 2 weeks |
| 4 | Backend API (FastAPI) | 2 weeks |
| 5 | Frontend dashboard + map | 3 weeks |
| 6 | Preparedness content + alerts | 1 week |
| 7 | Testing, polish, documentation | 2 weeks |

---

## 8. Risks & Limitations

- Public API rate limits or downtime could affect data freshness.
- Fire risk prediction accuracy depends on quality/resolution of historical data available for BC.
- Model outputs are a decision-support estimate, not an official emergency warning — must be clearly disclaimed in the UI.
- NDVI/satellite data may have gaps due to cloud cover.

---

## 9. Open Questions

- Which specific BC regions/stations will be covered in the MVP (province-wide vs. pilot regions)?
- Will evacuation route data be sourced live from an official API, or manually curated/linked?
- Is real-user testing in scope, or is this an academic/demo-only deliverable?
