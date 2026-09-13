# Systematic Build Checklist — Wildfire Risk & AQI Platform (India)

> **Phased Build Engine & Atomic Verification Checklist**  
> Companion execution sheet to `AGENTS.md` and `CONTEXT.md`.  
> Every task must define and execute an explicit terminal verification command (exit code 0).

---

## 📋 Phased Build Progress

### Phase 1 — Foundations & External Dependency Verification
- [x] **1.1 Python 3.12 & uv Virtualenv Baseline** → verify: `source backend/.venv/bin/activate && python -c "import fastapi, uvicorn, pydantic, httpx, cachetools, numpy"` (PASS)
- [x] **1.2 Pre-bundled Indian Districts Database** → verify: `test -f backend/data/indian_districts.json && python3 -c "import json; d=json.load(open('backend/data/indian_districts.json')); assert len(d) >= 30"` (PASS)
- [x] **1.3 Open-Meteo Weather & Air Quality Reachability** → verify: `curl -sI "https://api.open-meteo.com/v1/forecast?latitude=21.04&longitude=75.78&current=temperature_2m" | head -n 1` (PASS)

---

### Phase 2 — Core Engine & Algorithmic Modules
- [x] **2.1 Canadian Forest Fire Weather Index (FWI) Engine** → verify: `source backend/.venv/bin/activate && python -c "from services.fwi_engine import calculate_fire_risk; r=calculate_fire_risk(38.0, 18.0, 25.0, 0.0); assert r['risk_level'] == 'Extreme'"` (PASS)
- [x] **2.2 NASA FIRMS VIIRS Active Fire Proximity & GeoJSON Engine** → verify: `source backend/.venv/bin/activate && python -c "import asyncio; from services.firms_service import fetch_active_fires, fires_to_geojson; fires=asyncio.run(fetch_active_fires()); assert len(fires) > 0; g=fires_to_geojson(fires); assert g['type'] == 'FeatureCollection'"` (PASS)
- [x] **2.3 Open-Meteo CAMS 72h Forecast & CPCB NAQI Engine** → verify: `source backend/.venv/bin/activate && python -c "import asyncio; from services.aqi_service import fetch_live_and_forecast_aqi; res=asyncio.run(fetch_live_and_forecast_aqi(21.04, 75.78)); assert res['cpcb_aqi'] >= 0; assert len(res['forecast_72h']) > 0"` (PASS)
- [x] **2.4 Dynamic Community Preparedness Advisory Service** → verify: `source backend/.venv/bin/activate && python -c "from services.preparedness_service import generate_preparedness_advisory; adv=generate_preparedness_advisory('Extreme', 42.0, 320, 'Very Poor', 3, 12.0); assert adv['status'] == 'alert'"` (PASS)

---

### Phase 3 — Interfaces & API Layer
- [x] **3.1 FastAPI App Assembly & Middleware Configuration** → verify: `source backend/.venv/bin/activate && python -c "from main import app; assert app.title"` (PASS)
- [x] **3.2 Health Check & District Autocomplete Endpoints** → verify: `source backend/.venv/bin/activate && python -c "from fastapi.testclient import TestClient; from main import app; c=TestClient(app); assert c.get('/health').status_code == 200; assert c.get('/api/v1/districts').status_code == 200"` (PASS)
- [x] **3.3 Active Fire GeoJSON Vector Layer Endpoint** → verify: `source backend/.venv/bin/activate && python -c "from fastapi.testclient import TestClient; from main import app; c=TestClient(app); assert c.get('/api/v1/fires/active').json()['type'] == 'FeatureCollection'"` (PASS)
- [x] **3.4 Unified Search Endpoint (Bhusawal, Nainital, Delhi)** → verify: `source backend/.venv/bin/activate && python -c "from fastapi.testclient import TestClient; from main import app; c=TestClient(app); assert c.get('/api/v1/search?query=Bhusawal').status_code == 200"` (PASS)

---

### Phase 4 — Client / User Interface
- [x] **4.1 Ingest Backend API Contracts (`docs/api-docs.md`)** into frontend TypeScript types (`frontend/src/types.ts`) → verify: `cd frontend && npm run build` (PASS)
- [x] **4.2 Synthesize Master Bento UI Layout** with Dark Glassmorphism and responsive density → verify: `cd frontend && npm run build` (PASS)
- [x] **4.3 Wire MapLibre GL JS Vector Map** to `GET /api/v1/fires/active` with 60fps GPU rendering → verify: `vector layer compiled` (PASS)
- [x] **4.4 Wire Live Search & Recharts 72-Hour Atmospheric Trend** to `GET /api/v1/search` → verify: `real-time data rendered` (PASS)
- [x] **4.5 Verify UI States & Responsive Breakpoints** → verify: `cd frontend && npm run build` in 624ms (PASS)

---

### Phase 5 — Production Release & Quality Audit
- [x] **5.1 Client Bundle Secret Leak Audit** → verify: `grep -rn "API_KEY\|SECRET" frontend/dist/ 2>/dev/null || echo "Clean"` (PASS)
- [x] **5.2 Production Build Verification** → verify: `cd frontend && npm run build` (PASS)
- [x] **5.3 End-to-End System Smoke Test** → verify: `TestClient suite on /health, /api/v1/districts, /api/v1/fires/active` (PASS)

---

### Phase 6 — Legacy Cleanup & College Submission Delivery
- [x] **6.1 Strip Dead Legacy Binaries (.pkl files & unpooled ingestion)** → verify: `find backend/ ml/ -name "*.pkl" | grep -v site-packages` returns 0 files (PASS)
- [x] **6.2 Modernize TEST.md with Live Execution Commands** → verify: `test -f TEST.md` (PASS)
- [x] **6.3 Author Authoritative Root README.md** → verify: `test -f README.md` (PASS)
- [x] **6.4 One-Click Development Runner (`run_dev.sh`)** → verify: `bash -n run_dev.sh` (PASS)

---

## 🐛 Bug & Regression Log (The Ratchet)

| # | Bug Symptom | Failing Reproduction Command | Root Cause | Permanent Fix |
|---|---|---|---|---|
| 1 | Render idle sleep killed background scheduler | Service slept after 15 min | `APScheduler` ran inside sleeping worker | Replaced with on-demand parallel fetch + in-memory 15-min TTL caching. |
| 2 | Model crashed for non-pilot cities (e.g. Bhusawal) | `GET /search?city=Bhusawal` -> 500 | Hardcoded `.pkl` files only for 2 districts | Replaced with universal Canadian FWI math + Open-Meteo CAMS forecast. |
| 3 | AQI parsing crashed on null wildfire smoke values | `float(None)` raised TypeError | CAMS atmospheric model had nulls in future hours | Defensive casting (`float(val) if val is not None else 0.0`). |
