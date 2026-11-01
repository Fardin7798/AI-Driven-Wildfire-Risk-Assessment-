# CONTEXT.md — Active Memory & Build Tracker

## Project Overview
Rebuilding the complete backend and ML infrastructure for "AI-Driven Wildfire Risk Assessment, Air Quality Monitoring and Community Preparedness Platform" for India (district-level), country-agnostic.

- **Git Branch**: `main`
- **Target Database**: PostgreSQL 16 + PostGIS 3.4 (Schema: `wf`)
- **Python Version**: 3.12+

## Phased Build Checklist

- [x] **Phase 1: Project Scaffolding, Documentation & CI/CD**
  - [x] Create `.gitignore` and `.env.example`
  - [x] Create `AGENTS.md` and `CONTEXT.md`
  - [x] Create `backend/pyproject.toml` (groups: api, pipeline, train, dev)
  - [x] Create `backend/Dockerfile`, `backend/docker-compose.yml`, `backend/render.yaml`, `backend/alembic.ini`
  - [x] Create comprehensive documentation in `docs/`: `ARCHITECTURE.md`, `DATASETS.md`, `OPEN_ISSUES.md`, `API.md`, `MODEL_CARD.md`
  - [x] Create seed data: `backend/data/seed/countries.yaml`, `backend/data/seed/preparedness.json`
  - [x] Setup GitHub Actions: `.github/workflows/ci.yml`, `.github/workflows/scheduled-jobs.yml`

- [x] **Phase 2: Database Layer & Migrations (schema `wf`, PostGIS)**
  - [x] Async SQLAlchemy 2.0 session & base
  - [x] Models: `regions`, `fire_detections`, `weather_daily`, `fwi_state`, `aq_stations`, `aq_observations`, `aq_forecasts`, `risk_predictions`, `model_versions`, `ingestion_runs`, `preparedness_items`
  - [x] RLS policies and schema permissions
  - [x] Alembic migration environment and initial schema migration

- [x] **Phase 3: Domain Core Logic & Single-Source Feature Engineering**
  - [x] `app/domain/fwi.py`: Full Canadian FWI equations (Van Wagner 1987) with daily carry-over
  - [x] `app/domain/aqi.py`: Indian NAQI piecewise linear sub-indices & categories
  - [x] `app/domain/risk_classes.py`: Risk categories & dynamic probability threshold mapping
  - [x] `app/domain/features.py`: Single Source of Truth feature generation with zero lookahead leakage

- [x] **Phase 4: Country-Agnostic Providers Layer**
  - [x] `app/providers/base.py`: Protocols & dataclasses
  - [x] `app/providers/registry.py`: Country-aware provider selector
  - [x] `app/providers/firms.py`: NASA FIRMS live NRT & area parsing
  - [x] `app/providers/open_meteo_weather.py`: Open-Meteo weather with tenacity retries
  - [x] `app/providers/open_meteo_air.py`: Open-Meteo AQ & Copernicus CAMS
  - [x] `app/providers/cpcb_datagovin.py`: CPCB via data.gov.in (with `ENABLE_CPCB` flag)
  - [x] `app/providers/nasa_power.py`: NASA POWER fallback provider

- [x] **Phase 5: ML Inference Runtime**
  - [x] `app/ml/loader.py`: Artifact loader with SHA256 checksum & feature integrity validation
  - [x] `app/ml/wildfire_predictor.py`: XGBoost inference engine with FWI fallback
  - [x] `app/ml/aqi_forecaster.py`: Prophet & seasonal persistence forecaster

- [x] **Phase 6: Business Services Layer**
  - [x] `app/services/regions_service.py`
  - [x] `app/services/fire_service.py`
  - [x] `app/services/weather_service.py`
  - [x] `app/services/air_quality_service.py`
  - [x] `app/services/risk_service.py`
  - [x] `app/services/preparedness_service.py`

- [x] **Phase 7: Scheduled Ingestion & Background Jobs**
  - [x] `app/jobs/scheduler.py` (APScheduler + Postgres advisory lock)
  - [x] Job implementations: `ingest_fires`, `ingest_weather`, `update_fwi_state`, `predict_risk`, `ingest_air_quality`, `forecast_aqi`, `retention`
  - [x] Idempotent upserts & `ingestion_runs` tracking

- [x] **Phase 8: FastAPI API Layer & Internal Jobs Endpoint**
  - [x] Application factory, lifespan, CORS, rate limiting (`slowapi`), JSON logger (`structlog`)
  - [x] Pydantic v2 schemas for all responses
  - [x] API v1 endpoints: `/health`, `/regions`, `/risk`, `/fires`, `/air-quality`, `/weather`, `/models`, `/preparedness`, `/meta`, `/internal/jobs`, `/geo/cities`

- [x] **Phase 9: ML Training Pipeline & Kaggle Notebooks (`ml/`)**
  - [x] Historical data downloaders with resumable parquet caches
  - [x] Dataset construction scripts & validation reports
  - [x] Kaggle training notebooks for Wildfire (XGBoost/RF/FWI) and AQI (Prophet)
  - [x] Operational scripts (`load_regions.py`, `compute_landcover.py`, `backfill.py`)

- [x] **Phase 10: Tests & Verification**
  - [x] Unit tests for FWI reference values, NAQI breakpoints, feature leakage, provider parsers
  - [x] Integration tests for API endpoints
  - [x] Ruff linting & mypy type-check pass

- [x] **Phase 11: Production Verification & End-to-End Audit**
  - [x] Full audit of 20 live production endpoints on Render & Supabase
  - [x] Geocoding settlement search + PostGIS coordinate bridge verified
  - [x] Fallbacks for weather and air quality active and validated
  - [x] 100% test pass (pytest 20/20, ruff 0 errors, mypy 80/80 files clean)
  - [x] Production deployment live on `main` branch


- [~] **Phase 12: Production data fixes & honest model (2026-11-01)**
  - [x] Per-job advisory locks + staggered daily chain (weather was skipped every night)
  - [x] Open-Meteo multi-location batching (weather daily, AQ every 6 h) to stop HTTP 429
  - [x] Removed silent default weather/FWI/risk values; missing data now skips or shows `has_prediction: false`
  - [x] Predictor falls back to FWI when a model feature is missing (no zero-filling); TreeSHAP top factors
  - [x] Fire stats by source/state; readable GADM names; state filter tolerant of spaces
  - [x] `/models/current` reports what is actually served; fabricated comparison numbers removed
  - [x] Retired leaky `wildfire_xgb_v1` and synthetic-data notebooks
  - [x] Wildfire v2 pipeline (FIRMS SP + NASA POWER + backend feature code) and Kaggle kernel
  - [ ] Train `wildfire_xgb_v2` (owner decides where/how) and commit artifacts
  - [ ] AQI model on the same source it is served on (CAMS) with persistence baseline
  - [ ] Landcover (WorldCover) into `wf.regions`
