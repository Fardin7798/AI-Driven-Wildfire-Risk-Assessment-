# CONTEXT.md — Active Project State

## Project Overview
- **Name**: AI-Driven Wildfire Risk Assessment, Air Quality Monitoring, and Community Preparedness Platform (India)
- **Degree / College**: Bachelor of Engineering (CSE), Dr. BATU Lonere | Shri Sant Gadge Baba College of Engg & Tech, Bhusawal
- **Status**: Complete Full-Stack Rebuild & Verification Finished (Exit Code 0). Both Backend (FastAPI async microservice) and Frontend (React 19 + MapLibre GL JS + Bento Dashboard) are fully operational, cleaned of all legacy debt, and verified.
- **Current Milestone**: Phase 6 Complete (Final Polish & College Delivery Ready). All legacy `.pkl` binaries and unpooled ingestion scripts permanently deleted, `TEST.md` modernized, root `README.md` created with viva talking points, and `run_dev.sh` full-stack launcher added.

---

## Active Architecture & Modules

### 1. Backend (`backend/`)
- **Runtime**: Python 3.12 with `uv` virtual environment (`.venv`). Standby RAM ~42MB.
- **Core Modules**:
  - `services/fwi_engine.py`: Canadian Forest Fire Weather Index (FFMC, ISI, BUI, FWI) + Fire Risk Category (Low to Extreme).
  - `services/firms_service.py`: NASA FIRMS VIIRS 375m active fire integration + Haversine distance calculator.
  - `services/weather_service.py`: Open-Meteo async live weather fetcher.
  - `services/aqi_service.py`: Copernicus CAMS 72-hour hourly AQI forecast + official CPCB NAQI formula.
  - `services/preparedness_service.py`: Dynamic health guidance & emergency contacts.
  - `data/indian_districts.json`: 39 pre-bundled Indian districts.
  - `main.py`: Production-grade async FastAPI app with CORS and Swagger OpenAPI `/docs`.

### 2. Frontend (`frontend/`)
- **Stack**: React 19 + TypeScript + Vite 6 + MapLibre GL JS + Tailwind CSS v4 + Recharts.
- **Components**:
  - `src/components/RegionMap.tsx`: Vector map with Carto Dark Matter style, NASA FIRMS active satellite hotspots with glowing pulse, and selected district centroid with 50km radius indicator.
  - `src/components/BentoCards.tsx`: High-density Bento Grid cards (Wildfire Risk, Weather, CPCB AQI, 72h Forecast Chart, Preparedness).
  - `src/pages/Home.tsx`: Main dashboard with instant district search, native datalist autocomplete, and quick-focus chips (Bhusawal, Nainital, Delhi, Pune, etc.).
  - `src/components/Nav.tsx`: Clean dark navigation bar with direct link to interactive Swagger `/docs`.

---

## 4 System Blueprints (`docs/`)
- `docs/PRD.md`: Strict 8-section product requirements document.
- `docs/architecture.md`: System topology, mathematical FWI pipeline, and caching architecture.
- `docs/tech-stack.md`: Version-locked runtime and strict cross-language trade-off justifications.
- `docs/api-docs.md`: Public REST API contracts.

---

## Verification Status
- [x] Backend integration test passed (exit code 0).
- [x] Frontend `npm run build` passed in 624ms (exit code 0).
- [x] Secret leak audit passed (0 tokens or keys in `dist/`).
- [x] End-to-end full stack smoke tests passed (exit code 0).
- [x] Legacy binary files (.pkl) and dead scripts cleaned (0 orphaned models).
- [x] Authoritative root `README.md` and `TEST.md` updated.
- [x] One-click launcher `run_dev.sh` verified.
