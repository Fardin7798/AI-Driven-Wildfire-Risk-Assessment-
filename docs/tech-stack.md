# Tech Stack — Wildfire Risk & AQI Monitoring Platform (India)

## Overview
This document lists the complete technology stack for the project, organized by layer, along with the reasoning behind each choice. All tools are free/open-source; no paid services or physical hardware are required for development or demo.

---

## 1. Data Sources (External APIs — India-specific)

| Source | Data Provided | Cost | Notes |
|---|---|---|---|
| **NASA FIRMS** | Active fire detections (VIIRS/MODIS) | Free (API key required) | ✅ **Verified working (Aug 31, 2026)** — live-tested with a real MAP_KEY, returned 118 real fire detections across India (bbox 68,8,97,31, VIIRS_SNPP_NRT). **Primary fire data source** — see FSI note below for why FIRMS replaces FSI as primary. |
| **Forest Survey of India (FSI) Fire Alert System** | Near real-time forest fire hotspots (MODIS/VIIRS) | Free, public (site only) | ⚠️ **Verified: no public REST API.** fsiforestfire.gov.in is live and updates every 15 min, but API/WMS access is restricted to State Forest Departments. General public gets SMS alerts or the map UI only — not usable for automated ingestion. Demoted to reference/cross-check only; NASA FIRMS (same underlying MODIS/VIIRS data) is the primary fire source instead. |
| **IMD (via data.gov.in) / Open-Meteo** | Weather (temp, humidity, wind, rainfall) | Free | ✅ **Verified working** — Open-Meteo live-tested with real Nainital data (no key needed, no signup). Using as primary weather source; IMD dataset via data.gov.in not separately verified. |
| **CPCB (via data.gov.in API)** | Real-time National AQI from monitoring stations | Free (API key required — sign up at data.gov.in) | ✅ **Verified working (Aug 31, 2026)** — live-tested with a real personal API key, returned real-time data (3,416+ records nationwide, confirmed India + Uttarakhand + Delhi state filters working). Primary AQI data source. |
| **SAFAR (IITM Pune)** | AQI forecasts for Delhi-NCR and select metro cities | Free, public | ⚠️ **Verified: no public API** — safar.tropmet.res.in is a static-image website only (was unreachable during testing). Not usable for automated ingestion; CPCB + Open-Meteo cover the MVP without it. |
| **Bhuvan (ISRO) / Copernicus-Sentinel** | NDVI vegetation dryness index | Free | Optional — improves fire risk accuracy |

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
| **Database hosting** | Supabase (Postgres + PostGIS free tier) | Free-tier hosted Postgres with a one-click PostGIS toggle — no local DB setup needed, accessible from anywhere for demos. 500 MB free, sufficient for a student project. Not yet provisioned. |
| **Backend hosting** | ✅ **Render (free tier) — live** | Deployed via the Render MCP connector, auto-deploys on every push to `main`. Live at https://wildfire-aqi-backend.onrender.com (Singapore region). ⚠️ Free tier spins down after 15 min idle — first request after idle takes ~1 min to wake up. |
| **Local dev (optional)** | Docker + Docker Compose | Still useful for fully offline local development if needed, but Render + Supabase is the primary path now |
| **Version Control** | Git + GitHub | Standard, already set up for this project |

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

- **No hardware required** — every data source is a public Indian government API; nothing needs to be self-hosted or physically built.
- **No paid services required** — every tool listed has a free tier sufficient for a student/academic-scale project (data.gov.in API key is free).
- **Consistent language** — Python across backend + ML keeps the codebase simpler to maintain and reason about.
- **Open-source mapping** — avoids Google Maps billing/API key friction entirely.
- **Realistic for the project timeline** (~2–3 months) — every tool here is mainstream, well-documented, and has a low learning curve compared to more specialized alternatives.
- **India-specific caveat (resolved)** — FSI fire data has no public API (verified Aug 31, 2026); NASA FIRMS is used as the primary fire source instead, live-verified working.
