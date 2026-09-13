# Tech Stack Specification

## AI-Driven Wildfire Risk Assessment & Air Quality Monitoring Platform (India)

---

## 1. Core Runtime & Language Specification

| Component | Technology | Version | Purpose |
|---|---|---|---|
| **Backend Runtime** | Python (CPython) | 3.12+ | Asynchronous backend API and scientific calculations. |
| **Package Manager** | uv (Astral) | Latest | Rust-based blazing fast virtual environment and dependency manager. |
| **Frontend Runtime** | Node.js / Browser | Node 20+ / ES2022 | Client build tooling and modern browser execution. |
| **Frontend Language** | TypeScript | ~5.8+ | End-to-end type safety for API contracts, GeoJSON, and component props. |

---

## 2. Framework & Key Libraries

### Backend Stack
- **FastAPI (`>=0.115.0`)**: High-performance async ASGI web framework.
- **Uvicorn (`>=0.30.0`)**: Lightning-fast ASGI production web server.
- **Pydantic (`>=2.9.0`)**: Rust-powered strict schema validation and data modeling.
- **HTTPX (`>=0.27.0`)**: Fully async HTTP client for concurrent external API aggregation.
- **Cachetools (`>=5.5.0`)**: High-efficiency in-memory TTL caching.
- **NumPy (`>=1.26.0`)**: Vectorized numerical array and mathematical operations.

### Frontend Stack
- **React (`^19.0.0`)**: Modern declarative component rendering.
- **Vite (`^6.0.0`)**: Next-generation instant HMR build tool.
- **MapLibre GL JS (`^5.0.0`)**: WebGL hardware-accelerated vector map engine.
- **Tailwind CSS (`^4.0.0`)**: Utility-first modern CSS framework with CSS variables.
- **Recharts (`^2.15.0`)**: Composable SVG charting library for time-series forecasts.
- **React Router DOM (`^7.0.0`)**: Declarative client-side routing.

---

## 3. Data Storage & Persistence

1. **In-Memory Volatile Cache**: `cachetools.TTLCache` (maxsize=100, TTL=900s) for live weather, satellite fire points, and AQI snapshots.
2. **Static GeoJSON / Centroids**: Pre-compiled `backend/data/indian_districts.json` (~80KB) containing verified geographic coordinates of Indian districts.
3. **Optional Cloud Database**: Supabase PostgreSQL + PostGIS (for persistent bookmarking, audit logs, and historical queries).

---

## 4. Strict Trade-Off Justifications (Why X and NOT Y)

| Decision | Chosen | Rejected Alternative | Engineering Rationale |
|---|---|---|---|
| **Backend Framework** | **FastAPI** | Go (Gin) / Node.js | Go and Node lack native scientific libraries for meteorological indices (FWI) and require building custom math from scratch. FastAPI provides native OpenAPI Swagger `/docs` crucial for university defense. |
| **Wildfire Engine** | **Canadian FWI Standard** | Heavy Colab Retraining Loop | Retraining custom tree models per district is fragile and failed outside trained cities. FWI is a globally recognized physics-based standard that executes in 0.05ms with 0 training required. |
| **AQI Forecasting** | **Copernicus CAMS via Open-Meteo** | Per-City Prophet Pickle Models | Prophet models require 40MB+ per city, take 500MB+ in compile dependencies, and fail on unseen districts. Open-Meteo provides 72-hour hourly CAMS atmospheric forecasts for all coordinates in India with 0 server compute load. |
| **Map Rendering Engine** | **MapLibre GL JS** | Leaflet | Leaflet renders markers into the DOM, causing severe lag and mobile freezing when rendering thousands of NASA satellite fire points. MapLibre utilizes WebGL GPU hardware acceleration for 60fps clustering. |
| **Frontend Architecture** | **React + Vite (SPA)** | Next.js (SSR) | Next.js requires a Node server runtime that suffers 10–15s cold starts on free hosting tiers. Vite produces a purely static build (`dist/`) deployable to Cloudflare Pages or Vercel with zero cold start. |

---

## 5. Version-Lock Table

```
fastapi>=0.115.0
uvicorn[standard]>=0.30.0
pydantic>=2.9.0
python-dotenv>=1.0.1
httpx>=0.27.0
cachetools>=5.5.0
numpy>=1.26.0

react^19.0.0
react-dom^19.0.0
maplibre-gl^5.0.0
recharts^2.15.0
tailwindcss^4.0.0
vite^6.0.0
```
