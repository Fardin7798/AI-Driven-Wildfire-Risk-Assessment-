import os
import sys

_current_dir = os.path.dirname(os.path.abspath(__file__))
if _current_dir not in sys.path:
    sys.path.insert(0, _current_dir)

import re
import json
import asyncio
import urllib.parse
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from services.fwi_engine import calculate_fire_risk
from services.firms_service import fetch_active_fires, find_nearby_fires, fires_to_geojson
from services.weather_service import fetch_live_weather
from services.aqi_service import fetch_live_and_forecast_aqi
from services.preparedness_service import generate_preparedness_advisory
from services.supabase_service import log_telemetry, get_recent_telemetry_logs, check_supabase_health

load_dotenv()

app = FastAPI(
    title="AI-Driven Wildfire Risk Assessment & Air Quality Platform (India)",
    description="Production-grade API providing scientific Canadian FWI fire danger rating, NASA FIRMS VIIRS 375m active satellite fire correlation, Copernicus CAMS 72-hour AQI forecasts, Supabase persistent audit telemetry, and actionable community preparedness advisories across India.",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={
            "error": True,
            "message": "An internal error occurred while streaming environmental telemetry.",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    )

DATA_PATH = os.path.join(os.path.dirname(__file__), "data", "indian_districts.json")
try:
    with open(DATA_PATH, "r") as f:
        DISTRICTS_DB: List[Dict[str, Any]] = json.load(f)
except Exception:
    DISTRICTS_DB = []

def normalize_str(s: str) -> str:
    return re.sub(r'[^a-zA-Z0-9]', '', s).lower()

def find_best_district_match(query_str: str) -> Optional[Dict[str, Any]]:
    norm_query = normalize_str(query_str)
    if not norm_query:
        return None

    # Priority 1: Exact alphanumeric match on name or ID
    for d in DISTRICTS_DB:
        if norm_query == normalize_str(d["name"]) or norm_query == normalize_str(d["id"]):
            return d

    # Priority 2: Prefix match or token prefix
    clean = re.sub(r'[^a-zA-Z0-9\s]', ' ', query_str).lower().strip()
    for d in DISTRICTS_DB:
        d_clean = re.sub(r'[^a-zA-Z0-9\s]', ' ', d["name"]).lower().strip()
        if d_clean.startswith(clean) or normalize_str(d["name"]).startswith(norm_query):
            return d
        tokens = d_clean.split()
        if any(t.startswith(clean) or clean.startswith(t) for t in tokens if len(t) >= 3):
            return d

    # Priority 3: Substring match
    if len(norm_query) >= 3:
        for d in DISTRICTS_DB:
            if norm_query in normalize_str(d["name"]) or norm_query in normalize_str(d.get("state", "")):
                return d

    return None

@app.get("/health")
async def health_check():
    db_health = await check_supabase_health()
    return {
        "status": "healthy",
        "service": "Wildfire Risk & Air Quality Engine (India)",
        "version": "1.0.0",
        "districts_loaded": len(DISTRICTS_DB),
        "database": db_health,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

@app.get("/api/v1/districts")
async def list_districts(search: Optional[str] = None):
    if not search:
        return {"total": len(DISTRICTS_DB), "districts": DISTRICTS_DB}
    q = search.lower().strip()
    filtered = [d for d in DISTRICTS_DB if q in d["name"].lower() or q in d["state"].lower()]
    if filtered:
        return {"total": len(filtered), "districts": filtered}

    import httpx, unicodedata, urllib.parse
    geo_url = f"https://geocoding-api.open-meteo.com/v1/search?name={urllib.parse.quote(q)}&count=6&language=en&format=json"
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(geo_url)
            if resp.status_code == 200 and resp.json().get("results"):
                geo_results = []
                for r in resp.json()["results"]:
                    if r.get("country_code") == "IN":
                        clean_name = unicodedata.normalize('NFKD', r["name"]).encode('ASCII', 'ignore').decode('utf-8') or r["name"]
                        geo_results.append({
                            "id": f"geo-{r['id']}",
                            "name": clean_name,
                            "state": r.get("admin1", "India"),
                            "lat": r["latitude"],
                            "lon": r["longitude"],
                            "zone": f"{r.get('admin1', 'Indian')} Eco-Region"
                        })
                if geo_results:
                    return {"total": len(geo_results), "districts": geo_results}
    except Exception:
        pass

    return {"total": 0, "districts": []}

@app.get("/api/v1/fires")
@app.get("/api/v1/fires/active")
async def get_active_satellite_fires(format: str = Query("geojson", enum=["geojson", "list"])):
    fires = await fetch_active_fires()
    if format == "geojson":
        return fires_to_geojson(fires)
    return {"total": len(fires), "fires": fires}

@app.get("/api/v1/search")
async def search_city_or_district(
    query: Optional[str] = Query(None, description="City or district name (e.g. Bhusawal, Nainital, Delhi, Pune, Leh)"),
    lat: Optional[float] = Query(None, ge=-90.0, le=90.0, description="Latitude in decimal degrees (-90 to 90)"),
    lon: Optional[float] = Query(None, ge=-180.0, le=180.0, description="Longitude in decimal degrees (-180 to 180)")
):
    target_name = "Custom Coordinates"
    target_state = "India"
    target_lat = lat
    target_lon = lon
    target_zone = "Unknown"
    matched = None

    if query:
        matched = find_best_district_match(query)
        if matched:
            target_name = matched["name"]
            target_state = matched["state"]
            target_lat = matched["lat"]
            target_lon = matched["lon"]
            target_zone = matched.get("zone", "Indian Plateau")
        elif lat is None or lon is None:
            import httpx
            clean_term = re.sub(r'[/()]', ' ', query).strip()
            encoded_term = urllib.parse.quote(clean_term)
            geo_url = f"https://geocoding-api.open-meteo.com/v1/search?name={encoded_term}&count=10&language=en&format=json"
            try:
                async with httpx.AsyncClient(timeout=8.0) as client:
                    resp = await client.get(geo_url)
                    if resp.status_code == 200 and resp.json().get("results"):
                        candidates = resp.json()["results"]
                        # Prioritize Indian geographic matches
                        selected = next((c for c in candidates if c.get("country_code") == "IN"), candidates[0])
                        import unicodedata
                        raw_name = selected["name"]
                        clean_name = unicodedata.normalize('NFKD', raw_name).encode('ASCII', 'ignore').decode('utf-8') or raw_name
                        target_name = clean_name
                        target_state = selected.get("admin1", "India")
                        target_lat = selected["latitude"]
                        target_lon = selected["longitude"]
                        target_zone = f"{selected.get('admin1', 'Indian')} Eco-Region"
            except Exception:
                pass

    if target_lat is None or target_lon is None:
        if DISTRICTS_DB:
            default_dist = DISTRICTS_DB[0]
            target_name = default_dist["name"]
            target_state = default_dist["state"]
            target_lat = default_dist["lat"]
            target_lon = default_dist["lon"]
            target_zone = default_dist.get("zone", "Indian Plateau")
        else:
            target_name = "Default Region"
            target_state = "India"
            target_lat = 20.5937
            target_lon = 78.9629
            target_zone = "National Plateau"

    weather = await fetch_live_weather(target_lat, target_lon)
    aqi_data = await fetch_live_and_forecast_aqi(target_lat, target_lon)
    all_fires = await fetch_active_fires()

    nearby_fires = find_nearby_fires(all_fires, target_lat, target_lon, radius_km=50.0)
    closest_km = nearby_fires[0]["distance_km"] if nearby_fires else 999.0

    fire_risk = calculate_fire_risk(
        temp=weather["temperature"],
        rh=weather["humidity"],
        wind=weather["wind_speed"],
        rain=weather["precipitation"]
    )

    preparedness = generate_preparedness_advisory(
        risk_level=fire_risk["risk_level"],
        fwi_score=fire_risk["fwi_score"],
        aqi_val=aqi_data["cpcb_aqi"],
        aqi_category=aqi_data["category"],
        nearby_fires_count=len(nearby_fires),
        closest_fire_km=closest_km
    )

    asyncio.create_task(
        log_telemetry(
            district_name=target_name,
            state=target_state,
            lat=target_lat,
            lon=target_lon,
            eco_zone=target_zone,
            fwi_score=fire_risk["fwi_score"],
            risk_level=fire_risk["risk_level"],
            cpcb_aqi=aqi_data["cpcb_aqi"],
            aqi_category=aqi_data["category"],
            nearby_fires_50km=len(nearby_fires),
            closest_fire_km=closest_km if nearby_fires else None,
            temperature=weather["temperature"],
            humidity=weather["humidity"],
            wind_speed=weather["wind_speed"],
            district_id=matched["id"] if matched else None
        )
    )

    return {
        "location": {
            "name": target_name,
            "state": target_state,
            "latitude": target_lat,
            "longitude": target_lon,
            "eco_zone": target_zone
        },
        "weather": weather,
        "wildfire_assessment": {
            "fwi_score": fire_risk["fwi_score"],
            "risk_level": fire_risk["risk_level"],
            "color": fire_risk["color"],
            "badge": fire_risk["badge"],
            "ffmc": fire_risk["ffmc"],
            "isi": fire_risk["isi"],
            "key_drivers": fire_risk["key_drivers"],
            "nearby_satellite_fires_50km": len(nearby_fires),
            "closest_active_fire_km": closest_km if nearby_fires else None,
            "active_hotspots": nearby_fires[:5]
        },
        "air_quality": aqi_data,
        "community_preparedness": preparedness,
        "metadata": {
            "standards": ["Canadian Forest Fire Weather Index (FWI)", "NASA LANCE FIRMS VIIRS 375m", "Copernicus CAMS", "CPCB National AQI"],
            "database_sync": "Supabase PostgreSQL",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    }

@app.get("/api/v1/telemetry/recent")
async def get_recent_telemetry(limit: int = Query(10, ge=1, le=50)):
    return {"total": limit, "logs": await get_recent_telemetry_logs(limit=limit)}

@app.get("/api/v1/preparedness")
def get_preparedness(risk_level: str = "Moderate", aqi: int = 120):
    category = "Moderate"
    if aqi <= 50:
        category = "Good"
    elif aqi <= 100:
        category = "Satisfactory"
    elif aqi <= 200:
        category = "Moderate"
    elif aqi <= 300:
        category = "Poor"
    elif aqi <= 400:
        category = "Very Poor"
    else:
        category = "Severe"

    return generate_preparedness_advisory(
        risk_level=risk_level,
        fwi_score=15.0,
        aqi_val=aqi,
        aqi_category=category,
        nearby_fires_count=0
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
