import os
from datetime import datetime, timezone
from typing import Literal

import psycopg2
import psycopg2.extras
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

load_dotenv()

DATABASE_URL = os.environ.get("DATABASE_URL")

app = FastAPI(
    title="Wildfire Risk & AQI Monitoring Platform (India)",
    version="0.2.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten before public launch
    allow_methods=["GET"],
    allow_headers=["*"],
)


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
# 2. Forest Fire Risk
# ---------------------------------------------------------------------------


@app.get("/risk/{region_id}")
def get_risk(region_id: str, days: int = Query(7, ge=1, le=90)):
    region = get_region_or_404(region_id)
    return {
        "region_id": region_id,
        "current": {
            "risk_level": region["current_risk_level"],
            "risk_score": 0.78,
            "timestamp": region["last_updated"],
            "model_version": "v1.2",
        },
        "history": [
            {"timestamp": "2026-08-29T14:00:00Z", "risk_level": "Moderate", "risk_score": 0.55},
            {"timestamp": "2026-08-28T14:00:00Z", "risk_level": "Moderate", "risk_score": 0.51},
        ][:days],
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
    return {
        "region_id": region_id,
        "current_aqi": aqi,
        "category": aqi_category(aqi),
        "dominant_pollutant": "PM2.5",
        "timestamp": region["last_updated"],
        "forecast": [
            {"timestamp": "2026-08-30T18:00:00Z", "predicted_aqi": aqi + 18, "lower_bound": aqi - 12, "upper_bound": aqi + 48},
            {"timestamp": "2026-08-31T00:00:00Z", "predicted_aqi": aqi - 22, "lower_bound": aqi - 52, "upper_bound": aqi + 8},
        ],
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
    data = [
        {"date": "2026-08-01", "risk_score": 0.35, "aqi": 45},
        {"date": "2026-08-02", "risk_score": 0.40, "aqi": 52},
    ]
    if metric == "risk":
        data = [{"date": d["date"], "risk_score": d["risk_score"]} for d in data]
    elif metric == "aqi":
        data = [{"date": d["date"], "aqi": d["aqi"]} for d in data]
    return {"region_id": region_id, "data": data[:days]}


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
