from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.schemas.weather import WeatherDailyResponse
from app.services.weather_service import get_weather_for_region

router = APIRouter(prefix="/weather", tags=["Weather"])


@router.get("/{region_id}", response_model=list[WeatherDailyResponse])
async def get_district_weather(
    region_id: int,
    days: int = Query(default=7, ge=1, le=30),
    db: AsyncSession = Depends(get_db),
) -> list[WeatherDailyResponse]:
    """Retrieve historical and forecasted synoptic weather variables for a district."""
    records = await get_weather_for_region(session=db, region_id=region_id, days=days)
    if not records:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No weather records found for region {region_id}.",
        )
    return [WeatherDailyResponse.model_validate(r) for r in records]
