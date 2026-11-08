"""Ask GitHub Actions to run the Open-Meteo pipeline jobs now (workflow_dispatch).

Render's scheduler calls this at the jobs' times because GitHub's own `schedule` trigger ran
3-7 h late on 5-8 Nov 2026, while a workflow_dispatch run starts within about a minute. The jobs
themselves still run on GitHub (Render's shared outbound IP uses up Open-Meteo's daily quota).
"""

import httpx

from app.core.config import settings
from app.core.logging import logger

WORKFLOW_FILE = "pipeline-jobs.yml"
GITHUB_API = "https://api.github.com"


async def dispatch_pipeline_jobs(jobs: str) -> bool:
    """Start pipeline-jobs.yml with `jobs` (space separated). Returns True when GitHub accepts."""
    if not settings.GITHUB_DISPATCH_TOKEN:
        logger.warn("github_dispatch_skipped_no_token", jobs=jobs)
        return False
    url = f"{GITHUB_API}/repos/{settings.GITHUB_REPO}/actions/workflows/{WORKFLOW_FILE}/dispatches"
    headers = {
        "Authorization": f"Bearer {settings.GITHUB_DISPATCH_TOKEN}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    body = {"ref": settings.GITHUB_DISPATCH_REF, "inputs": {"jobs": jobs}}
    for attempt in range(1, 4):
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(url, headers=headers, json=body)
        except httpx.RequestError as e:
            logger.warn("github_dispatch_request_error", jobs=jobs, attempt=attempt, error=str(e))
            continue
        if resp.status_code == 204:
            logger.info("github_dispatch_ok", jobs=jobs, ref=settings.GITHUB_DISPATCH_REF)
            return True
        logger.error(
            "github_dispatch_failed", jobs=jobs, status=resp.status_code, body=resp.text[:200]
        )
        if resp.status_code < 500:
            return False
    return False


async def dispatch_daily_chain() -> None:
    await dispatch_pipeline_jobs("ingest_weather update_fwi_state predict_risk")


async def dispatch_weather_retry() -> None:
    await dispatch_pipeline_jobs("--unless-succeeded-within=12 ingest_weather")


async def dispatch_forecast_aqi() -> None:
    await dispatch_pipeline_jobs("forecast_aqi")
