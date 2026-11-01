from datetime import timedelta

from sqlalchemy import func, select

from app.core.logging import logger
from app.core.timeutil import today_ist
from app.db.models.fire import FireDetection
from app.db.models.region import Region
from app.db.models.weather import FWIState, WeatherDaily
from app.db.session import async_session_factory
from app.domain.features import ROLLING_WINDOW_DAYS, DailyWeatherRecord, extract_features
from app.jobs.scheduler import tracked_job
from app.ml.loader import model_loader
from app.ml.wildfire_predictor import predict_wildfire_risk
from app.services.risk_service import save_risk_prediction

# Live fire-history features must count the same sensor the model was trained on.
DEFAULT_FIRE_FEATURE_SOURCE = "VIIRS_NOAA20_NRT"


def _to_record(r: WeatherDaily) -> DailyWeatherRecord | None:
    """Convert a DB row; rows missing a core variable are dropped, never filled."""
    core = (r.temp_max, r.temp_mean, r.rh_mean, r.wind_max, r.precip_sum)
    if any(v is None for v in core):
        return None
    return DailyWeatherRecord(
        record_date=r.date,
        temp_max=r.temp_max,  # type: ignore[arg-type]
        temp_mean=r.temp_mean,  # type: ignore[arg-type]
        rh_min=r.rh_min,
        rh_mean=r.rh_mean,  # type: ignore[arg-type]
        wind_max=r.wind_max,  # type: ignore[arg-type]
        precip_sum=r.precip_sum,  # type: ignore[arg-type]
        et0=r.et0,
        soil_moisture=r.soil_moisture,
    )


@tracked_job("predict_risk")
async def job_predict_risk() -> int:
    today = today_ist()
    cutoff_window = today - timedelta(days=ROLLING_WINDOW_DAYS - 1)
    cutoff_30d = today - timedelta(days=30)
    cutoff_7d = today - timedelta(days=7)
    predicted = skipped = fallbacks = 0

    artifact = model_loader.load_wildfire_model()
    meta = artifact.metadata if artifact else {}
    fire_source = meta.get("fire_feature_source", DEFAULT_FIRE_FEATURE_SOURCE)
    climatology: dict[str, list[float]] = meta.get("climatology", {}).get("monthly_rate", {})

    async with async_session_factory() as session:
        regions = (await session.execute(select(Region))).scalars().all()
        if not regions:
            raise RuntimeError("No regions loaded")

        w_rows = (
            (
                await session.execute(
                    select(WeatherDaily)
                    .where(WeatherDaily.date >= cutoff_window, WeatherDaily.date <= today)
                    .order_by(WeatherDaily.region_id, WeatherDaily.date.asc())
                )
            )
            .scalars()
            .all()
        )
        weather_map: dict[int, dict] = {}
        for r in w_rows:
            rec = _to_record(r)
            if rec is None:
                continue
            per_day = weather_map.setdefault(r.region_id, {})
            if r.date not in per_day or not r.is_forecast:
                per_day[r.date] = rec

        fwi_rows = (
            (await session.execute(select(FWIState).where(FWIState.date == today))).scalars().all()
        )
        fwi_map = {row.region_id: row for row in fwi_rows}

        not_low = func.lower(func.left(func.coalesce(FireDetection.confidence, ""), 1)) != "l"

        async def fire_counts(since) -> dict[int, int]:
            q = (
                select(FireDetection.region_id, func.count(FireDetection.id))
                .where(
                    FireDetection.region_id.isnot(None),
                    FireDetection.source == fire_source,
                    not_low,
                    FireDetection.acq_datetime_utc >= since,
                    FireDetection.acq_datetime_utc < today,
                )
                .group_by(FireDetection.region_id)
            )
            return {
                int(rid): int(n) for rid, n in (await session.execute(q)).all() if rid is not None
            }

        fires_7d_map = await fire_counts(cutoff_7d)
        fires_30d_map = await fire_counts(cutoff_30d)

        for reg in regions:
            per_day = weather_map.get(reg.id, {})
            today_weather = per_day.get(today)
            fwi_row = fwi_map.get(reg.id)
            if (
                today_weather is None
                or fwi_row is None
                or reg.centroid_lat is None
                or reg.centroid_lon is None
            ):
                skipped += 1
                continue

            clim = climatology.get(reg.gadm_id or "")
            features = extract_features(
                target_date=today,
                current_weather=today_weather,
                weather_history=[per_day[d] for d in sorted(per_day)],
                fwi_values={
                    "ffmc": fwi_row.ffmc,
                    "dmc": fwi_row.dmc,
                    "dc": fwi_row.dc,
                    "isi": fwi_row.isi,
                    "bui": fwi_row.bui,
                    "fwi": fwi_row.fwi,
                },
                lat=reg.centroid_lat,
                lon=reg.centroid_lon,
                landcover=reg.landcover or {},
                fires_prev_7d=fires_7d_map.get(reg.id, 0),
                fires_prev_30d=fires_30d_map.get(reg.id, 0),
                climatological_fire_freq=clim[today.month - 1] if clim else float("nan"),
            )

            pred = predict_wildfire_risk(features)
            if pred is None:
                skipped += 1
                continue
            fallbacks += int(pred.is_fallback)
            await save_risk_prediction(
                session=session,
                region_id=reg.id,
                pred_date=today,
                probability=pred.probability,
                risk_class=pred.risk_class,
                model_version=pred.model_version,
                fwi_value=pred.fwi_value,
                top_factors=pred.top_factors,
            )
            predicted += 1

        await session.commit()

    logger.info(
        "predict_risk_summary", predicted=predicted, skipped=skipped, fwi_fallbacks=fallbacks
    )
    if predicted == 0:
        raise RuntimeError(f"No risk predictions written ({skipped} regions lacked weather/FWI)")
    return predicted
