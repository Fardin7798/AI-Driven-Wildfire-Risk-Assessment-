from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert

from app.db.models.region import Region
from app.db.models.weather import FWIState, WeatherDaily
from app.db.session import async_session_factory
from app.domain.fwi import calculate_daily_fwi
from app.jobs.scheduler import tracked_job


@tracked_job("update_fwi_state")
async def job_update_fwi_state() -> int:
    today = date.today()
    yesterday = today - timedelta(days=1)
    updated_count = 0

    async with async_session_factory() as session:
        regions = (await session.execute(select(Region.id))).scalars().all()

        for region_id in regions:
            # 1. Fetch yesterday's carry-over FWI state
            prev_stmt = select(FWIState).where(
                FWIState.region_id == region_id, FWIState.date == yesterday
            )
            prev_fwi = (await session.execute(prev_stmt)).scalar_one_or_none()

            prev_ffmc = prev_fwi.ffmc if prev_fwi else 85.0
            prev_dmc = prev_fwi.dmc if prev_fwi else 6.0
            prev_dc = prev_fwi.dc if prev_fwi else 15.0

            # 2. Fetch today's weather
            w_stmt = select(WeatherDaily).where(
                WeatherDaily.region_id == region_id, WeatherDaily.date == today
            )
            w_row = (await session.execute(w_stmt)).scalar_one_or_none()

            temp = w_row.temp_max if (w_row and w_row.temp_max is not None) else 28.0
            rh = w_row.rh_min if (w_row and w_row.rh_min is not None) else 40.0
            wind = w_row.wind_max if (w_row and w_row.wind_max is not None) else 15.0
            rain = w_row.precip_sum if (w_row and w_row.precip_sum is not None) else 0.0

            # 3. Roll FWI calculation forward
            res = calculate_daily_fwi(
                temp=temp,
                rh=rh,
                wind=wind,
                rain=rain,
                month=today.month,
                prev_ffmc=prev_ffmc,
                prev_dmc=prev_dmc,
                prev_dc=prev_dc,
            )

            stmt = (
                insert(FWIState)
                .values(
                    region_id=region_id,
                    date=today,
                    ffmc=res.ffmc,
                    dmc=res.dmc,
                    dc=res.dc,
                    isi=res.isi,
                    bui=res.bui,
                    fwi=res.fwi,
                )
                .on_conflict_do_update(
                    index_elements=["region_id", "date"],
                    set_={
                        "ffmc": res.ffmc,
                        "dmc": res.dmc,
                        "dc": res.dc,
                        "isi": res.isi,
                        "bui": res.bui,
                        "fwi": res.fwi,
                    },
                )
            )
            await session.execute(stmt)
            updated_count += 1

        await session.commit()

    return updated_count
