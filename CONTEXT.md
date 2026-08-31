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
- **Status:** Planning complete, all 3 core APIs verified live — ready to start implementation
- **Last worked on:** Live-verified NASA FIRMS, CPCB/data.gov.in, and Open-Meteo with real personal API keys (Aug 31, 2026) — all confirmed returning real India data. Fixed stale Canada/BC references in CONTEXT.md and TEST.md. Next: set up backend project structure + Docker Compose.

---

## Tech Stack

- **Frontend:** React, TypeScript, Vite, MapLibre GL JS, Recharts
- **Backend:** Python, FastAPI, APScheduler
- **Database:** PostgreSQL + PostGIS
- **ML:** XGBoost (fire risk classification), Prophet (AQI forecasting), SHAP (explainability — stretch goal)
- **Hosting:** Local/Docker for MVP; Render or Railway free tier if a live demo is needed
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
│   └── tech-stack.md
├── backend/                  # (not yet created) FastAPI app, ingestion, ML models
├── frontend/                 # (not yet created) React + Vite dashboard
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

- [ ] Data ingestion pipeline (weather, fire, AQI APIs)
- [ ] Fire risk ML model (training + validation)
- [ ] AQI forecasting model
- [ ] Backend API (FastAPI)
- [ ] Frontend dashboard + map
- [ ] Preparedness content + alerts
- [x] Project planning (PRD, architecture, API docs, tech stack)
- [x] Graphify + Git/GitHub setup

---

## Current WIP & Bugs

**In progress:**
- Nothing coded yet — next step is setting up the backend ingestion pipeline (weather + fire + AQI API calls).

**Known bugs:**
- None yet (no code written).

---

## Roadmap

1. ~~Verify FSI fire data access and get a data.gov.in API key~~ ✅ **Done (Aug 31, 2026)** — FSI has no public API (confirmed), using NASA FIRMS instead. CPCB and FIRMS personal API keys obtained and live-tested successfully.
2. Set up backend project structure + Docker Compose (Postgres + PostGIS)
3. Build data ingestion scripts (weather, fire, AQI) — test each API independently
3. Train and validate the fire-risk ML model on historical data
4. Build FastAPI endpoints to serve predictions + AQI data
5. Build the React dashboard, connect to the API
6. Add preparedness content and alert logic
7. Testing, polish, documentation

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
- **Live URL:** none yet
- **Other docs:** `docs/PRD_Wildfire_AQI_Platform.md`, `docs/architecture.md`, `docs/api-docs.md`, `docs/tech-stack.md`
