from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.timeutil import today_ist
from app.db.models.air_quality import AQForecast, AQObservation
from app.db.models.region import Region
from app.providers.base import RawAQObservation


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
            func.lower(Region.state_name) == state.lower().strip()
        )
    query = query.limit(limit)
    result = await session.execute(query)
    return list(result.scalars().all())


async def get_air_quality_for_region(session: AsyncSession, region_id: int) -> AQObservation | None:
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


async def get_air_quality_forecast(session: AsyncSession, region_id: int) -> list[AQForecast]:
    today = today_ist()
    query = (
        select(AQForecast)
        .options(selectinload(AQForecast.region))
        .where(AQForecast.region_id == region_id, AQForecast.target_date >= today)
        .order_by(AQForecast.target_date.asc())
    )
    result = await session.execute(query)
    return list(result.scalars().all())


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
