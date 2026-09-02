import logging
import os
from datetime import datetime, timezone
from typing import Literal

import joblib
import psycopg2
import psycopg2.extras
import requests
from apscheduler.schedulers.background import BackgroundScheduler
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import ingestion

load_dotenv()
logger = logging.getLogger("uvicorn.error")

DATABASE_URL = os.environ.get("DATABASE_URL")

# Prophet AQI forecast models — one per region, trained in
# ml/aqi_forecasting_training.ipynb. Loaded lazily/defensively: missing a
# model file for a region just means no forecast for that region, not a crash.
_AQI_MODELS = {}
for _region_id in ("uk-nainital", "dl-delhi"):
    _path = os.path.join(os.path.dirname(__file__), f"aqi_forecast_{_region_id}.pkl")
    if os.path.exists(_path):
        _AQI_MODELS[_region_id] = joblib.load(_path)

app = FastAPI(
    title="Wildfire Risk & AQI Monitoring Platform (India)",
    version="0.3.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten before public launch
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


def run_ingestion_job():
    try:
        result = ingestion.fetch_all()
        logger.info(f"Ingestion job completed: {result}")
    except Exception as e:
        logger.error(f"Ingestion job failed: {e}")


scheduler = BackgroundScheduler()
# Per docs/architecture.md cadence: weather ~15-60min, AQI hourly, fire every
# few hours. Using one combined hourly job for MVP simplicity (free-tier
# Render spins down when idle, so this only runs while the service is awake).
scheduler.add_job(run_ingestion_job, "interval", hours=1, id="ingestion_job")


@app.on_event("startup")
def start_scheduler():
    scheduler.start()


@app.on_event("shutdown")
def stop_scheduler():
    scheduler.shutdown(wait=False)


def get_db_connection():
    if not DATABASE_URL:
        raise HTTPException(status_code=500, detail="DATABASE_URL not configured")
    return psycopg2.connect(DATABASE_URL, cursor_factory=psycopg2.extras.RealDictCursor)


def get_region_or_404(region_id: str) -> dict:
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id AS region_id, name, state, current_risk_level, current_aqi,
                       last_updated, ST_X(centroid) AS lon, ST_Y(centroid) AS lat
                FROM regions WHERE id = %s
                """,
                (region_id,),
            )
            row = cur.fetchone()
    finally:
        conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="Region not found")
    return {
        "region_id": row["region_id"],
        "name": row["name"],
        "state": row["state"],
        "centroid": {"lat": float(row["lat"]), "lon": float(row["lon"])},
        "current_risk_level": row["current_risk_level"],
        "current_aqi": int(row["current_aqi"]),
        "last_updated": row["last_updated"].isoformat().replace("+00:00", "Z"),
    }




# ---------------------------------------------------------------------------
# Health check (used by TEST.md smoke tests, Render health checks)
# ---------------------------------------------------------------------------


@app.get("/health")
def health():
    return {"status": "ok", "time": datetime.now(timezone.utc).isoformat()}


@app.post("/admin/ingest")
def trigger_ingestion():
    """Manually trigger a data ingestion run (for demo/testing).
    No auth required for MVP per docs/api-docs.md — this only pulls and
    writes read-only ingestion data, it does not touch user data."""
    try:
        return ingestion.fetch_all()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------------------------
# 1. Regions
# ---------------------------------------------------------------------------


@app.get("/regions")
def list_regions():
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id AS region_id, name, state, current_risk_level, current_aqi,
                       last_updated, ST_X(centroid) AS lon, ST_Y(centroid) AS lat
                FROM regions ORDER BY id
                """
            )
            rows = cur.fetchall()
    finally:
        conn.close()
    return [
        {
            "region_id": r["region_id"],
            "name": r["name"],
            "state": r["state"],
            "centroid": {"lat": float(r["lat"]), "lon": float(r["lon"])},
            "current_risk_level": r["current_risk_level"],
            "current_aqi": int(r["current_aqi"]),
            "last_updated": r["last_updated"].isoformat().replace("+00:00", "Z"),
        }
        for r in rows
    ]


@app.get("/regions/{region_id}")
def get_region(region_id: str):
    region = get_region_or_404(region_id)
    return {**region, "geometry": "GeoJSON Polygon"}


# ---------------------------------------------------------------------------
# 1b. Search any city in India (live, on-demand — not a stored/tracked region)
# ---------------------------------------------------------------------------


def geocode_india(city: str) -> dict:
    resp = requests.get(
        "https://geocoding-api.open-meteo.com/v1/search",
        params={"name": city, "count": 5, "country": "IN"},
        timeout=15,
    )
    resp.raise_for_status()
    results = resp.json().get("results", [])
    if not results:
        raise HTTPException(status_code=404, detail=f"No Indian city found matching '{city}'")
    r = results[0]
    return {
        "name": r["name"],
        "state": r.get("admin1", ""),
        "lat": r["latitude"],
        "lon": r["longitude"],
    }


