"""Daily AQI forecast job: model B (no-station boosters) for every district.

Origin t = yesterday (IST); h1..h3 = t+1..t+3. Inputs for 50 district centroids are
fetched per Open-Meteo request (`fetch_inputs_batch`); each district is then forecast by
`app.ml.aqi_station_b.forecast_district`. If a batch request fails (not quota), its districts
fall back to one request pair each.
A district without complete inputs gets a row in wf.aqi_forecast_skips with the reason; no
value is imputed. An Open-Meteo hourly/daily quota error stops the job (rows already written
are committed) and is raised so the run is recorded as failed.
"""

import time
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
from app.ml.aqi_station_b import fetch_inputs_batch, forecast_district, origin_day
from app.ml.loader import AqiStationModel, model_loader
from app.providers.open_meteo_http import OpenMeteoQuotaExceeded

SOURCE = "model_b_no_station"
COMMIT_EVERY = 50  # districts per batch request and per transaction (a quota stop keeps them)


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
    started = time.monotonic()
    async with async_session_factory() as session:
        regions = await _regions(session)
        try:
            for start in range(0, len(regions), COMMIT_EVERY):
                chunk = regions[start : start + COMMIT_EVERY]
                located = [(r, la, lo) for r, la, lo in chunk if la is not None and lo is not None]
                batch: dict[int, tuple[dict[str, list[Any]], dict[str, list[Any]]]] = {}
                try:
                    fetched = await fetch_inputs_batch(
                        [(float(la), float(lo)) for _, la, lo in located], origin
                    )
                    batch = {r: inp for (r, _, _), inp in zip(located, fetched, strict=True)}
                except OpenMeteoQuotaExceeded:
                    raise
                except Exception as e:  # fall back to one request pair per district
                    logger.warn("forecast_aqi_batch_fetch_failed", start=start, error=str(e)[:200])
                for region_id, lat, lon in chunk:
                    if lat is None or lon is None:
                        result: dict[str, Any] = {
                            "status": "skipped",
                            "reason": "region has no centroid",
                        }
                    else:
                        result = await forecast_district(
                            region_id,
                            float(lat),
                            float(lon),
                            model=model,
                            origin=origin,
                            inputs=batch.get(region_id),
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
                await session.commit()
                logger.info(
                    "forecast_aqi_progress",
                    done=start + len(chunk),
                    regions=len(regions),
                    seconds=round(time.monotonic() - started, 1),
                )
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
