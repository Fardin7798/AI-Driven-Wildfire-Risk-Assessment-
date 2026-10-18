from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import verify_job_token
from app.jobs.forecast_aqi import job_forecast_aqi
from app.jobs.ingest_air_quality import job_ingest_air_quality
from app.jobs.ingest_fires import job_ingest_fires
from app.jobs.ingest_weather import job_ingest_weather
from app.jobs.predict_risk import job_predict_risk
from app.jobs.retention import job_retention
from app.jobs.update_fwi_state import job_update_fwi_state
from app.schemas.jobs import JobTriggerResponse

router = APIRouter(prefix="/internal/jobs", tags=["Internal Pipeline Triggers"])

JOB_MAPPING = {
    "ingest_fires": job_ingest_fires,
    "ingest_weather": job_ingest_weather,
    "update_fwi_state": job_update_fwi_state,
    "predict_risk": job_predict_risk,
    "ingest_air_quality": job_ingest_air_quality,
    "forecast_aqi": job_forecast_aqi,
    "retention": job_retention,
}


@router.post(
    "/{job_name}",
    response_model=JobTriggerResponse,
    dependencies=[Depends(verify_job_token)],
    include_in_schema=False,
)
async def trigger_internal_job(job_name: str) -> JobTriggerResponse:
    """Trigger an ingestion or batch computation job on demand. Protected by X-Job-Token."""
    handler = JOB_MAPPING.get(job_name)
    if not handler:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Unknown job '{job_name}'. Valid jobs: {list(JOB_MAPPING.keys())}",
        )

    try:
        rows = await handler()
        return JobTriggerResponse(
            job_name=job_name,
            status="success",
            rows_written=rows,
            message=f"Job '{job_name}' completed with {rows} records processed.",
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Job '{job_name}' execution failed: {str(e)[:300]}",
        ) from e
