"""
Data ingestion pipeline — pulls from the 3 verified free India data sources
and writes into the Supabase Postgres+PostGIS database.

Sources (see docs/tech-stack.md for verification notes):
  - Open-Meteo        -> raw_weather        (no key needed)
  - NASA FIRMS         -> raw_fire_detections (MAP_KEY)
  - CPCB / data.gov.in -> raw_aqi            (API key)

Run directly for a one-off pull:  python3 ingestion.py
Or import fetch_all() and call it from a scheduler (see main.py).
"""
import os
import requests
import psycopg2
import psycopg2.extras
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.environ.get("DATABASE_URL")
NASA_FIRMS_MAP_KEY = os.environ.get("NASA_FIRMS_MAP_KEY")
CPCB_API_KEY = os.environ.get("CPCB_DATA_GOV_IN_API_KEY")

# India bounding box (west, south, east, north) for the FIRMS area query
INDIA_BBOX = "68,8,97,37"

# data.gov.in blocks the default python-requests User-Agent — send a
# browser-like one, or every call hangs until it times out.
BROWSER_HEADERS = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"}

def get_conn():
    return psycopg2.connect(DATABASE_URL, cursor_factory=psycopg2.extras.RealDictCursor)


def get_regions(conn):
    with conn.cursor() as cur:
        cur.execute(
            "SELECT id, name, state, ST_X(centroid) AS lon, ST_Y(centroid) AS lat FROM regions"
        )
        return cur.fetchall()


# ---------------------------------------------------------------------------
# 1. Weather (Open-Meteo) — no key needed
# ---------------------------------------------------------------------------

