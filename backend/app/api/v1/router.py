from fastapi import APIRouter

from app.api.v1.air_quality import router as air_quality_router
from app.api.v1.fires import router as fires_router
from app.api.v1.geo import router as geo_router
from app.api.v1.health import router as health_router
from app.api.v1.internal_jobs import router as internal_jobs_router
from app.api.v1.meta import router as meta_router
from app.api.v1.models_info import router as models_info_router
from app.api.v1.preparedness import router as preparedness_router
from app.api.v1.regions import router as regions_router
from app.api.v1.risk import router as risk_router
from app.api.v1.weather import router as weather_router

api_v1_router = APIRouter()

api_v1_router.include_router(health_router)
api_v1_router.include_router(regions_router)
api_v1_router.include_router(risk_router)
api_v1_router.include_router(fires_router)
api_v1_router.include_router(geo_router)
api_v1_router.include_router(air_quality_router)
api_v1_router.include_router(weather_router)
api_v1_router.include_router(models_info_router)
api_v1_router.include_router(preparedness_router)
api_v1_router.include_router(meta_router)
api_v1_router.include_router(internal_jobs_router)

__all__ = ["api_v1_router"]
