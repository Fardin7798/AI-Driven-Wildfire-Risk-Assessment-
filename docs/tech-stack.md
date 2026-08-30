# Tech Stack — Wildfire Risk & AQI Monitoring Platform (BC)

## Overview
This document lists the complete technology stack for the project, organized by layer, along with the reasoning behind each choice. All tools are free/open-source; no paid services or physical hardware are required for development or demo.

---

## 1. Data Sources (External APIs)

| Source | Data Provided | Cost | Notes |
|---|---|---|---|
| **NASA FIRMS** | Active fire detections (VIIRS/MODIS) | Free (API key required) | Near real-time thermal anomaly data |
| **Open-Meteo** | Weather (temp, humidity, wind, rainfall) | Free, no key needed | Primary weather data source |
| **NOAA HRRR / GFS** | High-resolution weather forecasts | Free | Optional, for more precise modeling |
| **BC Wildfire Service** | Historical fire records, current situation reports | Free, public data | Region-specific ground truth |
| **PurpleAir** | Real-time AQI/PM2.5 readings | Free tier (API key required) | Community sensor network |
| **Copernicus / Sentinel-2** | NDVI vegetation dryness index | Free | Optional — improves fire risk accuracy |

---

## 2. Backend

| Component | Technology | Why |
|---|---|---|
| **API Framework** | Python + FastAPI | Async, fast, auto-generated docs (Swagger/OpenAPI), great for ML model serving |
| **Task Scheduling** | APScheduler | Lightweight, in-process scheduler for periodic data ingestion — no separate infra needed |
| **Database** | PostgreSQL + PostGIS | PostGIS adds geospatial query support (region lookups, spatial joins) on top of reliable relational storage |
| **ORM (optional)** | SQLAlchemy | Standard, well-supported Python ORM if raw SQL becomes unwieldy |

---

## 3. Machine Learning

| Component | Technology | Why |
|---|---|---|
| **Fire Risk Classification** | XGBoost | Strong performance on tabular weather/historical data, handles missing values well, fast to train |
| **AQI Time-Series Forecast** | Prophet | Purpose-built for time-series forecasting, handles seasonality, easy to interpret |
| **Explainability (stretch goal)** | SHAP | Shows which features (humidity, wind, etc.) drove a specific prediction — useful for thesis/demo credibility |
| **Model training environment** | scikit-learn, pandas, NumPy | Standard Python ML stack for preprocessing and evaluation |

---

## 4. Frontend

| Component | Technology | Why |
|---|---|---|
| **Framework** | React + TypeScript | Type safety, large ecosystem, widely used and well-documented |
| **Build tool** | Vite | Fast dev server and build times compared to older tooling (e.g., CRA) |
| **Mapping** | MapLibre GL JS | Open-source (no API key/billing like Google Maps), WebGL-based, good performance for interactive fire/AQI maps |
| **Charts** | Recharts | Simple, React-native charting library for trend graphs |
| **Styling** | Tailwind CSS (optional) | Fast utility-first styling if a custom design system isn't needed |

---

## 5. Infrastructure & Deployment

| Component | Technology | Why |
|---|---|---|
| **Containerization** | Docker + Docker Compose | Runs Postgres, backend, and frontend together with one command — no manual environment setup |
| **Version Control** | Git + GitHub | Standard, already set up for this project |
| **Hosting (optional, for live demo)** | Render / Railway (free tier) | No-cost hosting sufficient for a student project demo |

---

## 6. Development Tooling (Claude Code workflow)

| Tool | Purpose |
|---|---|
| **Claude Code** | AI pair-programmer for building the project |
| **Graphify** | Maps the codebase + docs into a knowledge graph so Claude Code can query instead of re-reading files every session |
| **Claude Task Master** | Converts the PRD into a dependency-ordered task list (`tasks.json`) that Claude Code executes step by step |
| **CLAUDE.md** | Persistent project instructions (stack, conventions, commands) loaded automatically every session |

---

## 7. Why This Stack Overall

- **No hardware required** — every data source is a public API; nothing needs to be self-hosted or physically built.
- **No paid services required** — every tool listed has a free tier sufficient for a student/academic-scale project.
- **Consistent language** — Python across backend + ML keeps the codebase simpler to maintain and reason about.
- **Open-source mapping** — avoids Google Maps billing/API key friction entirely.
- **Realistic for the project timeline** (~2–3 months) — every tool here is mainstream, well-documented, and has a low learning curve compared to more specialized alternatives.
