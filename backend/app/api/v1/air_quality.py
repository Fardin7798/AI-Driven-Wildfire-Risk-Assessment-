from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.db.models.air_quality import AQForecast, AQObservation
from app.schemas.air_quality import AQForecastResponse, AQObservationResponse
from app.schemas.common import SHORT_DISCLAIMER, get_as_of
from app.services.air_quality_service import (
    get_air_quality_for_region,
    get_air_quality_forecast,
    get_latest_air_quality,
)

router = APIRouter(prefix="/air-quality", tags=["Air Quality"])


def _serialize_aq(obs: AQObservation) -> AQObservationResponse:
    try:
        district_name = obs.region.district_name if getattr(obs, "region", None) else None
        state_name = obs.region.state_name if getattr(obs, "region", None) else None
    except Exception:
        district_name = None
        state_name = None

    return AQObservationResponse(
        region_id=obs.region_id,
        district_name=district_name,
        state_name=state_name,
        observed_at_utc=obs.observed_at_utc,
        pm25=obs.pm25,
        pm10=obs.pm10,
        no2=obs.no2,
        so2=obs.so2,
        co=obs.co,
        o3=obs.o3,
        nh3=obs.nh3,
        aqi=obs.aqi,
        aqi_category=obs.aqi_category,
        provider=obs.provider,
        as_of=get_as_of(),
        disclaimer_short=SHORT_DISCLAIMER,
    )


def _serialize_forecast(fc: AQForecast) -> AQForecastResponse:
    try:
        district_name = fc.region.district_name if getattr(fc, "region", None) else None
    except Exception:
        district_name = None
    return AQForecastResponse(
        region_id=fc.region_id,
        district_name=district_name,
        target_date=fc.target_date,
        horizon_days=fc.horizon_days,
        pm25_pred=float(fc.pm25_pred or 0.0),
        aqi_pred=int(fc.aqi_pred or 0),
        aqi_category=str(fc.aqi_category or "Moderate"),
        model_version=fc.model_version,
        as_of=get_as_of(),
        disclaimer_short=SHORT_DISCLAIMER,
    )


@router.get("/latest", response_model=list[AQObservationResponse])
async def list_latest_air_quality(
    state: str | None = Query(default=None, max_length=100),
    limit: int = Query(default=50, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
) -> list[AQObservationResponse]:
    """Retrieve the most recent real-time air quality observations across districts."""
    records = await get_latest_air_quality(session=db, state=state, limit=limit)
    return [_serialize_aq(r) for r in records]


@router.get("/{region_id}", response_model=AQObservationResponse)
async def get_region_air_quality(
    region_id: int,
    db: AsyncSession = Depends(get_db),
) -> AQObservationResponse:
    """Retrieve latest air quality snapshot for a specific district."""
    record = await get_air_quality_for_region(session=db, region_id=region_id)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No air quality observation found for region {region_id}.",
        )
    return _serialize_aq(record)


@router.get("/{region_id}/forecast", response_model=list[AQForecastResponse])
async def get_region_aq_forecast(
    region_id: int,
    db: AsyncSession = Depends(get_db),
) -> list[AQForecastResponse]:
    """Retrieve 1 to 3 day AQI trajectory forecasts for a district."""
    records = await get_air_quality_forecast(session=db, region_id=region_id)
    return [_serialize_forecast(r) for r in records]
