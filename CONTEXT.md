# CONTEXT.md — Active Project State

## Project Overview
- **Name**: AI-Driven Wildfire Risk Assessment, Air Quality Monitoring, and Community Preparedness Platform (India)
- **Degree / College**: Bachelor of Engineering (CSE), Dr. BATU Lonere | Shri Sant Gadge Baba College of Engg & Tech, Bhusawal
- **Status**: Complete Full-Stack Rebuild & Verification Finished (Exit Code 0).
- **Current Milestone**: Full Audit, Hardening & Vite Code-Splitting Completed. MapLibre GL raster tile optimization deployed, FastAPI coordinate validation + Indian geocoding disambiguation verified, Supabase PostGIS integrated (`laasumeyzxskujxrxpcx`), all 39 Indian districts seeded, live NASA Suomi-NPP VIIRS South Asia active satellite fire stream connected (zero mock data), real-time query audit logging active, and dynamic environment resolution verified.

---

## Active Architecture & Modules

### 1. Backend (`backend/`)
- **Runtime**: Python 3.12 with `uv` virtual environment (`.venv`).
- **Core Modules**:
  - `services/fwi_engine.py`: Van Wagner (1987) Canadian Forest Fire Weather Index (FFMC, ISI, BUI, FWI) + Fire Risk Category. Execution latency: ~0.05ms.
  - `services/firms_service.py`: NASA FIRMS VIIRS 375m active satellite fire integration with automatic fallback to NASA's official live public South Asia feed (100% genuine real fires, zero mock data).
  - `services/weather_service.py`: Open-Meteo async live weather fetcher (15-min TTL cache).
  - `services/aqi_service.py`: Copernicus CAMS 72-hour hourly AQI forecast + official CPCB NAQI formula.
  - `services/supabase_service.py`: Non-blocking async persistence layer for Supabase PostgreSQL + PostGIS audit logging (`telemetry_logs` table). Reads dynamic credentials strictly from environment variables (`override=True`).
  - `services/preparedness_service.py`: Dynamic health guidance & emergency contacts.
  - `data/indian_districts.json`: 39 pre-bundled Indian districts with PostGIS centroids and eco-zones.
  - `main.py`: Production-grade async FastAPI app with CORS, dynamic fallback resolution, input coordinate validation (-90 to 90, -180 to 180), multi-tier district matching + Indian geocoding fallback, and `/health`, `/api/v1/search`, `/api/v1/fires`, `/api/v1/telemetry/recent`.

### 2. Frontend (`frontend/`)
- **Stack**: React 19 + TypeScript + Vite 8 + MapLibre GL JS + Tailwind CSS v4 + Framer Motion + Lucide React + Recharts.
- **Optimization**:
  - `vite.config.ts`: Custom Rollup manual chunking splitting monolithic bundle (1.72 MB -> 254 kB main bundle, 85% reduction), grouping `vendor-map`, `vendor-charts`, `vendor-motion`, and `vendor-icons`.
  - `src/components/RegionMap.tsx`: ESRI ArcGIS World Dark Gray Dual-Layer (Base + High-Contrast Reference labels on top) with WebGL vector overlays (NASA fires + 50km radius buffer ring), zero font glyph dependencies, ResizeObserver to prevent container height collapse.
  - `src/components/BentoCards.tsx`: High-density Bento Grid cards (Canadian FWI RiskGauge conic gradient, Live Weather 4-metric bar, CPCB NAQI 6-pollutant grid, Recharts 72h CAMS Forecast, NDMA Preparedness & Emergency Directory).
  - `src/pages/Docs.tsx`: Native Interactive API Specification console with live endpoint testing, cURL snippets, and embedded FastAPI Swagger UI view (zero external tab redirect).
  - `src/App.tsx`: React Router integration with dedicated `/docs` route and mobile floating bottom navigation bar.
  - `src/pages/Home.tsx`: Main dashboard with dynamic health badge, live Supabase telemetry audit panel, instant district search, native datalist autocomplete for 39 districts, and quick-focus chips.
  - `src/components/Nav.tsx`: Clean dark navigation bar with dynamic `DOCS_URL` and live telemetry status.
  - `src/lib/api.ts`: Centralized API service dynamically resolving `VITE_API_BASE` and `DOCS_URL`.

---

## Verification Status
- [x] Backend edge-case test suite: 8/8 tests passed with 100% success (exit code 0).
- [x] Coordinate boundary validation (-90 to 90 lat, -180 to 180 lon) returns 422 for out-of-bounds inputs.
- [x] Geocoding disambiguation prioritizes Indian national matches (`country_code == 'IN'`).
- [x] Zero hardcoded secrets in source files (all keys resolved via `.env`).
- [x] Zero mock fire fallbacks (live NASA VIIRS public feed streams real active fires).
- [x] Zero hardcoded `localhost` URLs in frontend (dynamically resolved via `DOCS_URL` and `VITE_API_BASE`).
- [x] Frontend `npm run build` passed with 0 errors and zero chunk size warnings (exit code 0).
- [x] Supabase PostGIS database seeded with 39 districts; real-time telemetry audit trail operational.
- [x] GitHub repository updated and synced with `origin/main`.
- [x] One-click development runner `./run_dev.sh` verified.
