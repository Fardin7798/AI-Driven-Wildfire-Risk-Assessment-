from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.schemas.fires import FireDetectionResponse, FireStatsResponse
from app.services.fire_service import get_fire_stats, get_recent_fires

router = APIRouter(prefix="/fires", tags=["Fire Detections"])


@router.get("/recent", response_model=list[FireDetectionResponse])
async def list_recent_fires(
    hours: int = Query(default=24, ge=1, le=168),
    bbox: str | None = Query(
        default=None,
        description="Bounding box in format 'west,south,east,north'",
        pattern=r"^-?\d+(\.\d+)?,-?\d+(\.\d+)?,-?\d+(\.\d+)?,-?\d+(\.\d+)?$",
    ),
    limit: int = Query(default=1000, ge=1, le=5000),
    db: AsyncSession = Depends(get_db),
) -> list[FireDetectionResponse]:
    """Retrieve active satellite thermal anomalies (FIRMS VIIRS/MODIS) within time and spatial window."""
    parsed_bbox: tuple[float, float, float, float] | None = None
    if bbox:
        parts = [float(p.strip()) for p in bbox.split(",")]
        parsed_bbox = (parts[0], parts[1], parts[2], parts[3])

    records = await get_recent_fires(session=db, hours=hours, bbox=parsed_bbox, limit=limit)
    return [FireDetectionResponse.model_validate(r) for r in records]


@router.get("/stats", response_model=FireStatsResponse)
async def get_active_fire_statistics(
    days: int = Query(default=7, ge=1, le=30),
    db: AsyncSession = Depends(get_db),
) -> FireStatsResponse:
    """Retrieve aggregated thermal anomaly indicators (count, high confidence, total FRP)."""
    stats_dict = await get_fire_stats(session=db, days=days)
    return FireStatsResponse(
        period_days=stats_dict.get("period_days", days),
        total_detections=stats_dict.get("total_detections", 0),
        total_fires=stats_dict.get("total_detections", 0),
        high_confidence_count=stats_dict.get("high_confidence_count", 0),
        high_confidence_fires=stats_dict.get("high_confidence_count", 0),
        total_radiative_power_mw=stats_dict.get("total_radiative_power_mw", 0.0),
        by_source=stats_dict.get("by_source", {}),
        by_state=stats_dict.get("by_state", {}),
        outside_districts=stats_dict.get("outside_districts", 0),
        time_range_hours=days * 24,
    )
