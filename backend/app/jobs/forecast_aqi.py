"""Daily AQI forecast job: model B (no-station boosters) for every district.

Origin t = yesterday (IST); h1..h3 = t+1..t+3. Each district is forecast by
`app.ml.aqi_station_b.forecast_district` from live Open-Meteo inputs at its centroid.
A district without complete inputs gets a row in wf.aqi_forecast_skips with the reason; no
value is imputed. An Open-Meteo hourly/daily quota error stops the job (rows already written
are committed) and is raised so the run is recorded as failed.
"""

from datetime import date
from typing import Any

from sqlalchemy import delete, func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import logger
from app.db.models.air_quality import AQIForecastB, AQIForecastSkip
from app.db.models.region import Region
from app.db.session import async_session_factory
from app.jobs.scheduler import tracked_job
from app.ml.aqi_station_b import forecast_district, origin_day
from app.ml.loader import AqiStationModel, model_loader

SOURCE = "model_b_no_station"
COMMIT_EVERY = 50  # districts per transaction, so a quota stop keeps finished work


async def _regions(session: AsyncSession) -> list[tuple[int, float | None, float | None]]:
    rows = await session.execute(
        select(Region.id, func.ST_Y(Region.centroid), func.ST_X(Region.centroid)).order_by(
            Region.id
        )
    )
    return [(int(r[0]), r[1], r[2]) for r in rows.all()]


async def _write_forecasts(session: AsyncSession, result: dict[str, Any]) -> int:
    origin = date.fromisoformat(result["origin_date"])
    for f in result["forecasts"]:
        stmt = insert(AQIForecastB).values(
            region_id=result["region_id"],
            origin_date=origin,
            target_date=date.fromisoformat(f["target_date"]),
            horizon=f["horizon_days"],
            pm25_si_pred=f["pm25_si_pred"],
            category=f["aqi_category"],
            model_version=f["model_version"],
            source=SOURCE,
            extrapolated=f["extrapolated"],
        )
        await session.execute(
            stmt.on_conflict_do_update(
                constraint="uq_aqi_forecasts_b_region_origin_horizon_version",
                set_={
                    "target_date": stmt.excluded.target_date,
                    "pm25_si_pred": stmt.excluded.pm25_si_pred,
                    "category": stmt.excluded.category,
                    "source": stmt.excluded.source,
                    "extrapolated": stmt.excluded.extrapolated,
                    "created_at": func.now(),
                },
            )
        )
    # A forecast now exists for this key, so an earlier skip no longer applies.
    await session.execute(
        delete(AQIForecastSkip).where(
            AQIForecastSkip.region_id == result["region_id"],
            AQIForecastSkip.origin_date == origin,
            AQIForecastSkip.model_version == result["model_version"],
        )
    )
    return len(result["forecasts"])


async def _write_skip(
    session: AsyncSession, region_id: int, origin: date, model_version: str, reason: str
) -> bool:
    """Record a skip unless a forecast from complete inputs already exists for this key (a
    re-run whose inputs failed does not invalidate it). Returns True when recorded."""
    existing = await session.execute(
        select(AQIForecastB.id)
        .where(
            AQIForecastB.region_id == region_id,
            AQIForecastB.origin_date == origin,
            AQIForecastB.model_version == model_version,
        )
        .limit(1)
    )
    if existing.first() is not None:
        return False
    stmt = insert(AQIForecastSkip).values(
        region_id=region_id, origin_date=origin, model_version=model_version, reason=reason
    )
    await session.execute(
        stmt.on_conflict_do_update(
            constraint="uq_aqi_forecast_skips_region_origin_version",
            set_={"reason": stmt.excluded.reason, "created_at": func.now()},
        )
    )
    return True


async def run_forecast_aqi(model: AqiStationModel, origin: date) -> dict[str, int]:
    written = forecast_regions = skipped = kept = 0
    async with async_session_factory() as session:
        regions = await _regions(session)
        try:
            for i, (region_id, lat, lon) in enumerate(regions, start=1):
                if lat is None or lon is None:
                    result: dict[str, Any] = {
                        "status": "skipped",
                        "reason": "region has no centroid",
                    }
                else:
                    result = await forecast_district(
                        region_id, float(lat), float(lon), model=model, origin=origin
                    )
                if result["status"] == "ok":
                    written += await _write_forecasts(session, result)
                    forecast_regions += 1
                elif await _write_skip(
                    session, region_id, origin, model.model_version, result["reason"]
                ):
                    skipped += 1
                else:
                    kept += 1
                if i % COMMIT_EVERY == 0:
                    await session.commit()
        finally:
            # Also on a quota stop: keep the districts finished so far.
            await session.commit()
            logger.info(
                "forecast_aqi_summary",
                origin=origin.isoformat(),
                model_version=model.model_version,
                regions=len(regions),
                forecast_regions=forecast_regions,
                rows_written=written,
                skipped=skipped,
                skipped_kept_previous_forecast=kept,
            )
    return {
        "regions": len(regions),
        "forecast_regions": forecast_regions,
        "rows_written": written,
        "skipped": skipped,
        "skipped_kept_previous_forecast": kept,
    }


@tracked_job("forecast_aqi")
async def job_forecast_aqi() -> int:
    model = model_loader.load_aqi_model()
    if model is None:
        raise RuntimeError("AQI model B not loaded; no forecasts written")
    stats = await run_forecast_aqi(model, origin_day())
    return stats["rows_written"]
