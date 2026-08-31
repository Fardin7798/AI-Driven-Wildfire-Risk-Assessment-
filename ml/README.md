# ML Training

`wildfire_risk_training.ipynb` — trains an XGBoost fire-risk classifier on real
historical data (NASA FIRMS fire detections + Open-Meteo historical weather).

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
