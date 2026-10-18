# Open Issues & Implementation Notes

This document tracks upstream data source caveats, external format adjustments, and operational tracking notes.

| Issue ID | Domain | Description | Status / Resolution |
|---|---|---|---|
| ISSUE-01 | NASA FIRMS | Suomi-NPP VIIRS delivery ceases on 2 Nov 2026. Live ingestion uses NOAA-20 VIIRS, NOAA-21 VIIRS, and MODIS. | Resolved in config list (`FIRMS_SOURCES`). |
| ISSUE-02 | Open-Meteo AQ | Historical CAMS AQ data before September 2022 has limited global geographic granularity. | Pipeline uses available window (Sep 2022 - present) and supports NASA POWER fallback for climatological features. |
| ISSUE-03 | data.gov.in CPCB | CPCB real-time API occasionally throttles or undergoes endpoint downtime during peak pollution periods. | Handled via `ENABLE_CPCB` feature flag; automatic fallback to Open-Meteo CAMS live grid. |
| ISSUE-04 | Model Weights | Production weights (>50 MB) excluded from git tracking. Small inference weights committed under `backend/models/`. | Automated download hook from remote storage when production weight exceeds threshold. |
