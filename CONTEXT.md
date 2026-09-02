# CONTEXT.md

<!--
  HOW TO USE THIS FILE:
  At the start of every Claude Code session, say:
  "Read CONTEXT.md and continue where we left off."
  Keep this file updated as the project evolves. Delete resolved bugs.
-->

---

## Project Overview

- **Name:** AI-Driven Wildfire Risk Assessment, Air Quality Monitoring, and Community Preparedness Platform (India)
- **Description:** A web dashboard that predicts forest fire risk, monitors real-time air quality, and gives Indian communities preparedness info (evacuation routes, safety tips) — built entirely on free public Indian government APIs, no hardware.
- **Status:** Full stack live in production — backend, database, ML models (XGBoost + Prophet), frontend dashboard, AND now a `/search` endpoint covering all of India (not just the 2 pilot regions). Preparedness content is basic (hardcoded tips); alerting logic is minimal (threshold-based, no notifications).
- **Last worked on:** Fixed the generalization gap identified right after the frontend went live — `/search?city={name}` now works for ANY Indian city, using Open-Meteo's free geocoding + live weather, the same trained XGBoost model (which generalizes fine since it only needs weather features, not location-specific training), and CPCB's city-level AQI filter. `aqi` is honestly `null` (not faked) when a city has no CPCB station coverage. Live-verified against 5 real cities (Jaipur/Mumbai/Nagpur/Kargil + a 404 case) both locally and in production. Note: this endpoint does NOT provide historical trend/AQI forecast — those still require a pre-trained per-region Prophet model, which only exists for the 2 tracked regions. Also created a reusable, generic project-build template system at `~/templates/` (separate from this repo) based on this project's methodology.

---

## Tech Stack

