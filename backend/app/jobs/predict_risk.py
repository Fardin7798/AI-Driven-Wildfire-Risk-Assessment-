from datetime import timedelta

from sqlalchemy import func, select

from app.core.timeutil import today_ist
from app.db.models.fire import FireDetection
from app.db.models.region import Region
from app.db.models.weather import FWIState, WeatherDaily
from app.db.session import async_session_factory
from app.domain.features import DailyWeatherRecord, extract_features
from app.jobs.scheduler import tracked_job
from app.ml.wildfire_predictor import predict_wildfire_risk
from app.services.risk_service import save_risk_prediction


@tracked_job("predict_risk")
async def job_predict_risk() -> int:
    today = today_ist()
    cutoff_30d = today - timedelta(days=30)
    cutoff_7d = today - timedelta(days=7)
    predicted_count = 0

    async with async_session_factory() as session:
        regions = (await session.execute(select(Region))).scalars().all()
        if not regions:
            return 0

        # 1. Bulk prefetch weather history for past 30 days across all regions
        w_stmt = (
            select(WeatherDaily)
            .where(
                WeatherDaily.date >= cutoff_30d,
                WeatherDaily.date <= today,
            )
            .order_by(WeatherDaily.region_id, WeatherDaily.date.asc())
        )
        all_weather_rows = (await session.execute(w_stmt)).scalars().all()
        weather_map: dict[int, list[DailyWeatherRecord]] = {}
        for r in all_weather_rows:
            rec = DailyWeatherRecord(
                record_date=r.date,
                temp_max=r.temp_max or 25.0,
                temp_mean=r.temp_mean or 20.0,
                rh_min=r.rh_min or 30.0,
                rh_mean=r.rh_mean or 50.0,
                wind_max=r.wind_max or 10.0,
                precip_sum=r.precip_sum or 0.0,
                et0=r.et0 or 3.0,
                soil_moisture=r.soil_moisture or 0.2,
            )
            weather_map.setdefault(r.region_id, []).append(rec)

        # 2. Bulk prefetch FWI state for today
        fwi_stmt = select(FWIState).where(FWIState.date == today)
        fwi_rows = (await session.execute(fwi_stmt)).scalars().all()
        fwi_map: dict[int, FWIState] = {row.region_id: row for row in fwi_rows}

        # 3. Bulk aggregate fire counts
        fires_7d_q = (
            select(FireDetection.region_id, func.count(FireDetection.id))
            .where(
                FireDetection.acq_datetime_utc >= cutoff_7d,
                FireDetection.acq_datetime_utc < today,
            )
            .group_by(FireDetection.region_id)
        )
        fires_7d_map = dict((await session.execute(fires_7d_q)).all())

        fires_30d_q = (
            select(FireDetection.region_id, func.count(FireDetection.id))
            .where(
                FireDetection.acq_datetime_utc >= cutoff_30d,
                FireDetection.acq_datetime_utc < today,
            )
            .group_by(FireDetection.region_id)
        )
        fires_30d_map = dict((await session.execute(fires_30d_q)).all())

        for reg in regions:
            weather_history = weather_map.get(reg.id, [])
            today_weather = next((w for w in weather_history if w.record_date == today), None)
            if not today_weather:
                today_weather = DailyWeatherRecord(
                    record_date=today,
                    temp_max=30.0,
                    temp_mean=25.0,
                    rh_min=30.0,
                    rh_mean=50.0,
                    wind_max=12.0,
                    precip_sum=0.0,
                    et0=4.0,
                    soil_moisture=0.15,
                )

            fwi_row = fwi_map.get(reg.id)
            fwi_dict = {
                "ffmc": fwi_row.ffmc if fwi_row else 85.0,
                "dmc": fwi_row.dmc if fwi_row else 6.0,
                "dc": fwi_row.dc if fwi_row else 15.0,
                "isi": fwi_row.isi if fwi_row else 2.0,
                "bui": fwi_row.bui if fwi_row else 8.0,
                "fwi": fwi_row.fwi if fwi_row else 5.0,
            }

            fires_prev_7d = fires_7d_map.get(reg.id, 0)
            fires_prev_30d = fires_30d_map.get(reg.id, 0)

            lat = reg.centroid_lat or 28.6139
            lon = reg.centroid_lon or 77.2090
            features = extract_features(
                target_date=today,
                current_weather=today_weather,
                weather_history=weather_history,
                fwi_values=fwi_dict,
                lat=lat,
                lon=lon,
                landcover=reg.landcover or {},
                fires_prev_7d=fires_prev_7d,
                fires_prev_30d=fires_prev_30d,
                climatological_fire_freq=0.01,
            )

            pred = predict_wildfire_risk(features)

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
            predicted_count += 1

        await session.commit()

    return predicted_count
