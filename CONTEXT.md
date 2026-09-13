# CONTEXT.md — Active Project State

## Project Overview
- **Name**: AI-Driven Wildfire Risk Assessment, Air Quality Monitoring, and Community Preparedness Platform (India)
- **Degree / College**: Bachelor of Engineering (CSE), Dr. BATU Lonere | Shri Sant Gadge Baba College of Engg & Tech, Bhusawal
- **Status**: Complete Full-Stack Rebuild & Verification Finished (Exit Code 0).
- **Current Milestone**: Master Prompt Frontend Rebuild & Verification Complete. Orchestrated via v0 by Vercel API Engine (`krCAKF258Wp`). Implemented polymorphic `FadeUp` Framer Motion animations, `lucide-react` iconography, Google Fonts (`Inter` + `JetBrains Mono`), 60fps GPU vector map with dynamic 50km radius proximity circle & NASA VIIRS thermal halos, 5-segment Canadian FWI danger gauge, CPCB NAQI 0-500 scale bar, and NDMA one-click telephone emergency dials.

---

## Active Architecture & Modules

### 1. Backend (`backend/`)
- **Runtime**: Python 3.12 with `uv` virtual environment (`.venv`). Standby RAM ~42MB.
- **Core Modules**:
  - `services/fwi_engine.py`: Canadian Forest Fire Weather Index (FFMC, ISI, BUI, FWI) + Fire Risk Category (Low to Extreme). Execution latency: ~0.05ms.
  - `services/firms_service.py`: NASA FIRMS VIIRS 375m active fire integration + Haversine distance calculator.
  - `services/weather_service.py`: Open-Meteo async live weather fetcher (15-min TTL cache).
  - `services/aqi_service.py`: Copernicus CAMS 72-hour hourly AQI forecast + official CPCB NAQI formula.
  - `services/preparedness_service.py`: Dynamic health guidance & emergency contacts.
  - `data/indian_districts.json`: 39 pre-bundled Indian districts.
  - `main.py`: Production-grade async FastAPI app with CORS and Swagger OpenAPI `/docs`.

### 2. Frontend (`frontend/`)
- **Stack**: React 19 + TypeScript + Vite 8 + MapLibre GL JS + Tailwind CSS v4 + Framer Motion + Lucide React + Recharts.
- **Components**:
  - `src/components/FadeUp.tsx`: Polymorphic Framer Motion entrance animation component (`ease: [0.22, 1, 0.36, 1]`).
  - `src/components/RegionMap.tsx`: 60fps GPU vector map with Carto Dark Matter style, NASA FIRMS active hotspots, 50km proximity radius ring, and interactive popups.
  - `src/components/BentoCards.tsx`: High-density Bento Grid cards (Canadian FWI RiskGauge conic gradient, Live Weather 4-metric bar, CPCB NAQI 6-pollutant grid, Recharts 72h CAMS Forecast, NDMA Preparedness & Emergency Directory).
  - `src/pages/Home.tsx`: Main dashboard with instant district search, native datalist autocomplete for 39 districts, quick-focus chips, and all 5 mandatory UI states (Empty, Loading Skeleton, Error Banner with Retry, Partial, and Populated Bento Grid).
  - `src/components/Nav.tsx`: Clean dark navigation bar with direct link to interactive Swagger `/docs` and live telemetry status.

---

## Verification Status
- [x] Backend integration test passed (exit code 0).
- [x] Frontend `npm run build` passed in 1.32s with 0 errors (exit code 0).
- [x] Frontend `npm run lint` (`oxlint`) passed with 0 errors.
- [x] Secret leak audit passed (0 tokens or keys in `dist/`).
- [x] End-to-end full stack smoke tests passed (exit code 0).
- [x] Legacy binary files (.pkl) and dead scripts cleaned (0 orphaned models).
- [x] Master prompt specification implemented across all frontend components via v0 API engine.
- [x] One-click development runner `./run_dev.sh` verified with both servers running concurrently.
