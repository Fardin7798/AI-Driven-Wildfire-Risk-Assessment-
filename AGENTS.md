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
- **ML Runtime (`app/ml/`)**: Model loader, XGBoost wildfire inference with FWI fallback and TreeSHAP factors, rule-based persistence AQI forecasting.
- **Business Services (`app/services/`)**: Async database operations and business logic.
- **Background Jobs (`app/jobs/`)**: APScheduler with Postgres advisory locking and `X-Job-Token` protected HTTP endpoints.
- **API (`app/api/`)**: FastAPI, Pydantic v2 schemas, RFC 9457 errors, rate limiting, and structured JSON logs.
- **ML Pipeline (`ml/`)**: FIRMS + NASA POWER downloaders, spatial join to districts, dataset builder, training script and Kaggle kernel (see ml/README.md).

## Ground Rules
- `main` is the owner's branch; automated agents work on branch `backend` and open a PR to main.
- Never commit synthetic data or hand-written metrics; metrics come only from training output.
- Zero hardcoded secrets; all config via `.env`.
- All tables strictly within `wf` schema; never alter `public` schema.
- Python 3.12, type hints everywhere, strict linting (`ruff`), and type checking (`mypy`).
- All tests must pass (exit code 0) before advancing phases.
