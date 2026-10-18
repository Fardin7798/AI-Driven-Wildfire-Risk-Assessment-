# Datasets, Provenance & Attributions

This platform aggregates multiple open scientific datasets for environmental risk assessment across India.

## 1. NASA FIRMS (Fire Information for Resource Management System)
- **Source**: NASA LANCE (Land, Atmosphere Near real-time Capability for EOSDIS)
- **Satellites/Sensors**:
  - NOAA-20 VIIRS 375m (NRT)
  - NOAA-21 VIIRS 375m (NRT)
  - Terra & Aqua MODIS 1km (NRT)
- **License**: Public Domain (NASA Open Data Policy)
- **Attribution**: "We acknowledge the use of data and/or imagery from NASA's Fire Information for Resource Management System (FIRMS) (https://earthdata.nasa.gov/firms), part of the NASA Earth Observing System Data and Information System (EOSDIS)."
- **Live Endpoint**: `https://firms.modaps.eosdis.nasa.gov/api/area/csv/{MAP_KEY}/{SOURCE}/{west,south,east,north}/{DAY_RANGE}`
- **Historical Data**: Country Yearly Summary CSVs (India 2019-2025) placed in `data/raw/firms/`.

## 2. Open-Meteo Weather API (ERA5 Reanalysis & Forecast)
- **Source**: Open-Meteo API using ECMWF ERA5 reanalysis and high-resolution numerical weather prediction models.
- **License**: Creative Commons Attribution 4.0 International (CC BY 4.0)
- **Attribution**: "Weather data courtesy of Open-Meteo (https://open-meteo.com) under CC BY 4.0, derived from ECMWF ERA5 and national meteorological services."
- **Endpoints**:
  - Forecast: `https://api.open-meteo.com/v1/forecast`
  - Historical: `https://archive-api.open-meteo.com/v1/archive`

## 3. Open-Meteo Air Quality API (Copernicus CAMS)
- **Source**: Copernicus Atmosphere Monitoring Service (CAMS) Global and Regional atmospheric composition forecasts.
- **License**: Open Data under Copernicus Sentinel Data Policy & Open-Meteo CC BY 4.0
- **Attribution**: "Air quality forecasts provided by Open-Meteo using Copernicus Atmosphere Monitoring Service (CAMS) chemical transport simulation."
- **Endpoint**: `https://air-quality-api.open-meteo.com/v1/air-quality`

## 4. Central Pollution Control Board (CPCB) India via data.gov.in
- **Source**: National Air Quality Monitoring Programme (NAMP) & Continuous Ambient Air Quality Monitoring Stations (CAAQMS) via Open Government Data (OGD) Platform India.
- **License**: Government Open Data License - India (GODL)
- **Attribution**: "Air quality station monitoring data courtesy of Central Pollution Control Board (CPCB), Ministry of Environment, Forest and Climate Change, published on data.gov.in."
- **Endpoint**: `https://api.data.gov.in/resource/3b01bcb8-0b14-4abf-b6f2-c1bfd384ba69`

## 5. GADM Database of Global Administrative Areas (v4.1)
- **Source**: GADM (https://gadm.org) India Level-2 (Districts)
- **License**: Free for academic and non-commercial research use.
- **Attribution**: "Administrative boundaries derived from GADM version 4.1."

## 6. ESA WorldCover 10m 2021
- **Source**: European Space Agency (ESA) WorldCover 10 m 2021 v200 based on Sentinel-1 and Sentinel-2 data.
- **License**: Creative Commons Attribution 4.0 International (CC BY 4.0)
- **Attribution**: "Land cover classification courtesy of ESA WorldCover project 2021 / contains modified Copernicus Sentinel data (2021) processed by ESA WorldCover consortium."