def fetch_weather(conn):
    regions = get_regions(conn)
    inserted = 0
    for r in regions:
        resp = requests.get(
            "https://api.open-meteo.com/v1/forecast",
            params={
                "latitude": r["lat"],
                "longitude": r["lon"],
                "current": "temperature_2m,relative_humidity_2m,wind_speed_10m,precipitation",
                "timezone": "Asia/Kolkata",
            },
            timeout=15,
        )
        resp.raise_for_status()
        cur_data = resp.json()["current"]
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO raw_weather (region_id, timestamp, temp, humidity, wind_speed, rainfall)
                   VALUES (%s, %s, %s, %s, %s, %s)""",
                (
                    r["id"],
                    cur_data["time"],
                    cur_data["temperature_2m"],
                    cur_data["relative_humidity_2m"],
                    cur_data["wind_speed_10m"],
                    cur_data["precipitation"],
                ),
            )
        inserted += 1
    conn.commit()
    return inserted

# ---------------------------------------------------------------------------
# 2. Fire detections (NASA FIRMS)
# ---------------------------------------------------------------------------

def fetch_fire_detections(conn):
    if not NASA_FIRMS_MAP_KEY:
        raise RuntimeError("NASA_FIRMS_MAP_KEY not set")
    url = f"https://firms.modaps.eosdis.nasa.gov/api/area/csv/{NASA_FIRMS_MAP_KEY}/VIIRS_SNPP_NRT/{INDIA_BBOX}/1"
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    lines = resp.text.strip().split("\n")
    if len(lines) < 2:
        return 0  # header only, no detections today

    header = lines[0].split(",")
    inserted = 0
    with conn.cursor() as cur:
        for line in lines[1:]:
            vals = line.split(",")
            row = dict(zip(header, vals))
            timestamp = f"{row['acq_date']}T{row['acq_time'].zfill(4)[:2]}:{row['acq_time'].zfill(4)[2:]}:00Z"
            cur.execute(
                """INSERT INTO raw_fire_detections (lat, lon, confidence, frp, timestamp, source)
                   VALUES (%s, %s, %s, %s, %s, %s)""",
                (
                    float(row["latitude"]),
                    float(row["longitude"]),
                    row.get("confidence"),
                    float(row.get("frp") or 0),
                    timestamp,
                    "NASA_FIRMS",
                ),
            )
            inserted += 1
    conn.commit()
    return inserted

# ---------------------------------------------------------------------------
# 3. AQI (CPCB via data.gov.in)
# ---------------------------------------------------------------------------

def fetch_aqi(conn):
    if not CPCB_API_KEY:
        raise RuntimeError("CPCB_DATA_GOV_IN_API_KEY not set")
    regions = get_regions(conn)
    inserted = 0
    for r in regions:
        resp = requests.get(
            "https://api.data.gov.in/resource/3b01bcb8-0b14-4abf-b6f2-c1bfd384ba69",
            params={
                "api-key": CPCB_API_KEY,
                "format": "json",
                "limit": 50,
                "filters[state]": r["state"],
            },
            headers=BROWSER_HEADERS,
            timeout=20,
        )
        resp.raise_for_status()
        records = resp.json().get("records", [])
        aqi_values = []
        with conn.cursor() as cur:
            for rec in records:
                avg_value = rec.get("avg_value")
                if not avg_value or avg_value in ("NA", ""):
                    continue
                try:
                    avg_value = float(avg_value)
                except ValueError:
                    continue
                cur.execute(
                    """INSERT INTO raw_aqi (station_id, region_id, timestamp, pollutant_id, pollutant_avg)
                       VALUES (%s, %s, now(), %s, %s)""",
                    (rec.get("station"), r["id"], rec.get("pollutant_id"), avg_value),
                )
                inserted += 1
                if rec.get("pollutant_id") == "PM2.5":
                    aqi_values.append(avg_value)

            # crude proxy: use average PM2.5 as a stand-in for AQI until a
            # proper CPCB sub-index calculation is implemented
            if aqi_values:
                avg_pm25 = sum(aqi_values) / len(aqi_values)
                cur.execute(
                    "UPDATE regions SET current_aqi = %s, last_updated = now() WHERE id = %s",
                    (round(avg_pm25), r["id"]),
                )
    conn.commit()
    return inserted


# ---------------------------------------------------------------------------
# 4. Fire risk score — rule-based v1 (real inputs, not ML yet)
#
# Full ML training needs weeks of historical data we don't have yet.
# This is an honest interim: a simplified fire-danger formula driven by
# REAL weather + REAL nearby fire detections, not a hardcoded number.
# ---------------------------------------------------------------------------

def compute_risk(conn):
    regions = get_regions(conn)
    updated = 0
    with conn.cursor() as cur:
        for r in regions:
            cur.execute(
                """SELECT humidity, wind_speed, temp FROM raw_weather
                   WHERE region_id = %s ORDER BY timestamp DESC LIMIT 1""",
                (r["id"],),
            )
            w = cur.fetchone()
            if not w:
                continue

            cur.execute(
                """SELECT count(*) AS n FROM raw_fire_detections
                   WHERE timestamp > now() - interval '24 hours'
                     AND lat BETWEEN %s - 1 AND %s + 1
                     AND lon BETWEEN %s - 1 AND %s + 1""",
                (r["lat"], r["lat"], r["lon"], r["lon"]),
            )
            fire_count = cur.fetchone()["n"]

            humidity = float(w["humidity"] or 50)
            wind = float(w["wind_speed"] or 0)
            temp = float(w["temp"] or 25)

            score = (1 - humidity / 100) * 0.45
            score += min(wind / 40, 1) * 0.25
            score += min(fire_count / 5, 1) * 0.20
            score += (0.10 if temp > 35 else 0.0)
            score = round(min(max(score, 0), 1), 2)

            if score >= 0.75:
                level = "Extreme"
            elif score >= 0.5:
                level = "High"
            elif score >= 0.25:
                level = "Moderate"
            else:
                level = "Low"

            cur.execute(
                """INSERT INTO risk_scores (region_id, timestamp, risk_level, risk_score, model_version)
                   VALUES (%s, now(), %s, %s, %s)""",
                (r["id"], level, score, "rule-based-v1"),
            )
            cur.execute(
                "UPDATE regions SET current_risk_level = %s WHERE id = %s",
                (level, r["id"]),
            )
            updated += 1
    conn.commit()
    return updated


def fetch_all():
    conn = get_conn()
    try:
        results = {
            "weather_rows": fetch_weather(conn),
            "fire_rows": fetch_fire_detections(conn),
            "aqi_rows": fetch_aqi(conn),
            "risk_regions_updated": compute_risk(conn),
        }
    finally:
        conn.close()
    return results


if __name__ == "__main__":
    print(fetch_all())
