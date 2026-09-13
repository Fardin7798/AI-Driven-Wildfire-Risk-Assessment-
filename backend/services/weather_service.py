import httpx
from typing import Dict, Any
from cachetools import TTLCache

cache = TTLCache(maxsize=100, ttl=900)

async def fetch_live_weather(lat: float, lon: float) -> Dict[str, Any]:
    cache_key = f"weather_{round(lat, 2)}_{round(lon, 2)}"
    if cache_key in cache:
        return cache[cache_key]

    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": lat,
        "longitude": lon,
        "current": "temperature_2m,relative_humidity_2m,wind_speed_10m,precipitation,weather_code",
        "timezone": "Asia/Kolkata"
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
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
                    "timestamp": cur.get("time", "")
                }
                cache[cache_key] = result
                return result
    except Exception:
        pass

    fallback = {
        "temperature": 32.5,
        "humidity": 38.0,
        "wind_speed": 14.0,
        "precipitation": 0.0,
        "weather_code": 0,
        "timestamp": "fallback"
    }
    return fallback
