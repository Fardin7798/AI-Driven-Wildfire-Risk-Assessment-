import os
import math
import csv
import io
import logging
import httpx
from typing import List, Dict, Any, Optional
from cachetools import TTLCache

logger = logging.getLogger("firms_service")
cache = TTLCache(maxsize=10, ttl=900)

# Geodetic bounding box for the Republic of India
INDIA_MIN_LAT = 8.0
INDIA_MAX_LAT = 37.0
INDIA_MIN_LON = 68.0
INDIA_MAX_LON = 97.0
INDIA_BBOX = f"{int(INDIA_MIN_LON)},{int(INDIA_MIN_LAT)},{int(INDIA_MAX_LON)},{int(INDIA_MAX_LAT)}"

PUBLIC_VIIRS_SOUTH_ASIA_URL = "https://firms.modaps.eosdis.nasa.gov/data/active_fire/suomi-npp-viirs-c2/csv/SUOMI_VIIRS_C2_South_Asia_24h.csv"

def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2.0) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2.0) ** 2
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return R * c

async def fetch_active_fires(map_key: Optional[str] = None) -> List[Dict[str, Any]]:
    cache_key = "nasa_firms_india_fires"
    if cache_key in cache:
        return cache[cache_key]

    key = map_key or os.environ.get("NASA_FIRMS_MAP_KEY")
    fires: List[Dict[str, Any]] = []

    # 1. Primary path: Authenticated NASA FIRMS Area API if map_key provided
    if key:
        url = f"https://firms.modaps.eosdis.nasa.gov/api/area/csv/{key}/VIIRS_SNPP_NRT/{INDIA_BBOX}/1"
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.get(url)
                if resp.status_code == 200 and "latitude" in resp.text:
                    reader = csv.DictReader(io.StringIO(resp.text))
                    for row in reader:
                        try:
                            fires.append({
                                "lat": float(row["latitude"]),
                                "lon": float(row["longitude"]),
                                "brightness": float(row.get("bright_ti4", 300.0)),
                                "frp": float(row.get("frp", 0.0)),
                                "confidence": row.get("confidence", "nominal"),
                                "acq_date": row.get("acq_date", ""),
                                "acq_time": row.get("acq_time", ""),
                                "daynight": row.get("daynight", "D")
                            })
                        except (ValueError, KeyError):
                            continue
        except Exception as e:
            logger.warning("NASA FIRMS key-based query failed: %s", e)

    # 2. Secondary path: Live public NASA Suomi-NPP VIIRS South Asia feed (100% real active fires, no key required)
    if not fires:
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.get(PUBLIC_VIIRS_SOUTH_ASIA_URL)
                if resp.status_code == 200 and "latitude" in resp.text:
                    reader = csv.DictReader(io.StringIO(resp.text))
                    for row in reader:
                        try:
                            lat = float(row["latitude"])
                            lon = float(row["longitude"])
                            if INDIA_MIN_LAT <= lat <= INDIA_MAX_LAT and INDIA_MIN_LON <= lon <= INDIA_MAX_LON:
                                fires.append({
                                    "lat": lat,
                                    "lon": lon,
                                    "brightness": float(row.get("bright_ti4", 300.0)),
                                    "frp": float(row.get("frp", 0.0)),
                                    "confidence": row.get("confidence", "nominal"),
                                    "acq_date": row.get("acq_date", ""),
                                    "acq_time": row.get("acq_time", ""),
                                    "daynight": row.get("daynight", "D")
                                })
                        except (ValueError, KeyError):
                            continue
        except Exception as e:
            logger.warning("NASA FIRMS public feed stream failed: %s", e)

    cache[cache_key] = fires
    return fires

def find_nearby_fires(fires: List[Dict[str, Any]], lat: float, lon: float, radius_km: float = 50.0) -> List[Dict[str, Any]]:
    nearby = []
    for f in fires:
        dist = haversine_km(lat, lon, f["lat"], f["lon"])
        if dist <= radius_km:
            item = dict(f)
            item["distance_km"] = round(dist, 1)
            nearby.append(item)
    nearby.sort(key=lambda x: x["distance_km"])
    return nearby

def fires_to_geojson(fires: List[Dict[str, Any]]) -> Dict[str, Any]:
    features = []
    for f in fires:
        features.append({
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [f["lon"], f["lat"]]
            },
            "properties": {
                "brightness": f.get("brightness"),
                "frp": f.get("frp"),
                "confidence": f.get("confidence"),
                "acq_date": f.get("acq_date"),
                "acq_time": f.get("acq_time")
            }
        })
    return {
        "type": "FeatureCollection",
        "features": features
    }
