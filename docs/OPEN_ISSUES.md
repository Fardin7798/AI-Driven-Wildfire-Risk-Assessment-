# Open Issues & Implementation Notes

This document tracks upstream data source caveats, external format adjustments, and operational tracking notes.

| Issue ID | Domain | Description | Status / Resolution |
|---|---|---|---|
| ISSUE-01 | NASA FIRMS | Suomi-NPP VIIRS delivery ceases on 2 Nov 2026. Live ingestion uses NOAA-20 VIIRS, NOAA-21 VIIRS, and MODIS. | Resolved in config list (`FIRMS_SOURCES`). |
| ISSUE-02 | AQI model | AQI forecasts come from model B `aqi_station_xgb_v3` (no-station); its test numbers are a second look at the test period (see MODEL_CARD section 3). Old `wf.aq_forecasts` table is no longer read. | Resolved for serving. Dropping `wf.aq_forecasts` needs owner approval. |
| ISSUE-03 | data.gov.in CPCB | CPCB real-time API occasionally throttles or undergoes endpoint downtime during peak pollution periods. | Handled via `ENABLE_CPCB` feature flag; automatic fallback to Open-Meteo CAMS live grid. |
| ISSUE-04 | Live fire history | `fires_prev_7d/30d` read from `wf.fire_detections`; a fresh database has none. | Run once after deploy: `POST /api/v1/internal/jobs/backfill_fires` (or `python scripts/backfill.py`). |
| ISSUE-05 | Train/serve weather | Training weather is NASA POWER, live is Open-Meteo. | Same variables and units; monitor for bias. |
