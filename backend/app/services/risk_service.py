import json
from datetime import date, timedelta
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.timeutil import today_ist
from app.db.models.region import Region
from app.db.models.risk import RiskPrediction
from app.domain.names import humanize_gadm_name, normalize_name_key


async def get_latest_risk(
    session: AsyncSession, state: str | None = None, limit: int = 50
) -> list[RiskPrediction]:
    query = (
        select(RiskPrediction)
        .join(Region, RiskPrediction.region_id == Region.id)
        .options(selectinload(RiskPrediction.region))
    )
    if state:
        query = query.where(
            func.regexp_replace(func.lower(Region.state_name), "[^a-z0-9]", "", "g")
            == normalize_name_key(state)
        )

    query = query.order_by(RiskPrediction.date.desc(), RiskPrediction.probability.desc()).limit(
        limit
    )
    result = await session.execute(query)
    return list(result.scalars().all())


async def get_risk_by_region(
    session: AsyncSession, region_id: int, target_date: date | None = None
) -> RiskPrediction | None:
    t_date = target_date or today_ist()
    query = (
        select(RiskPrediction)
        .options(selectinload(RiskPrediction.region))
        .where(RiskPrediction.region_id == region_id, RiskPrediction.date == t_date)
        .order_by(RiskPrediction.created_at.desc())
        .limit(1)
    )
    result = await session.execute(query)
    record = result.scalar_one_or_none()
    if not record:
        # Fallback to most recent record
        query_fallback = (
            select(RiskPrediction)
            .options(selectinload(RiskPrediction.region))
            .where(RiskPrediction.region_id == region_id)
            .order_by(RiskPrediction.date.desc())
            .limit(1)
        )
        record = (await session.execute(query_fallback)).scalar_one_or_none()
    return record


async def get_risk_history(
    session: AsyncSession, region_id: int, days: int = 30
) -> list[RiskPrediction]:
    start_date = today_ist() - timedelta(days=days)
    query = (
        select(RiskPrediction)
        .options(selectinload(RiskPrediction.region))
        .where(RiskPrediction.region_id == region_id, RiskPrediction.date >= start_date)
        .order_by(RiskPrediction.date.asc())
    )
    result = await session.execute(query)
    return list(result.scalars().all())


async def get_risk_map_geojson(
    session: AsyncSession, target_date: date | None = None, state: str | None = None
) -> dict[str, Any]:
    t_date = target_date or today_ist()

    # Latest prediction per region for the date (several model versions may exist for one day).
    latest = (
        select(RiskPrediction)
        .where(RiskPrediction.date == t_date)
        .distinct(RiskPrediction.region_id)
        .order_by(RiskPrediction.region_id, RiskPrediction.created_at.desc())
        .subquery()
    )
    query = select(
        Region.id,
        Region.district_name,
        Region.state_name,
        func.ST_AsGeoJSON(Region.centroid).label("centroid_geojson"),
        latest.c.risk_class,
        latest.c.probability,
        latest.c.fwi_value,
        latest.c.model_version,
    ).outerjoin(latest, latest.c.region_id == Region.id)
    if state:
        query = query.where(
            func.regexp_replace(func.lower(Region.state_name), "[^a-z0-9]", "", "g")
            == normalize_name_key(state)
        )

    rows = (await session.execute(query)).all()

    features: list[dict[str, Any]] = []
    for r in rows:
        geom = json.loads(r.centroid_geojson) if r.centroid_geojson else None
        has_pred = r.risk_class is not None
        features.append(
            {
                "type": "Feature",
                "geometry": geom,
                "properties": {
                    "region_id": r.id,
                    "district_name": humanize_gadm_name(r.district_name),
                    "state_name": humanize_gadm_name(r.state_name),
                    "date": t_date.isoformat(),
                    # No prediction for this district today -> say so; never a placeholder risk.
                    "risk_class": r.risk_class if has_pred else None,
                    "probability": float(r.probability) if has_pred else None,
                    "fwi_value": float(r.fwi_value) if r.fwi_value is not None else None,
                    "model_version": r.model_version if has_pred else None,
                    "has_prediction": has_pred,
                },
            }
        )

    return {
        "type": "FeatureCollection",
        "date": t_date.isoformat(),
        "total": len(features),
        "with_prediction": sum(1 for f in features if f["properties"]["has_prediction"]),
        "features": features,
    }


async def save_risk_prediction(
    session: AsyncSession,
    region_id: int,
    pred_date: date,
    probability: float,
    risk_class: str,
    model_version: str,
    fwi_value: float,
    top_factors: dict[str, Any],
) -> None:
    stmt = (
        insert(RiskPrediction)
        .values(
            region_id=region_id,
            date=pred_date,
            probability=probability,
            risk_class=risk_class,
            model_version=model_version,
            fwi_value=fwi_value,
            top_factors=top_factors,
        )
        .on_conflict_do_update(
            index_elements=["region_id", "date", "model_version"],
            set_={
                "probability": probability,
                "risk_class": risk_class,
                "fwi_value": fwi_value,
                "top_factors": top_factors,
            },
        )
    )
    await session.execute(stmt)
