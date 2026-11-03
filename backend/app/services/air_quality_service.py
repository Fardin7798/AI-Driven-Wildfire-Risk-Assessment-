from sqlalchemy import func, select, union_all
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models.air_quality import AQIForecastB, AQIForecastSkip, AQObservation
from app.db.models.region import Region
from app.domain.names import normalize_name_key
from app.providers.base import RawAQObservation
from app.schemas.air_quality import AQIForecastPoint, DistrictAQIForecast


async def get_latest_air_quality(
    session: AsyncSession, state: str | None = None, limit: int = 50
) -> list[AQObservation]:
    query = (
        select(AQObservation)
        .options(selectinload(AQObservation.region))
        .options(selectinload(AQObservation.region))
        .order_by(AQObservation.observed_at_utc.desc())
    )
    if state:
        query = query.join(Region, AQObservation.region_id == Region.id).where(
            func.regexp_replace(func.lower(Region.state_name), "[^a-z0-9]", "", "g")
            == normalize_name_key(state)
        )
    query = query.limit(limit)
    result = await session.execute(query)
    return list(result.scalars().all())


async def get_air_quality_for_region(session: AsyncSession, region_id: int) -> AQObservation | None:
    """Latest stored observation; without one, fetch the CPCB-averaged current CAMS value (24-h
    window ending at the latest whole UTC hour) on demand, store it and return it."""
    query = (
        select(AQObservation)
        .options(selectinload(AQObservation.region))
        .where(AQObservation.region_id == region_id)
        .order_by(AQObservation.observed_at_utc.desc())
        .limit(1)
    )
    result = await session.execute(query)
    record = result.scalar_one_or_none()
    if record:
        return record

    reg_query = select(Region).where(Region.id == region_id)
    reg_res = await session.execute(reg_query)
    region = reg_res.scalar_one_or_none()
    if region and region.centroid_lat and region.centroid_lon:
        try:
            from app.providers.open_meteo_air import OpenMeteoAirProvider

            provider = OpenMeteoAirProvider()
            raw_obs_list = await provider.fetch_air_quality(
                region.centroid_lat, region.centroid_lon
            )
            if raw_obs_list:
                await upsert_aq_observation(session, raw_obs_list[0], region_id=region.id)
                await session.commit()
                re_res = await session.execute(query)
                return re_res.scalar_one_or_none()
        except Exception:
            return None

    return None


async def get_latest_aqi_forecasts(
    session: AsyncSession, model_version: str, region_id: int | None = None
) -> list[DistrictAQIForecast]:
    """Model-B rows for each district's latest origin day of `model_version`.

    The job writes either forecasts (wf.aqi_forecasts_b) or a skip (wf.aqi_forecast_skips) per
    district and origin, never both, so the latest origin over both tables decides which one the
    district reports. Districts with neither are absent.
    """
    keys = union_all(
        select(AQIForecastB.region_id, AQIForecastB.origin_date).where(
            AQIForecastB.model_version == model_version
        ),
        select(AQIForecastSkip.region_id, AQIForecastSkip.origin_date).where(
            AQIForecastSkip.model_version == model_version
        ),
    ).subquery()
    latest_q = select(keys.c.region_id, func.max(keys.c.origin_date).label("origin_date")).group_by(
        keys.c.region_id
    )
    if region_id is not None:
        latest_q = latest_q.where(keys.c.region_id == region_id)
    latest = latest_q.subquery()

    fc_rows = await session.execute(
        select(AQIForecastB, Region.district_name, Region.state_name)
        .join(
            latest,
            (AQIForecastB.region_id == latest.c.region_id)
            & (AQIForecastB.origin_date == latest.c.origin_date),
        )
        .join(Region, Region.id == AQIForecastB.region_id)
        .where(AQIForecastB.model_version == model_version)
        .order_by(AQIForecastB.region_id, AQIForecastB.horizon)
    )
    out: dict[int, DistrictAQIForecast] = {}
    for fc, district, state in fc_rows.all():
        d = out.get(fc.region_id)
        if d is None:
            d = out[fc.region_id] = DistrictAQIForecast(
                region_id=fc.region_id,
                district_name=district,
                state_name=state,
                status="forecast",
                origin_date=fc.origin_date,
                model_version=fc.model_version,
                source=fc.source,
                extrapolated=fc.extrapolated,
            )
        # extrapolated is a per-district verdict; OR over horizons in case rows ever differ.
        d.extrapolated = bool(d.extrapolated or fc.extrapolated)
        d.forecasts.append(
            AQIForecastPoint(
                horizon=fc.horizon,
                target_date=fc.target_date,
                pm25_si_pred=fc.pm25_si_pred,
                category=fc.category,
            )
        )

    skip_rows = await session.execute(
        select(AQIForecastSkip, Region.district_name, Region.state_name)
        .join(
            latest,
            (AQIForecastSkip.region_id == latest.c.region_id)
            & (AQIForecastSkip.origin_date == latest.c.origin_date),
        )
        .join(Region, Region.id == AQIForecastSkip.region_id)
        .where(AQIForecastSkip.model_version == model_version)
    )
    for sk, district, state in skip_rows.all():
        if sk.region_id in out:
            continue
        out[sk.region_id] = DistrictAQIForecast(
            region_id=sk.region_id,
            district_name=district,
            state_name=state,
            status="skipped",
            origin_date=sk.origin_date,
            model_version=sk.model_version,
            skip_reason=sk.reason,
        )
    return [out[k] for k in sorted(out)]


async def upsert_aq_observation(
    session: AsyncSession,
    obs: RawAQObservation,
    region_id: int | None = None,
    station_id: int | None = None,
) -> None:
    stmt = (
        insert(AQObservation)
        .values(
            station_id=station_id,
            region_id=region_id,
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
        )
        .on_conflict_do_update(
            index_elements=["provider", "station_id", "region_id", "observed_at_utc"],
            set_={
                "pm25": obs.pm25,
                "pm10": obs.pm10,
                "no2": obs.no2,
                "so2": obs.so2,
                "co": obs.co,
                "o3": obs.o3,
                "nh3": obs.nh3,
                "aqi": obs.aqi,
                "aqi_category": obs.aqi_category,
            },
        )
    )
    await session.execute(stmt)
