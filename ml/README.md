# ML Training

## Files

- `wildfire_risk_training.ipynb` — XGBoost fire-risk classifier (NASA FIRMS + Open-Meteo weather)
- `aqi_forecasting_training.ipynb` — Prophet AQI (PM2.5) forecasting, one model per region (Open-Meteo Air Quality historical API)

## wildfire_risk_training.ipynb

Trains an XGBoost fire-risk classifier on real historical data (NASA FIRMS fire detections + Open-Meteo historical weather).

## How to use

1. Upload this notebook to Google Colab (colab.research.google.com → File → Upload notebook)
2. Replace `FIRMS_MAP_KEY` in the second code cell with your own free key if the
   shared one hits a rate limit (get one: https://firms.modaps.eosdis.nasa.gov/api/map_key/)
3. Run all cells (Runtime → Run all)
4. First run: keep `SAMPLE_SIZE = 500` for a quick test (~2-3 min). Once
   confirmed working, increase it (or remove the `.sample()` line) to train
   on the full dataset.
5. Download the trained `fire_risk_model.pkl` at the end.

## Verified working (Sep 1, 2026)

- FIRMS historical query (60 days back): 868 rows returned
- Open-Meteo historical weather: real data returned for a test point/date

## Optional: agent-driven training via Colab MCP

If you've set up the Colab MCP server (see `~/.claude.json`), you can instead
ask your Claude Code session to open this notebook in a browser tab, connect
via `open_colab_browser_connection`, and run/iterate on it for you.

## aqi_forecasting_training.ipynb

Trains a Prophet time-series model per region to forecast AQI (PM2.5) using
real historical data from Open-Meteo's Air Quality API (CAMS reanalysis) —
free, no key needed, ~1 year of daily data available.

1. Upload to Colab, Run all — no API keys needed at all for this one
2. Downloads `aqi_forecast_uk-nainital.pkl` and `aqi_forecast_dl-delhi.pkl`
3. Verified working (Sep 1, 2026): 366 days of real daily PM2.5 data returned for Delhi
