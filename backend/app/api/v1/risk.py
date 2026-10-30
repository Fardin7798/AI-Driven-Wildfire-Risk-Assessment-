from datetime import date
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.db.models.risk import RiskPrediction
from app.schemas.common import SHORT_DISCLAIMER, get_as_of
from app.schemas.risk import RiskMapResponse, RiskPredictionResponse, TopFactor
from app.services.risk_service import (
    get_latest_risk,
    get_risk_by_region,
    get_risk_history,
    get_risk_map_geojson,
)

router = APIRouter(prefix="/risk", tags=["Wildfire Risk"])


def _serialize_risk(pred: RiskPrediction) -> RiskPredictionResponse:
    factors: list[TopFactor] = []
    if isinstance(pred.top_factors, dict):
        for k, v in pred.top_factors.items():
            try:
                factors.append(TopFactor(feature=str(k), impact=float(v)))
            except (ValueError, TypeError):
                continue
    elif isinstance(pred.top_factors, list):
        for item in pred.top_factors:
            if isinstance(item, dict) and "feature" in item and "impact" in item:
                factors.append(
                    TopFactor(feature=str(item["feature"]), impact=float(item["impact"]))
                )

    try:
        district_name = (
            pred.region.district_name
            if getattr(pred, "region", None)
            else f"District {pred.region_id}"
        )
        state_name = pred.region.state_name if getattr(pred, "region", None) else "India"
    except Exception:
        district_name = f"District {pred.region_id}"
        state_name = "India"

    return RiskPredictionResponse(
        region_id=pred.region_id,
        district_name=district_name,
        state_name=state_name,
        date=pred.date,
        probability=pred.probability,
        risk_class=pred.risk_class,
        model_version=pred.model_version,
        fwi_value=pred.fwi_value,
        top_factors=factors,
        as_of=get_as_of(),
        disclaimer_short=SHORT_DISCLAIMER,
    )


@router.get("/map", response_model=RiskMapResponse)
async def get_district_risk_map(
    target_date: date | None = Query(default=None, alias="date"),
    state: str | None = Query(default=None, max_length=100),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Retrieve GeoJSON map for district wildfire risk across India."""
    geojson_data = await get_risk_map_geojson(session=db, target_date=target_date, state=state)
    geojson_data["as_of"] = get_as_of()
    geojson_data["disclaimer_short"] = SHORT_DISCLAIMER
    return geojson_data


@router.get("/latest", response_model=list[RiskPredictionResponse])
async def get_latest_risk_predictions(
    state: str | None = Query(default=None, max_length=100),
    limit: int = Query(default=50, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
) -> list[RiskPredictionResponse]:
    """Get most recent wildfire risk predictions sorted by probability and date."""
    records = await get_latest_risk(session=db, state=state, limit=limit)
    return [_serialize_risk(r) for r in records]


@router.get("/{region_id}", response_model=RiskPredictionResponse)
async def get_region_risk(
    region_id: int,
    target_date: date | None = Query(default=None, alias="date"),
    db: AsyncSession = Depends(get_db),
) -> RiskPredictionResponse:
    """Get wildfire risk assessment for a specific district on a date."""
    record = await get_risk_by_region(session=db, region_id=region_id, target_date=target_date)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No risk prediction found for region {region_id}.",
        )
    return _serialize_risk(record)


@router.get("/{region_id}/history", response_model=list[RiskPredictionResponse])
async def get_region_risk_history(
    region_id: int,
    days: int = Query(default=14, ge=1, le=90),
    db: AsyncSession = Depends(get_db),
) -> list[RiskPredictionResponse]:
    """Get historical risk trajectory for a specific district."""
    records = await get_risk_history(session=db, region_id=region_id, days=days)
    return [_serialize_risk(r) for r in records]
