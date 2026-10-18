# CONTEXT.md — Active Memory & Build Tracker

## Project Overview
Rebuilding the complete backend and ML infrastructure for "AI-Driven Wildfire Risk Assessment, Air Quality Monitoring and Community Preparedness Platform" for India (district-level), country-agnostic.

- **Git Branch**: `rebuild/backend-v2`
- **Target Database**: PostgreSQL 16 + PostGIS 3.4 (Schema: `wf`)
- **Python Version**: 3.12+

## Phased Build Checklist

- [x] **Phase 1: Project Scaffolding, Documentation & CI/CD**
  - [x] Create `.gitignore` and `.env.example`
  - [x] Create `AGENTS.md` and `CONTEXT.md`
  - [ ] Create `backend/pyproject.toml` (groups: api, pipeline, train, dev)
  - [ ] Create `backend/Dockerfile`, `backend/docker-compose.yml`, `backend/render.yaml`, `backend/alembic.ini`
  - [ ] Create comprehensive documentation in `docs/`: `ARCHITECTURE.md`, `DATASETS.md`, `OPEN_ISSUES.md`, `API.md`, `MODEL_CARD.md`
  - [ ] Create seed data: `backend/data/seed/countries.yaml`, `backend/data/seed/preparedness.json`
  - [ ] Setup GitHub Actions: `.github/workflows/ci.yml`, `.github/workflows/scheduled-jobs.yml`

- [x] **Phase 2: Database Layer & Migrations (schema `wf`, PostGIS)**
  - [ ] Async SQLAlchemy 2.0 session & base
  - [ ] Models: `regions`, `fire_detections`, `weather_daily`, `fwi_state`, `aq_stations`, `aq_observations`, `aq_forecasts`, `risk_predictions`, `model_versions`, `ingestion_runs`, `preparedness_items`
  - [ ] RLS policies and schema permissions
  - [ ] Alembic migration environment and initial schema migration

- [x] **Phase 3: Domain Core Logic & Single-Source Feature Engineering**
  - [ ] `app/domain/fwi.py`: Full Canadian FWI equations (Van Wagner 1987) with daily carry-over
  - [ ] `app/domain/aqi.py`: Indian NAQI piecewise linear sub-indices & categories
  - [ ] `app/domain/risk_classes.py`: Risk categories & dynamic probability threshold mapping
  - [ ] `app/domain/features.py`: Single Source of Truth feature generation with zero lookahead leakage

- [x] **Phase 4: Country-Agnostic Providers Layer**
  - [ ] `app/providers/base.py`: Protocols & dataclasses
  - [ ] `app/providers/registry.py`: Country-aware provider selector
  - [ ] `app/providers/firms.py`: NASA FIRMS live NRT & area parsing
  - [ ] `app/providers/open_meteo_weather.py`: Open-Meteo weather with tenacity retries
  - [ ] `app/providers/open_meteo_air.py`: Open-Meteo AQ & Copernicus CAMS
  - [ ] `app/providers/cpcb_datagovin.py`: CPCB via data.gov.in (with `ENABLE_CPCB` flag)
  - [ ] `app/providers/nasa_power.py`: NASA POWER fallback provider

- [x] **Phase 5: ML Inference Runtime**
  - [ ] `app/ml/loader.py`: Artifact loader with SHA256 checksum & feature integrity validation
  - [ ] `app/ml/wildfire_predictor.py`: XGBoost inference engine with FWI fallback
  - [ ] `app/ml/aqi_forecaster.py`: Prophet & seasonal persistence forecaster

- [x] **Phase 6: Business Services Layer**
  - [ ] `app/services/regions_service.py`
  - [ ] `app/services/fire_service.py`
  - [ ] `app/services/weather_service.py`
  - [ ] `app/services/air_quality_service.py`
  - [ ] `app/services/risk_service.py`
  - [ ] `app/services/preparedness_service.py`

- [ ] **Phase 7: Scheduled Ingestion & Background Jobs**
  - [ ] `app/jobs/scheduler.py` (APScheduler + Postgres advisory lock)
  - [ ] Job implementations: `ingest_fires`, `ingest_weather`, `update_fwi_state`, `predict_risk`, `ingest_air_quality`, `forecast_aqi`, `retention`
  - [ ] Idempotent upserts & `ingestion_runs` tracking

- [ ] **Phase 8: FastAPI API Layer & Internal Jobs Endpoint**
  - [ ] Application factory, lifespan, CORS, rate limiting (`slowapi`), JSON logger (`structlog`)
  - [ ] Pydantic v2 schemas for all responses
  - [ ] API v1 endpoints: `/health`, `/regions`, `/risk`, `/fires`, `/air-quality`, `/weather`, `/models`, `/preparedness`, `/meta`, `/internal/jobs`

- [ ] **Phase 9: ML Training Pipeline & Kaggle Notebooks (`ml/`)**
  - [ ] Historical data downloaders with resumable parquet caches
  - [ ] Dataset construction scripts & validation reports
  - [ ] Kaggle training notebooks for Wildfire (XGBoost/RF/FWI) and AQI (Prophet)
  - [ ] Operational scripts (`load_regions.py`, `compute_landcover.py`, `backfill.py`)

- [ ] **Phase 10: Tests & Verification**
  - [ ] Unit tests for FWI reference values, NAQI breakpoints, feature leakage, provider parsers
  - [ ] Integration tests for API endpoints
  - [ ] Ruff linting & mypy type-check pass
