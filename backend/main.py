import os
import json
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from services.fwi_engine import calculate_fire_risk
from services.firms_service import fetch_active_fires, find_nearby_fires, fires_to_geojson
from services.weather_service import fetch_live_weather
from services.aqi_service import fetch_live_and_forecast_aqi
from services.preparedness_service import generate_preparedness_advisory

load_dotenv()

app = FastAPI(
    title="AI-Driven Wildfire Risk Assessment & Air Quality Platform (India)",
    description="Production-grade API providing scientific Canadian FWI fire danger rating, NASA FIRMS VIIRS 375m active satellite fire correlation, Copernicus CAMS 72-hour AQI forecasts, and actionable community preparedness advisories across India.",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DATA_PATH = os.path.join(os.path.dirname(__file__), "data", "indian_districts.json")
try:
    with open(DATA_PATH, "r") as f:
        DISTRICTS_DB: List[Dict[str, Any]] = json.load(f)
except Exception:
    DISTRICTS_DB = []

@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "service": "Wildfire Risk & Air Quality Engine (India)",
        "version": "1.0.0",
        "districts_loaded": len(DISTRICTS_DB),
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

@app.get("/api/v1/districts")
def list_districts(search: Optional[str] = None):
    if not search:
        return {"total": len(DISTRICTS_DB), "districts": DISTRICTS_DB}
    q = search.lower().strip()
    filtered = [d for d in DISTRICTS_DB if q in d["name"].lower() or q in d["state"].lower()]
    return {"total": len(filtered), "districts": filtered}

@app.get("/api/v1/fires/active")
async def get_active_satellite_fires(format: str = Query("geojson", enum=["geojson", "list"])):
    fires = await fetch_active_fires()
    if format == "geojson":
        return fires_to_geojson(fires)
    return {"total": len(fires), "fires": fires}

@app.get("/api/v1/search")
async def search_city_or_district(
    query: Optional[str] = Query(None, description="City or district name (e.g. Bhusawal, Nainital, Delhi, Pune)"),
    lat: Optional[float] = Query(None, description="Latitude (optional override)"),
    lon: Optional[float] = Query(None, description="Longitude (optional override)")
):
    target_name = "Custom Coordinates"
    target_state = "India"
    target_lat = lat
    target_lon = lon
    target_zone = "Unknown"

    if query:
        q_clean = query.lower().strip()
        matched = None
        for d in DISTRICTS_DB:
            if q_clean in d["name"].lower() or q_clean in d["id"].lower() or d["name"].lower() in q_clean:
                matched = d
                break
        if matched:
            target_name = matched["name"]
            target_state = matched["state"]
            target_lat = matched["lat"]
            target_lon = matched["lon"]
            target_zone = matched.get("zone", "Indian Plateau")
        elif lat is None or lon is None:
            import httpx
            geo_url = f"https://geocoding-api.open-meteo.com/v1/search?name={query}&count=1&language=en&format=json"
            try:
                async with httpx.AsyncClient(timeout=8.0) as client:
                    resp = await client.get(geo_url)
                    if resp.status_code == 200 and resp.json().get("results"):
                        top = resp.json()["results"][0]
                        target_name = top["name"]
                        target_state = top.get("admin1", "India")
                        target_lat = top["latitude"]
                        target_lon = top["longitude"]
                        target_zone = "Geocoded Region"
            except Exception:
                pass

    if target_lat is None or target_lon is None:
        target_name = "Jalgaon / Bhusawal"
        target_state = "Maharashtra"
        target_lat = 21.0450
        target_lon = 75.7873
        target_zone = "Deccan Plateau"

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
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    }

@app.get("/api/v1/preparedness")
def get_preparedness(risk_level: str = "Moderate", aqi: int = 120):
    return generate_preparedness_advisory(
        risk_level=risk_level,
        fwi_score=15.0,
        aqi_val=aqi,
        aqi_category="Moderate",
        nearby_fires_count=0
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
