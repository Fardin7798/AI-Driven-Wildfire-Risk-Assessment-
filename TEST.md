# Verification & Test Protocol (TEST.md)

## Purpose
Comprehensive test suite and smoke testing commands to verify the rebuilt Wildfire Risk, Air Quality & Community Preparedness platform.

---

## 1. Runtime Environment Check

```bash
# Python 3.12+
python3 --version

# Node.js 18+ and npm
node --version
npm --version
```

---

## 2. Backend Verification (FastAPI + Scientific Engines)

### 2.1 Virtual Environment & Dependencies
```bash
cd backend
source .venv/bin/activate
pip list | grep -E "fastapi|uvicorn|httpx|cachetools|numpy"
```

### 2.2 Integration Smoke Test Suite
Verify that all scientific modules, external API clients, and routing endpoints function correctly:
```bash
cd backend
source .venv/bin/activate
python -c "
from fastapi.testclient import TestClient
from main import app
from services.fwi_engine import calculate_fire_risk
from services.firms_service import haversine_km

client = TestClient(app)

# 1. Health check
res = client.get('/health')
assert res.status_code == 200, f'Health failed: {res.text}'

# 2. Districts catalog
res = client.get('/api/v1/districts')
assert res.status_code == 200 and len(res.json().get('districts', [])) > 0

# 3. Active fires GeoJSON
res = client.get('/api/v1/fires/active')
assert res.status_code == 200 and 'features' in res.json()

# 4. FWI Scientific Engine Check
fwi = calculate_fire_risk(temp=38.0, rh=15.0, wind=25.0, rain=0.0)
assert fwi['fwi_score'] > 0 and fwi['risk_level'] in ['LOW', 'MODERATE', 'HIGH', 'VERY HIGH', 'EXTREME']

# 5. Geodesic Haversine Check
dist = haversine_km(21.05, 75.79, 21.10, 75.85)
assert 5.0 < dist < 15.0

print('✅ ALL BACKEND TEST GATES PASSED SUCCESSFULLY!')
"
```

### 2.3 Starting Backend Dev Server
```bash
cd backend
source .venv/bin/activate
uvicorn main:app --reload --port 8000
```
- Interactive Swagger UI: `http://localhost:8000/docs`
- ReDoc Documentation: `http://localhost:8000/redoc`

---

## 3. Frontend Verification (React 19 + MapLibre + Vite)

### 3.1 Type Check & Production Build
```bash
cd frontend
npm run build
```
**Expected Result:** Builds in `< 1000ms` with **0 TypeScript and 0 Vite bundling errors**.

### 3.2 Starting Frontend Dev Server
```bash
cd frontend
npm run dev
```
**Expected Result:** Vite local server spins up at `http://localhost:5173`.

---

## 4. Live API Endpoint Smoke Tests

With the backend running on `http://localhost:8000`:

```bash
# 1. Platform Health
curl -s http://localhost:8000/health | jq .

# 2. All Pre-bundled Districts
curl -s http://localhost:8000/api/v1/districts | jq .

# 3. Search Endpoint (District lookup with live weather, FWI risk, AQI and preparedness)
curl -s "http://localhost:8000/api/v1/search?query=Bhusawal" | jq .

# 4. Active Satellite Fires (GeoJSON)
curl -s http://localhost:8000/api/v1/fires/active | jq .
```

---

## 5. One-Click Full-Stack Launch

To launch both backend and frontend concurrently for evaluation or viva presentation:

```bash
./run_dev.sh
```
Press `Ctrl+C` in the terminal to stop both servers gracefully.