- **Frontend:** React, TypeScript, Vite, MapLibre GL JS, Recharts
- **Backend:** Python, FastAPI, APScheduler
- **Database:** PostgreSQL + PostGIS
- **ML:** XGBoost (fire risk classification), Prophet (AQI forecasting), SHAP (explainability — stretch goal)
- **Hosting:** Render (backend, live at https://wildfire-aqi-backend.onrender.com; frontend static site, live at https://wildfire-aqi-frontend.onrender.com) + Supabase (Postgres+PostGIS, live — project `wildfire-aqi-db`, Mumbai region) — free tiers
- **Key data APIs:** Forest Survey of India (FSI) Fire Alert System, NASA FIRMS (cross-check), IMD/Open-Meteo, CPCB (via data.gov.in API), SAFAR (IITM Pune), Bhuvan/Copernicus-Sentinel (optional)
- **Dev tooling:** Claude Code, Graphify (codebase knowledge graph), Claude Task Master (PRD → tasks)

Full reasoning for each choice: see `docs/tech-stack.md`

---

## File Structure

```
/
├── docs/                     # Project documentation
│   ├── PRD_Wildfire_AQI_Platform.md
│   ├── architecture.md
│   ├── api-docs.md
│   ├── instructions.md
│   └── tech-stack.md
├── backend/                  # FastAPI app, ingestion, ML models — live at wildfire-aqi-backend.onrender.com
├── ml/                       # Training notebooks (XGBoost fire risk, Prophet AQI forecast)
├── frontend/                 # React + Vite dashboard — live at wildfire-aqi-frontend.onrender.com
├── .claude/                  # Claude Code config + Graphify skill
└── CLAUDE.md                 # Claude Code persistent instructions
```

---

## Database Schema

**regions**
- `id` — unique identifier
- `name` — region name (e.g. Nainital)
- `state` — Indian state (e.g. Uttarakhand)
- `geometry` — region polygon (PostGIS)
- `centroid` — lat/lon center point

**raw_weather**
- `region_id` — references regions
- `timestamp`, `temp`, `humidity`, `wind_speed`, `rainfall`

**raw_fire_detections**
- `lat`, `lon`, `confidence`, `frp`, `timestamp`, `source`

**raw_aqi**
- `station_id`, `region_id`, `timestamp`, `pm2_5`, `aqi_value`

**risk_scores**
- `region_id`, `timestamp`, `risk_level`, `model_version`

**aqi_forecast**
- `region_id`, `timestamp`, `predicted_aqi`, `confidence_interval`

**Relationships:**
- Each region has many weather/fire/AQI readings and risk scores.
- Fire detections are spatially joined to a region via PostGIS.

(Full schema detail: `docs/architecture.md`)

---

## Routes & Pages

**API Routes** (see `docs/api-docs.md` for full request/response specs)
| Route | Method | Description |
|-------|--------|-------------|
| `/regions` | GET | List all monitored regions with current status |
| `/regions/{region_id}` | GET | Detailed info for one region |
| `/risk/{region_id}` | GET | Current + historical fire risk |
| `/aqi/{region_id}` | GET | Current + forecasted AQI |
| `/alerts` | GET | Active high-risk/unhealthy-AQI alerts |
| `/trends/{region_id}` | GET | Historical time-series for charts |
| `/preparedness/{region_id}` | GET | Safety tips + evacuation resources |

**Frontend Pages** (planned — not yet built)
| Route | Description |
|-------|-------------|
| `/` | Map dashboard — regions, risk colors, AQI stations |
| `/region/:id` | Region detail — risk/AQI trend charts |
| `/preparedness` | Safety tips + evacuation info |

---

## Features Built

- [x] Data ingestion pipeline (weather, fire, AQI APIs) — live, hourly scheduler + manual `POST /admin/ingest` trigger, all 3 sources verified writing real rows to Supabase
- [x] Fire risk ML model (training + validation) — XGBoost, real historical FIRMS+weather data, live on Render (`xgboost-v1`)
- [x] AQI forecasting model — Prophet, real historical PM2.5 (Open-Meteo Air Quality API), live on Render
- [x] Backend API (FastAPI) — connected to real Supabase DB, live on Render
- [x] Frontend dashboard + map — React + MapLibre, live on Render, real backend data
- [x] Preparedness content + alerts — basic version live (hardcoded tips + evacuation links per region, threshold-based alerts); no notifications yet
- [x] Project planning (PRD, architecture, API docs, tech stack)
- [x] Graphify + Git/GitHub setup

---

## Current WIP & Bugs

**In progress:**
- Full stack is live end-to-end (backend, DB, ML, frontend). Remaining work is polish: better preparedness content, real alert notifications, thesis writeup, and testing. See Roadmap below.

**Known bugs:**
- None currently open. Resolved during setup: (1) Render's default Python 3.14 lacked prebuilt `pydantic-core` wheels — fixed by pinning `PYTHON_VERSION=3.12.3`. (2) Supabase's direct DB connection is IPv6-only on the free tier and Render has no IPv6 egress — fixed by using the Supavisor pooler. (3) data.gov.in silently blocks the default python-requests User-Agent — fixed with a browser-like header. (4) NASA FIRMS returns unpadded `acq_time` (e.g. `"807"` not `"0807"`) — fixed with `.zfill(4)`. (5) Frontend: `maplibre-gl` has no default export in the installed version — fixed the import style. (6) Frontend: a machine-wide `NODE_ENV=production` was silently stripping devDependencies on every `npm install` — fixed with `frontend/.npmrc` (`include=dev`).

---

## Roadmap

1. ~~Verify FSI fire data access and get a data.gov.in API key~~ ✅ **Done (Aug 31, 2026)** — FSI has no public API (confirmed), using NASA FIRMS instead. CPCB and FIRMS personal API keys obtained and live-tested successfully.
2. ~~Deploy a minimal backend skeleton~~ ✅ **Done (Aug 31, 2026)** — FastAPI backend matching `docs/api-docs.md` deployed live on Render with seed data
3. ~~Provision Supabase (Postgres+PostGIS) and connect it to the Render backend~~ ✅ **Done (Aug 31, 2026)** — schema created, seeded, connected via Supavisor pooler (fixed an IPv6/IPv4 connectivity bug in the process)
4. ~~Build data ingestion scripts (weather, fire, AQI)~~ ✅ **Done (Aug 31, 2026)** — hourly scheduler + manual trigger live, all 3 sources verified writing real data to Supabase
5. ~~Train and validate the fire-risk ML model on historical data~~ ✅ **Done (Sep 1, 2026)** — XGBoost trained in Colab on real historical FIRMS + Open-Meteo data (`ml/wildfire_risk_training.ipynb`), integrated into `ingestion.py`, live on Render (`model_version: "xgboost-v1"`). **Known limitation:** no land-cover feature yet, so hot+dry urban weather (e.g. Delhi) can read as fire-prone the same as hot+dry forest weather — v2 improvement, worth noting in the thesis.
6. ~~Build FastAPI endpoints to serve predictions + AQI data~~ ✅ **Done** — all endpoints now serve real DB/model data, no more seed/hardcoded values
7. ~~Build the React dashboard, connect to the deployed API~~ ✅ **Done (Sep 1, 2026)** — Vite+React+TS dashboard live on Render (https://wildfire-aqi-frontend.onrender.com), 3 routes, MapLibre map, real backend data throughout
8. ~~Add preparedness content and alert logic~~ ✅ **Basic version done** — hardcoded tips + evacuation links per region, threshold-based alerts. Could be expanded (more detailed tips, real notifications) but functional for MVP.
9. Testing, polish, documentation — write up the thesis/report, add unit tests, polish edge cases (loading states, empty states already handled in the frontend; error boundary/retry logic could be more robust)

---

## Rules for Claude

**Always:**
- Follow the tech stack defined in `docs/tech-stack.md` — don't substitute libraries without asking.
- Check the knowledge graph (`graphify query`) before reading files directly, per the Graphify skill setup.
- Keep all data sources free/public — no paid APIs or physical hardware.
- Reference `docs/PRD_Wildfire_AQI_Platform.md` for scope and `docs/architecture.md` for system design before implementing a new feature.

**Never:**
- Add a paid API dependency without asking first — the whole project is scoped to be free.
- Skip the `.env` pattern for API keys — never hardcode keys in source.
- Change the database schema without checking `docs/architecture.md` first.

---

## Owner & Links

- **Author:** Fardin (Fardin7798)
- **GitHub:** https://github.com/Fardin7798/AI-Driven-Wildfire-Risk-Assessment-
- **Live URL:** Backend deployed — https://wildfire-aqi-backend.onrender.com (Render, free tier, Singapore region, auto-deploys on push to `main`)
- **Other docs:** `docs/PRD_Wildfire_AQI_Platform.md`, `docs/architecture.md`, `docs/api-docs.md`, `docs/tech-stack.md`, `docs/instructions.md` (full build methodology/history)
