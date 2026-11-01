# Open Issues & Implementation Notes

This document tracks upstream data source caveats, external format adjustments, and operational tracking notes.

| Issue ID | Domain | Description | Status / Resolution |
|---|---|---|---|
| ISSUE-01 | NASA FIRMS | Suomi-NPP VIIRS delivery ceases on 2 Nov 2026. Live ingestion uses NOAA-20 VIIRS, NOAA-21 VIIRS, and MODIS. | Resolved in config list (`FIRMS_SOURCES`). |
| ISSUE-02 | AQI model | No learned AQI model is served. The earlier CPCB-station model was removed because live data is CAMS. | Next: build CAMS district history (Open-Meteo, available from ~2022) and train on Kaggle with a persistence baseline. |
| ISSUE-03 | data.gov.in CPCB | CPCB real-time API occasionally throttles or undergoes endpoint downtime during peak pollution periods. | Handled via `ENABLE_CPCB` feature flag; automatic fallback to Open-Meteo CAMS live grid. |
| ISSUE-04 | Live fire history | `fires_prev_7d/30d` read from `wf.fire_detections`; a fresh database has none. | Backfill 30 days of FIRMS NRT (`scripts/backfill.py ingest_fires`) when deploying the wildfire model. |
| ISSUE-05 | Train/serve weather | Training weather is NASA POWER, live is Open-Meteo. | Same variables and units; monitor for bias. |
