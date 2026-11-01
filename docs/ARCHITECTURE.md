# Platform Architecture — Wildfire Risk, Air Quality & Preparedness

## System Topology & Data Flow

```mermaid
graph TD
    subgraph External Data Sources
        FIRMS[NASA FIRMS Area API<br/>VIIRS NOAA-20/21, MODIS (NRT)]
        OM_W[Open-Meteo Weather API<br/>Daily Forecast]
        OM_AQ[Open-Meteo CAMS Air Quality<br/>Criteria Pollutants + 72h Forecast]
        CPCB[data.gov.in CPCB Real-time<br/>Optional Hourly Station Feed]
        GADM[GADM 4.1<br/>India Level-2 District Polygons]
        ESA[ESA WorldCover 10m<br/>Vegetation & Cropland Fractions]
    end

    subgraph Ingestion & Scheduling Engine
        SCHED[APScheduler In-Process<br/>+ Postgres Advisory Lock]
        JOBS[Async Ingestion Jobs<br/>Fires / Weather / AQ / Retention]
        INT_API[POST /internal/jobs/:job<br/>X-Job-Token Protected]
        GH_CRON[GitHub Actions Cron<br/>Awake Keep-Alive Trigger]
    end

    subgraph Domain Engine & Storage
        DB[(PostgreSQL 16 + PostGIS 3.4<br/>Schema: wf<br/>Supabase / Local Docker)]
        FWI_ENG[Canadian FWI Physics Engine<br/>FFMC, DMC, DC, ISI, BUI, FWI]
        NAQI_ENG[CPCB NAQI Standard Calculator<br/>Piecewise Linear Aggregation]
        FEAT_ENG[Single-Source Feature Engine<br/>features.py: Training & Live]
    end

    subgraph Machine Learning Runtime
        XGB[XGBoost Wildfire v2<br/>FWI fallback when no artifact]
        AQIF[AQI Forecaster<br/>Persistence baseline]
        SHAP_EXP[TreeSHAP Explainer<br/>Top 3 Drivers]
    end

    subgraph API Presentation Layer
        FASTAPI[FastAPI v1 Engine<br/>Uvicorn Async ASGI]
        RATELIMIT[SlowAPI Rate Limiter<br/>IP-based Quotas]
        SCHEMAS[Pydantic v2 Contract<br/>RFC 9457 Problem Details]
    end

    FIRMS --> JOBS
    OM_W --> JOBS
    OM_AQ --> JOBS
    CPCB --> JOBS
    GH_CRON --> INT_API --> JOBS
    SCHED --> JOBS

    JOBS --> DB
    JOBS --> FWI_ENG --> DB
    JOBS --> NAQI_ENG --> DB

    DB --> FEAT_ENG --> XGB --> DB
    DB --> AQIF --> DB

    DB --> FASTAPI
    XGB --> SHAP_EXP --> FASTAPI
    FASTAPI --> RATELIMIT --> SCHEMAS
```

## Architectural Layers
1. **Transport Layer (`app/api/`)**:
   - HTTP routing, input validation (Pydantic v2), slowapi rate limiting, CORS configuration, RFC 9457 error envelopes.
2. **Services Layer (`app/services/`)**:
   - High-level business orchestrations querying database repositories and provider clients.
3. **Domain Core (`app/domain/`)**:
   - Canadian FWI calculation (Van Wagner 1987) with daily carry-over state.
   - Indian CPCB NAQI calculation with pollutant sub-index aggregation.
   - Dynamic risk categorization.
   - `features.py`: Exact same feature generation used in both offline model training and online serving to eliminate train-serve skew.
4. **Data Providers (`app/providers/`)**:
   - Country-agnostic interfaces (`base.py`) with provider implementations for FIRMS, Open-Meteo, CPCB, and NASA POWER.
5. **Database Layer (`app/db/`)**:
   - Isolated `wf` schema in PostgreSQL with PostGIS geometric spatial indexes (`GIST`) and Row Level Security (`RLS`).
