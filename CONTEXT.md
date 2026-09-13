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


### 3. Design System & UI Palette Evolution
- **Theme Selection**: User opted out of dark mode and glassmorphism in favor of **Post 1: Nordic Cool Slate & Sapphire** (Clean Institutional Light Mode).
- **Core Palette**:
  - Background Canvas: Slate 50 (`#F8FAFC`)
  - Component & Card Surfaces: Solid White (`#FFFFFF`) with hairline Slate 200 (`#E2E8F0`) borders and micro-elevation (`shadow-xs` / `shadow-sm`). Zero blur/glass artifacts.
  - Typography: Slate 900 (`#0F172A`) headings, Slate 600 (`#475569`) body, Slate 500 (`#64748B`) subtitles.
  - Primary Accent: Crisp Sapphire / Deep Sky (`#0284C7` / `#0369A1`).
  - Spatial Mapping: ESRI World Light Gray Base (`Canvas/World_Light_Gray_Base`) + Reference Labels (`Canvas/World_Light_Gray_Reference`).
- **Applied Surfaces**:
  - Desktop Sidebar (`Nav.tsx`) & Mobile Nav Bar (`App.tsx`): Unified to solid white with Slate 200 border, dark slate text, active indicator pill, and light emergency speed dial.
  - Bento Grid & Spotlight Cards (`CardSpotlight.tsx`, `BentoCards.tsx`): Converted to light surfaces with high-contrast text and crisp chart gridlines.
  - Interactive Docs (`Docs.tsx`): Unified to Post 1 light theme with clean cURL panel and embedded Swagger UI.
  - Verified via Playwright automation (Screenshots in `screenshots/`).

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
- [x] Production Polish & Institutional Integrity Overhaul:
  - Eliminated raw database schema leaks, internal project hashes, and developer prompts from UI.
  - Converted NASA VIIRS satellite popup from raw Kelvin to Celsius with heat classification.
  - Added layman hazard interpretations for Canadian FWI sub-indices (FFMC fuel dryness & ISI spread rate).
  - Designed and integrated academic thesis & scientific methodology footer across Home and Docs.
  - Hardened Supabase telemetry persistence with 8s timeout and baseline telemetry snapshot fallback.
- [x] Multi-Tier Resilient Weather Engine & Dynamic City Search:
  - Eliminated static weather fallback freeze (32.5°C & 17.5 FWI across all Indian cities).
  - Upgraded Open-Meteo with custom academic User-Agent header and added resilient Tier 2 wttr.in live atmospheric fallback (unrestricted on cloud egress IPs).
  - Enabled dynamic district & city search autocomplete across any Indian city/town with Open-Meteo geocoding.
  - Normalized unicode diacritics for clean city names (e.g., Burhānpur -> Burhanpur).
  - Fixed hyphen matching in find_best_district_match (Delhi-NCR -> Delhi-NCR).
  - Verified live execution across Burhanpur, Jalgaon, Delhi, Shimla, Pune, and Jaipur (all distinct live temperatures and FWI danger levels).
- [x] Aceternity Bento Grid (Demo 2: Populated with Header and Content) + Card Spotlight:
  - Created frontend/src/components/ui/BentoGrid.tsx featuring BentoGrid and BentoGridItem with header, title, description, icon, eyebrow, and action.
  - Created frontend/src/components/ui/CardSpotlight.tsx with dynamic radial gradient tracking mouseX/mouseY using Framer Motion.
  - Calibrated semantic color palette matching project theme: Deep obsidian slate base (#090a0f, #0c0e14), subtle atmospheric sky (rgba(56,189,248,0.14)), wildfire ember (rgba(249,115,22,0.16)), and clean air emerald (rgba(16,185,129,0.15)).
  - Replaced legacy Panel wrappers in Home.tsx and BentoCards.tsx with modular BentoGridItem components.
  - Verified 100% via Playwright: desktop full-page, hover spotlight interactions, dynamic Burhanpur search, and mobile viewport responsive grid.
- [x] Post 1 Light Theme Overhaul (Nordic Cool Slate & Sapphire):
  - Completely eliminated cheap glassmorphism, heavy blurs, and dark theme in favor of Swiss/Nordic precision design.
  - Base canvas configured to #F8FAFC (cool off-white), Cards set to solid crisp #FFFFFF with hairline #E2E8F0 borders and natural micro-elevation.
  - High-contrast typography hierarchy: deep rich slate #0F172A for numbers and metrics (17:1 WCAG AAA contrast ratio), #1E293B for headings, #475569 for body.
  - Converted MapLibre RegionMap to ESRI World_Light_Gray_Base for seamless canvas integration with high-contrast road and boundary labels.
  - Re-calibrated Card Spotlight to soft ambient light-mode luminescence (rgba(2, 132, 199, 0.05)).
  - Semantic hazard badges: Low (Emerald bg #ECFDF5 / text #047857), Moderate (Amber bg #FFFBEB / text #B45309), High (Orange bg #FFF7ED / text #C2410C), Extreme (Red bg #FEF2F2 / text #B91C1C).
  - 100% verified via Playwright: desktop full-page, hover spotlight interactions, dynamic Burhanpur search, and mobile viewport.
