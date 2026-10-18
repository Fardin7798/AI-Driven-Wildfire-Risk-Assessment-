"""Scheduled background jobs and task runners."""

from app.jobs.forecast_aqi import job_forecast_aqi
from app.jobs.ingest_air_quality import job_ingest_air_quality
from app.jobs.ingest_fires import job_ingest_fires
from app.jobs.ingest_weather import job_ingest_weather
from app.jobs.predict_risk import job_predict_risk
from app.jobs.retention import job_retention
from app.jobs.scheduler import scheduler, start_scheduler, stop_scheduler, tracked_job
from app.jobs.update_fwi_state import job_update_fwi_state

__all__ = [
    "job_forecast_aqi",
    "job_ingest_air_quality",
    "job_ingest_fires",
    "job_ingest_weather",
    "job_predict_risk",
    "job_retention",
    "job_update_fwi_state",
    "scheduler",
    "start_scheduler",
    "stop_scheduler",
    "tracked_job",
]
