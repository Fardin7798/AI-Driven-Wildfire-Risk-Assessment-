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

- [x] **Phase 7: Scheduled Ingestion - [x] **Phase 7: Scheduled Ingestion & Background Jobs** Background Jobs**
  - [x] `app/jobs/scheduler.py` (APScheduler + Postgres advisory lock)
  - [x] Job implementations: `ingest_fires`, `ingest_weather`, `update_fwi_state`, `predict_risk`, `ingest_air_quality`, `forecast_aqi`, `retention`
  - [x] Idempotent upserts & `ingestion_runs` tracking

- [x] **Phase 8: FastAPI API Layer - [x] **Phase 8: FastAPI API Layer & Internal Jobs Endpoint** Internal Jobs Endpoint**
  - [x] Application factory, lifespan, CORS, rate limiting (`slowapi`), JSON logger (`structlog`)
  - [x] Pydantic v2 schemas for all responses
  - [x] API v1 endpoints: `/health`, `/regions`, `/risk`, `/fires`, `/air-quality`, `/weather`, `/models`, `/preparedness`, `/meta`, `/internal/jobs`, `/geo/cities`

- [x] **Phase 9: ML Training Pipeline - [x] **Phase 9: ML Training Pipeline & Kaggle Notebooks (`ml/`)** Kaggle Notebooks (`ml/`)**
  - [x] Historical data downloaders with resumable parquet caches
  - [x] Dataset construction scripts - [x] Dataset construction scripts & validation reports validation reports
  - [x] Kaggle training notebooks for Wildfire (XGBoost/RF/FWI) and AQI (Prophet)
  - [x] Operational scripts (`load_regions.py`, `compute_landcover.py`, `backfill.py`)

- [x] **Phase 10: Tests - [x] **Phase 10: Tests & Verification** Verification**
  - [x] Unit tests for FWI reference values, NAQI breakpoints, feature leakage, provider parsers
  - [x] Integration tests for API endpoints
  - [x] Ruff linting - [x] Ruff linting & mypy type-check pass mypy type-check pass
