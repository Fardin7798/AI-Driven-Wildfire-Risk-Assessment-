# AGENTS.md

> **Master Agent Handbook & Developer Guide**  
> AI-Driven Wildfire Risk Assessment, Air Quality Monitoring, and Community Preparedness Platform (India)  
> Single source of truth for all AI pair programmers and contributors.

---

## 🧭 System Overview & Architecture Summary
- **Domain**: Real-time environmental intelligence, wildfire danger assessment, atmospheric air quality forecasting, and community disaster preparedness for India.
- **Target Archetype**: Full-Stack Web Application (FastAPI async microservice + React 19 / Vite SPA).
- **Core Architecture**: Decoupled, asynchronous, zero-maintenance architecture with on-demand parallel API aggregation, in-memory TTL caching, Canadian FWI mathematical engine, and WebGL vector mapping.
- **Detailed Specs**: Read `docs/architecture.md`, `docs/PRD.md`, `docs/tech-stack.md`, and `docs/api-docs.md` before making code changes.
- **Active Memory & Progress**: Read `CONTEXT.md` before starting work; update it before completing any session.
- **Systematic Feature Delivery**: Follow `systematic-build.md` for phased, atomic verification.

---

## 📁 Repository Layout & Invariants

```text
/home/shaikhfardin/Final Year Project/
├── docs/                      # Architectural specs, PRD, and boundary contracts
│   ├── PRD.md                 # 8-section requirements & acceptance criteria
│   ├── architecture.md        # System design, dataflow, and caching topology
│   ├── tech-stack.md          # Version-locked libraries & trade-off rationale
│   └── api-docs.md            # Boundary contracts for REST endpoints
├── backend/                   # FastAPI microservice
│   ├── main.py                # App entrypoint, routing, CORS, and OpenAPI docs
│   ├── services/              # Core business logic & external integrations
│   │   ├── fwi_engine.py      # Canadian Forest Fire Weather Index (FFMC, ISI, FWI)
│   │   ├── firms_service.py   # NASA FIRMS VIIRS 375m active fire integration
│   │   ├── weather_service.py # Open-Meteo async weather fetcher
│   │   ├── aqi_service.py     # Copernicus CAMS 72h forecast & CPCB NAQI formula
│   │   └── preparedness_service.py # Dynamic health advisories & emergency contacts
│   ├── data/                  # Pre-bundled Indian districts database
│   │   └── indian_districts.json
│   └── requirements.txt       # Lean Python dependencies
├── frontend/                  # React 19 + TypeScript + Vite dashboard
│   ├── src/                   # Components, pages, and MapLibre GL JS vector maps
│   └── package.json           # Client packages
├── CONTEXT.md                 # Living workspace memory & state tracker
├── systematic-build.md        # Phased build engine & atomic verification checklist
└── AGENTS.md                  # This file
```

---

## 🚫 Forbidden Zones (Hook Enforced)
1. **Auto-Generated Artifacts**: Never commit `dist/`, `.venv/`, `node_modules/`, `__pycache__/`.
2. **Private Credentials**: Never commit `.env` or API keys. Commit `.env.example` only.
3. **No Colab / Jupyter Training Traps**: All ML and meteorological calculations must run headless and deterministically in pure Python (`services/`).
4. **Zero-Stub Policy**: No placeholder comments (`// TODO`, `/* FIXME */`). Every change must be verified with exit code 0.
