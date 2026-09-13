# Project Context & Coding Guidelines

## Project: WildfireRisk & CleanAir India
AI-Driven Wildfire Risk Assessment, Air Quality Monitoring, and Community Preparedness Platform (India).

### Key Architectural Invariants
1. **Zero Colab / Zero Heavy ML Models**: The platform does NOT use offline Prophet or XGBoost `.pkl` files. It relies on:
   - **Canadian Forest Fire Weather Index (FWI)** pure math formulation (`backend/services/fwi_engine.py`).
   - **Copernicus Atmosphere Monitoring Service (CAMS)** via Open-Meteo Air Quality API (`backend/services/aqi_service.py`).
   - **NASA FIRMS VIIRS 375m** active fire detection + Haversine geodesic proximity (`backend/services/firms_service.py`).
2. **On-Demand Caching**: In-memory 15-minute `cachetools.TTLCache` replaces complex background database cron schedulers.
3. **Frontend**: React 19 + TypeScript + Vite + MapLibre GL JS (WebGL vector map) + Tailwind CSS v4 + Recharts.

### Fast Development & Test Commands
```bash
# Backend verification
cd backend && source .venv/bin/activate && python -c "from fastapi.testclient import TestClient; from main import app; c = TestClient(app); assert c.get('/health').status_code == 200"

# Backend dev server
cd backend && source .venv/bin/activate && uvicorn main:app --reload --port 8000

# Frontend build & typecheck
cd frontend && npm run build

# One-click launch
./run_dev.sh
```
