# CONTEXT.md — Current State

Platform: AI-Driven Wildfire Risk Assessment, Air Quality Monitoring and Community Preparedness
(India, district level via GADM 4.1 level 2, 676 districts; country-agnostic design).

- **Branches**: `main` (owner, deployed to Render) · `backend` (agent work, merged via PR)
- **Stack**: FastAPI + Python 3.12, PostgreSQL + PostGIS (schema `wf`, Supabase), APScheduler
- **Docs**: `docs/ARCHITECTURE.md`, `docs/API.md`, `docs/DATASETS.md`, `docs/MODEL_CARD.md`,
  `docs/OPEN_ISSUES.md`, `ml/README.md`

## What runs in production
| Part | How it works |
|---|---|
| Weather | Open-Meteo forecast API, batched per request, daily 00:20 IST |
| FWI | Canadian FWI with daily carry-over, 00:50 IST; skipped for districts without weather |
| Wildfire risk | `wildfire_xgb_v2` when its artifact is deployed, else FWI fallback; 01:10 IST |
| Fires | NASA FIRMS NRT (VIIRS NOAA-20/21, MODIS), joined to districts with PostGIS |
| Air quality | Open-Meteo CAMS every 6 h; NAQI calculation; rule-based 1-3 day forecast 01:30 IST |
| Preparedness | Static NDMA-style guidance from `backend/data/seed/preparedness.json` |

## Rules
- No synthetic data, no default values standing in for missing data, no hand-written metrics.
- Training and serving share `backend/app/domain/features.py` and `fwi.py`.
- Models train on Kaggle (`ml/kaggle_*`), metrics come only from the training output.
- Tests, ruff, ruff format and mypy must pass before a PR.

## Status
- [x] Backend v2 rebuild (schema, providers, jobs, API, tests)
- [x] Production data fixes (per-job locks, batching, no fabricated values, fire stats, names)
- [x] Leaky `wildfire_xgb_v1`, CPCB-station `aqi_xgb_v1`, synthetic notebooks and invented reports removed
- [x] Wildfire v2 pipeline: FIRMS VIIRS SP + NASA POWER -> district-day dataset -> Kaggle training
- [x] `wildfire_xgb_v2` trained on Kaggle (2026-11-01) and served from `backend/models/`
- [ ] AQI model trained on CAMS history (same source as live) with persistence baseline
- [ ] Land cover (ESA WorldCover) fractions into `wf.regions`
- [ ] Frontend rebuild