def live_weather(lat: float, lon: float) -> dict:
    resp = requests.get(
        "https://api.open-meteo.com/v1/forecast",
        params={
            "latitude": lat,
            "longitude": lon,
            "current": "temperature_2m,relative_humidity_2m,wind_speed_10m,precipitation",
            "timezone": "Asia/Kolkata",
        },
        timeout=15,
    )
    resp.raise_for_status()
    c = resp.json()["current"]
    return {
        "temp": c["temperature_2m"],
        "humidity": c["relative_humidity_2m"],
        "wind_speed": c["wind_speed_10m"],
        "rainfall": c["precipitation"],
    }


def live_aqi_for_city(city: str) -> dict | None:
    if not ingestion.CPCB_API_KEY:
        return None
    resp = requests.get(
        "https://api.data.gov.in/resource/3b01bcb8-0b14-4abf-b6f2-c1bfd384ba69",
        params={
            "api-key": ingestion.CPCB_API_KEY,
            "format": "json",
            "limit": 50,
            "filters[city]": city,
        },
        headers=ingestion.BROWSER_HEADERS,
        timeout=20,
    )
    resp.raise_for_status()
    records = resp.json().get("records", [])
    pm25_values = [
        float(r["avg_value"])
        for r in records
        if r.get("pollutant_id") == "PM2.5" and r.get("avg_value") not in (None, "", "NA")
    ]
    if not pm25_values:
        return None
    avg = round(sum(pm25_values) / len(pm25_values))
    return {"current_aqi": avg, "category": aqi_category(avg), "stations_used": len(pm25_values)}


@app.get("/search")
def search_city(city: str = Query(..., min_length=2)):
    """Live, on-demand lookup for ANY city in India — not limited to the
    pre-tracked regions in the `regions` table. Fire risk uses the same
    trained model as tracked regions (it only needs weather, so it
    genuinely generalizes anywhere). AQI uses a live CPCB city filter.
    No historical trend or AQI forecast is available here — those only
    exist for tracked regions (see /regions, /trends)."""
    location = geocode_india(city)
    weather = live_weather(location["lat"], location["lon"])

    risk_level, risk_score, model_version = None, None, None
    if ingestion._risk_model is not None:
        score = float(
            ingestion._risk_model.predict_proba(
                [[weather["temp"], weather["humidity"], weather["wind_speed"], weather["rainfall"]]]
            )[0][1]
        )
        risk_score = round(score, 4)
        risk_level = (
            "Extreme" if score >= 0.75 else "High" if score >= 0.5 else "Moderate" if score >= 0.25 else "Low"
        )
        model_version = "xgboost-v1"

    aqi = live_aqi_for_city(location["name"])

    return {
        "query": city,
        "resolved_location": location,
        "weather": weather,
        "risk_level": risk_level,
        "risk_score": risk_score,
        "model_version": model_version,
        "aqi": aqi,
        "note": "Live on-demand lookup — not a tracked region. No historical trend or AQI forecast available (those require a pre-trained per-region model). AQI is None if no CPCB station data was found for this city.",
    }


# ---------------------------------------------------------------------------
# 2. Forest Fire Risk
# ---------------------------------------------------------------------------


@app.get("/risk/{region_id}")
def get_risk(region_id: str, days: int = Query(7, ge=1, le=90)):
    get_region_or_404(region_id)
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """SELECT risk_level, risk_score, timestamp, model_version FROM risk_scores
                   WHERE region_id = %s ORDER BY timestamp DESC LIMIT 1""",
                (region_id,),
            )
            current = cur.fetchone()
            cur.execute(
                """SELECT timestamp, risk_level, risk_score FROM risk_scores
                   WHERE region_id = %s AND timestamp > now() - (%s || ' days')::interval
                   ORDER BY timestamp DESC OFFSET 1""",
                (region_id, days),
            )
            history = cur.fetchall()
    finally:
        conn.close()

    if not current:
        # no risk score computed yet for this region — ingestion hasn't run
        raise HTTPException(status_code=404, detail="No risk data yet for this region — run ingestion first")

    return {
        "region_id": region_id,
        "current": {
            "risk_level": current["risk_level"],
            "risk_score": float(current["risk_score"]),
            "timestamp": current["timestamp"].isoformat().replace("+00:00", "Z"),
            "model_version": current["model_version"],
        },
        "history": [
            {
                "timestamp": h["timestamp"].isoformat().replace("+00:00", "Z"),
                "risk_level": h["risk_level"],
                "risk_score": float(h["risk_score"]),
            }
            for h in history
        ],
    }


# ---------------------------------------------------------------------------
# 3. Air Quality
# ---------------------------------------------------------------------------


def aqi_category(aqi: int) -> str:
    if aqi <= 50:
        return "Good"
    if aqi <= 100:
        return "Satisfactory"
    if aqi <= 200:
        return "Moderate"
    if aqi <= 300:
        return "Poor"
    if aqi <= 400:
        return "Very Poor"
    return "Severe"


