# AGENTS.md — Wildfire Risk & Air Quality Platform (Backend v2)

## Project Overview
Production-grade backend and ML pipeline for "AI-Driven Wildfire Risk Assessment, Air Quality Monitoring and Community Preparedness Platform" for India (district-level), architected to be country-agnostic.

## Architecture Layers
- **Database (`wf` schema)**: PostgreSQL + PostGIS (Supabase in prod, `postgis/postgis:16-3.4` in local dev). RLS enforced on all tables.
- **Providers Layer (`app/providers/`)**: Country-agnostic protocol interfaces for FIRMS, Open-Meteo Weather, Open-Meteo AQ / CAMS, CPCB (data.gov.in), and NASA POWER fallback.
- **Domain Core (`app/domain/`)**:
  - Canadian Forest Fire Weather Index (FWI) system (FFMC, DMC, DC, ISI, BUI, FWI) with daily carry-over.
  - Indian National AQI (NAQI) piecewise linear sub-index aggregator.
  - Risk class categorization engine.
  - Single Source of Truth `features.py` shared by offline training and live inference without leakage.
- **ML Runtime (`app/ml/`)**: Model loader, XGBoost inference engine with FWI fallback, Prophet/persistence AQI forecasting.
- **Business Services (`app/services/`)**: Async database operations and business logic.
- **Background Jobs (`app/jobs/`)**: APScheduler with Postgres advisory locking and `X-Job-Token` protected HTTP endpoints.
- **API (`app/api/`)**: FastAPI, Pydantic v2 schemas, RFC 9457 errors, rate limiting, and structured JSON logs.
- **ML Pipeline (`ml/`)**: Data acquisition, spatial joining, landcover filtering, dataset generation, validation, and training notebooks.

## Ground Rules
- Work exclusively on branch `main`.
- Zero hardcoded secrets; all config via `.env`.
- All tables strictly within `wf` schema; never alter `public` schema.
- Python 3.12, type hints everywhere, strict linting (`ruff`), and type checking (`mypy`).
- All tests must pass (exit code 0) before advancing phases.
