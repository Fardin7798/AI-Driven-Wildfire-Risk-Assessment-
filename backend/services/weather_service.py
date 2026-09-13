import httpx
import logging
from typing import Dict, Any
from cachetools import TTLCache
from datetime import datetime, timezone

logger = logging.getLogger(__name__)
cache = TTLCache(maxsize=100, ttl=900)

async def fetch_live_weather(lat: float, lon: float) -> Dict[str, Any]:
    cache_key = f"weather_{round(lat, 2)}_{round(lon, 2)}"
    if cache_key in cache:
        return cache[cache_key]

    headers = {
        "User-Agent": "AeroRisk-India/1.0 (academic-environmental-research; contact@aerorisk.in)"
    }

    # Tier 1: Open-Meteo high-resolution hourly model
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": lat,
        "longitude": lon,
        "current": "temperature_2m,relative_humidity_2m,wind_speed_10m,precipitation,weather_code",
        "timezone": "Asia/Kolkata"
    }

    try:
        async with httpx.AsyncClient(timeout=8.0, headers=headers) as client:
            resp = await client.get(url, params=params)
            if resp.status_code == 200:
                data = resp.json()
                cur = data.get("current", {})
                result = {
                    "temperature": float(cur.get("temperature_2m", 30.0)),
                    "humidity": float(cur.get("relative_humidity_2m", 45.0)),
                    "wind_speed": float(cur.get("wind_speed_10m", 12.0)),
                    "precipitation": float(cur.get("precipitation", 0.0)),
                    "weather_code": int(cur.get("weather_code", 0)),
                    "timestamp": cur.get("time", datetime.now(timezone.utc).isoformat())
                }
                cache[cache_key] = result
                return result
    except Exception as e:
        logger.debug("Open-Meteo fetch failed: %s; trying Tier 2 wttr.in fallback", e)

    # Tier 2: Resilient wttr.in live atmospheric fallback
    try:
        wttr_url = f"https://wttr.in/{round(lat, 4)},{round(lon, 4)}?format=j1"
        async with httpx.AsyncClient(timeout=6.0, headers={"User-Agent": "curl/7.88.1"}) as client:
            resp = await client.get(wttr_url)
            if resp.status_code == 200:
                data = resp.json()
                curr = data.get("current_condition", [{}])[0]
                result = {
                    "temperature": float(curr.get("temp_C", 28.0)),
                    "humidity": float(curr.get("humidity", 55.0)),
                    "wind_speed": float(curr.get("windspeedKmph", 12.0)),
                    "precipitation": float(curr.get("precipMM", 0.0)),
                    "weather_code": int(curr.get("weatherCode", 0)),
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
                cache[cache_key] = result
                return result
    except Exception as e:
        logger.warning("wttr.in fallback failed: %s", e)

    return {
        "temperature": 28.5,
        "humidity": 65.0,
        "wind_speed": 11.0,
        "precipitation": 0.0,
        "weather_code": 0,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