@app.get("/aqi/{region_id}")
def get_aqi(region_id: str):
    region = get_region_or_404(region_id)
    aqi = region["current_aqi"]

    forecast = []
    forecast_note = None
    model = _AQI_MODELS.get(region_id)
    if model is not None:
        future = model.make_future_dataframe(periods=3)
        pred = model.predict(future).tail(3)
        forecast = [
            {
                "timestamp": row["ds"].strftime("%Y-%m-%dT00:00:00Z"),
                "predicted_aqi": round(max(row["yhat"], 0)),
                "lower_bound": round(max(row["yhat_lower"], 0)),
                "upper_bound": round(max(row["yhat_upper"], 0)),
            }
            for _, row in pred.iterrows()
        ]
        forecast_note = "Prophet model trained on ~1 year of real historical PM2.5 (Open-Meteo Air Quality API). Forecast is PM2.5-based, not the full CPCB sub-index formula."
    else:
        forecast_note = "No forecast model available for this region yet."

    return {
        "region_id": region_id,
        "current_aqi": aqi,
        "category": aqi_category(aqi),
        "dominant_pollutant": "PM2.5",
        "timestamp": region["last_updated"],
        "forecast": forecast,
        "forecast_note": forecast_note,
    }


# ---------------------------------------------------------------------------
# 4. Alerts
# ---------------------------------------------------------------------------


@app.get("/alerts")
def get_alerts():
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id AS region_id, current_risk_level, current_aqi, last_updated FROM regions")
            regions = cur.fetchall()
    finally:
        conn.close()

    alerts = []
    for region in regions:
        last_updated = region["last_updated"].isoformat().replace("+00:00", "Z")
        if region["current_risk_level"] in ("High", "Extreme"):
            alerts.append({
                "region_id": region["region_id"],
                "alert_type": "forest_fire_risk",
                "severity": region["current_risk_level"],
                "message": "High forest fire risk due to low humidity and high wind speed.",
                "triggered_at": last_updated,
            })
        if region["current_aqi"] > 300:
            alerts.append({
                "region_id": region["region_id"],
                "alert_type": "air_quality",
                "severity": aqi_category(int(region["current_aqi"])),
                "message": "AQI has reached unhealthy levels.",
                "triggered_at": last_updated,
            })
    return alerts


# ---------------------------------------------------------------------------
# 5. Trends
# ---------------------------------------------------------------------------


@app.get("/trends/{region_id}")
def get_trends(
    region_id: str,
    days: int = Query(30, ge=1, le=365),
    metric: Literal["risk", "aqi", "both"] = "both",
):
    get_region_or_404(region_id)
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """SELECT date_trunc('day', timestamp)::date AS date, avg(risk_score) AS risk_score
                   FROM risk_scores WHERE region_id = %s
                     AND timestamp > now() - (%s || ' days')::interval
                   GROUP BY 1 ORDER BY 1""",
                (region_id, days),
            )
            risk_rows = {r["date"].isoformat(): float(r["risk_score"]) for r in cur.fetchall()}

            cur.execute(
                """SELECT date_trunc('day', timestamp)::date AS date, avg(pollutant_avg) AS aqi
                   FROM raw_aqi WHERE region_id = %s AND pollutant_id = 'PM2.5'
                     AND timestamp > now() - (%s || ' days')::interval
                   GROUP BY 1 ORDER BY 1""",
                (region_id, days),
            )
            aqi_rows = {r["date"].isoformat(): round(float(r["aqi"]), 1) for r in cur.fetchall()}
    finally:
        conn.close()

    all_dates = sorted(set(risk_rows) | set(aqi_rows))
    data = []
    for date in all_dates:
        point = {"date": date}
        if metric in ("risk", "both") and date in risk_rows:
            point["risk_score"] = risk_rows[date]
        if metric in ("aqi", "both") and date in aqi_rows:
            point["aqi"] = aqi_rows[date]
        data.append(point)

    return {
        "region_id": region_id,
        "data": data,
        "note": "Real data, aggregated daily from actual ingestion — history is only as deep as the pipeline has been running (started Aug 31, 2026).",
    }


# ---------------------------------------------------------------------------
# 6. Preparedness
# ---------------------------------------------------------------------------


@app.get("/preparedness/{region_id}")
def get_preparedness(region_id: str):
    region = get_region_or_404(region_id)
    return {
        "region_id": region_id,
        "current_risk_level": region["current_risk_level"],
        "tips": [
            "Keep an emergency go-bag ready.",
            "Monitor official Forest Survey of India (FSI) and State Forest Department updates.",
            "Avoid outdoor burning and report smoke/fire sightings to the nearest forest office.",
        ],
        "evacuation_resources": [
            {"title": "Forest Survey of India — Fire Alerts", "url": "https://fsiforestfire.gov.in/"},
            {"title": "National Disaster Management Authority (NDMA)", "url": "https://ndma.gov.in/"},
        ],
    }
