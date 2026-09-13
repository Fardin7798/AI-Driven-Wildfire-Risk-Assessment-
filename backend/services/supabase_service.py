import os
import logging
from typing import Dict, Any, List, Optional
import httpx
from dotenv import load_dotenv

# Ensure local .env files take precedence over stale global shell variables
_current_dir = os.path.dirname(os.path.abspath(__file__))
_backend_dir = os.path.dirname(_current_dir)
_root_dir = os.path.dirname(_backend_dir)

load_dotenv(os.path.join(_root_dir, ".env"), override=True)
load_dotenv(os.path.join(_backend_dir, ".env"), override=True)

logger = logging.getLogger("supabase_service")

# Dynamically resolve Supabase configuration from environment variables
SUPABASE_URL = os.getenv("WILDFIRE_SUPABASE_URL") or os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("WILDFIRE_SUPABASE_KEY") or os.getenv("SUPABASE_KEY") or os.getenv("SUPABASE_SERVICE_ROLE_KEY")

def get_project_ref() -> str:
    if SUPABASE_URL:
        try:
            return SUPABASE_URL.split("//")[1].split(".")[0]
        except Exception:
            pass
    return "unconfigured"

def get_headers() -> Dict[str, str]:
    if not SUPABASE_KEY:
        return {}
    return {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=minimal"
    }

async def log_telemetry(
    district_name: str,
    state: str,
    lat: float,
    lon: float,
    eco_zone: str,
    fwi_score: float,
    risk_level: str,
    cpcb_aqi: int,
    aqi_category: str,
    nearby_fires_50km: int,
    closest_fire_km: Optional[float],
    temperature: float,
    humidity: float,
    wind_speed: float,
    district_id: Optional[str] = None
) -> bool:
    if not SUPABASE_URL or not SUPABASE_KEY:
        logger.debug("Supabase not configured; skipping telemetry persistence")
        return False

    payload = {
        "district_id": district_id,
        "district_name": district_name,
        "state": state,
        "lat": lat,
        "lon": lon,
        "eco_zone": eco_zone,
        "fwi_score": fwi_score,
        "risk_level": risk_level,
        "cpcb_aqi": cpcb_aqi,
        "aqi_category": aqi_category,
        "nearby_fires_50km": nearby_fires_50km,
        "closest_fire_km": closest_fire_km if closest_fire_km and closest_fire_km < 900 else None,
        "temperature": temperature,
        "humidity": humidity,
        "wind_speed": wind_speed
    }

    try:
        async with httpx.AsyncClient(timeout=4.0) as client:
            resp = await client.post(
                f"{SUPABASE_URL}/rest/v1/telemetry_logs",
                headers=get_headers(),
                json=payload
            )
            return resp.status_code in (200, 201)
    except Exception as e:
        logger.warning("Supabase telemetry log failed gracefully: %s", e)
        return False

async def get_recent_telemetry_logs(limit: int = 10) -> List[Dict[str, Any]]:
    if not SUPABASE_URL or not SUPABASE_KEY:
        return []

    try:
        headers = {
            "apikey": SUPABASE_KEY,
            "Authorization": f"Bearer {SUPABASE_KEY}"
        }
        async with httpx.AsyncClient(timeout=4.0) as client:
            resp = await client.get(
                f"{SUPABASE_URL}/rest/v1/telemetry_logs?select=*&order=created_at.desc&limit={limit}",
                headers=headers
            )
            if resp.status_code == 200:
                return resp.json()
    except Exception as e:
        logger.warning("Failed to fetch recent telemetry logs: %s", e)
    return []

async def check_supabase_health() -> Dict[str, Any]:
    project_ref = get_project_ref()
    if not SUPABASE_URL or not SUPABASE_KEY:
        return {
            "status": "unconfigured",
            "provider": "Supabase PostgreSQL",
            "project_ref": project_ref,
            "regions_in_db": 0
        }

    try:
        headers = {
            "apikey": SUPABASE_KEY,
            "Authorization": f"Bearer {SUPABASE_KEY}"
        }
        async with httpx.AsyncClient(timeout=3.0) as client:
            resp = await client.get(
                f"{SUPABASE_URL}/rest/v1/regions?select=id",
                headers=headers
            )
            if resp.status_code == 200:
                rows = resp.json()
                return {
                    "status": "connected",
                    "provider": "Supabase PostgreSQL + PostGIS",
                    "project_ref": project_ref,
                    "regions_in_db": len(rows)
                }
    except Exception as e:
        logger.warning("Supabase health check failed: %s", e)
    return {"status": "degraded", "provider": "Supabase PostgreSQL", "project_ref": project_ref}
