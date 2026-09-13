# Engineering Methodology & Build Instructions

This document records the engineering methodology, architectural invariants, and systematic verification standards followed in the **WildfireRisk & CleanAir India** platform.

---

## 1. Core Architectural Principles

1. **Deterministic Physics Over Black-Box Models**:
   - Instead of fragile, uncalibrated black-box classifiers that suffer from covariate shift, wildfire risk is calculated using the **Canadian Forest Fire Weather Index (FWI)**.
   - Operating on live surface temperature ($T$), relative humidity ($RH$), wind velocity ($W$), and precipitation ($P$), it executes in <0.05ms with zero model drift.

2. **Global Supercomputer Forecasting Over Local Fits**:
   - Rather than training localized time-series models (e.g. Prophet) per district—which demand heavy offline retraining and continuous manual maintenance—the platform ingests the European Space Agency's **Copernicus Atmosphere Monitoring Service (CAMS)**.
   - This delivers 72-hour hourly chemical transport forecasts (PM2.5, PM10, CO, NO2, SO2, O3, optical smoke depth) across any coordinate in India.

3. **On-Demand TTL Caching Over Background Schedulers**:
   - Background crons (e.g. APScheduler) fail when deployed on free-tier containers that sleep during inactivity.
   - An in-memory 15-minute `cachetools.TTLCache` provides sub-2ms repeated responses without unpooled database leaks.

4. **Contract-First Synchronization**:
   - Strict TypeScript models in `frontend/src/types.ts` are 1-to-1 synchronized with FastAPI Pydantic responses.

---

## 2. Verification Protocol

Every subsystem must pass atomic verification commands:
```bash
# 1. Backend Integration Smoke Test
cd backend && source .venv/bin/activate && python -c "
from fastapi.testclient import TestClient
from main import app
c = TestClient(app)
assert c.get('/health').status_code == 200
assert c.get('/api/v1/districts').status_code == 200
assert c.get('/api/v1/fires/active').status_code == 200
print('Backend integration verified!')
"

# 2. Frontend Typecheck & Production Build
cd frontend && npm run build
```

---

## 3. Maintenance & Extension Guidelines

- **Adding Districts**: Extend `backend/data/indian_districts.json` with new district names, states, and coordinates. No database migrations required.
- **Adjusting Risk Breakpoints**: Fine-tune FWI category thresholds inside `backend/services/fwi_engine.py`.
- **Modifying Visual Dashboard**: Edit Bento grid modules in `frontend/src/components/BentoCards.tsx` while maintaining strict TypeScript typing in `frontend/src/types.ts`.
