# Wildfire Risk, Air Quality & Community Preparedness Backend (v2)

Production-grade FastAPI backend and machine learning pipeline predicting wildfire risk and air quality trajectories across Indian districts.

## Key Features
- **Wildfire Risk**: XGBoost district-day model (`wildfire_xgb_v2`, NASA FIRMS VIIRS NOAA-20 labels + NASA POWER weather, 2019-2024) with Canadian FWI fallback. See docs/MODEL_CARD.md.
- **Air Quality**: Indian National AQI (NAQI) calculation (CPCB standard) and a rule-based 1-3 day persistence forecast (learned AQI model not yet deployed).
- **Active Satellite Detections**: Live streaming thermal anomalies from NASA FIRMS Area API.
- **Atmospheric Weather**: Live synoptic metrics and ERA5 reanalysis via Open-Meteo with tenacity retries.
- **Safety Preparedness**: Official civil defense safety directives and emergency speed-dials (NDMA standard).
- **Security & Schema**: All data strictly encapsulated in PostgreSQL schema `wf` with PostGIS spatial indexes and Row Level Security.

## Local Development
```bash
# 1. Spin up PostgreSQL 16 + PostGIS 3.4
docker compose up -d db

# 2. Setup Virtual Environment
python3.12 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev,pipeline]"

# 3. Apply Alembic Migrations
alembic upgrade head

# 4. Start Development Server
uvicorn app.main:app --reload --port 8000
```
