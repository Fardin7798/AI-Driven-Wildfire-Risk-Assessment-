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
| Weather | Open-Meteo forecast API `models=ecmwf_ifs` (temp max/min from hourly, IST day), batched per request, daily 00:20 IST with retries at 06:20 and 12:20 IST; runs in GitHub Actions `pipeline-jobs.yml` (`python -m app.jobs.cli`), not on Render, because Render's IP hits the Open-Meteo daily quota |
| FWI | Canadian FWI with daily carry-over, right after the 00:20 IST weather run in the same GitHub Actions job; skipped for districts without weather |
| Wildfire risk | `wildfire_xgb_v3` (IFS weather) when its artifact is deployed, else FWI fallback; runs right after FWI in the same GitHub Actions job |
| Fires | NASA FIRMS NRT (VIIRS NOAA-20/21, MODIS), joined to districts with PostGIS |
| Air quality | Open-Meteo CAMS every 6 h; current NAQI from CPCB averaging (24-h means; CO/O3 max 8-h running mean; >= 16 valid hours per pollutant) of the trailing 24 h; model-B 1-3 day forecast |
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
- [x] `wildfire_xgb_v2` trained on Kaggle (2026-11-01); served until v3 (retired 2026-11-04)
- [x] AQI model B `aqi_station_xgb_v3` (PM2.5 sub-index, no-station) trained on Kaggle, served via `forecast_aqi` job and `/air-quality/forecast` endpoints
- [x] `wildfire_xgb_v3` (ECMWF IFS training weather = live weather, test 2025) trained on Kaggle 2026-11-04, wired into serving on `backend` (deploy + DB re-fill pending)
- [ ] Land cover (ESA WorldCover) fractions into `wf.regions`
- [ ] Frontend rebuild
