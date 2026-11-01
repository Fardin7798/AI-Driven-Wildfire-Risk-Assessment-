"""Shared Open-Meteo HTTP client that respects the free-tier limits.

Free tier: 600 calls/min, 5,000/hour, 10,000/day, where a multi-location request counts once
per location. A minutely 429 is waited out; an hourly/daily 429 stops the job instead of
retrying into a longer ban.
"""

import asyncio
from typing import Any

import httpx

from app.core.logging import logger

MINUTE_LIMIT_WAIT_SECONDS = 61
MAX_ATTEMPTS = 3
# Pause between 50-location batches: 50 calls every 10 s = 300 calls/min, half the limit.
BATCH_PAUSE_SECONDS = 10.0


class OpenMeteoQuotaExceeded(RuntimeError):
    """Hourly or daily quota used up; further requests would only extend the block."""


async def get_json(url: str, params: dict[str, Any]) -> Any:
    last_error: Exception | None = None
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                resp = await client.get(url, params=params)
        except httpx.RequestError as e:
            last_error = e
            await asyncio.sleep(2**attempt)
            continue

        if resp.status_code == 429:
            reason = resp.text[:200]
            logger.warn("open_meteo_rate_limited", url=url, reason=reason, attempt=attempt)
            if "hourly" in reason.lower() or "daily" in reason.lower():
                raise OpenMeteoQuotaExceeded(reason)
            await asyncio.sleep(MINUTE_LIMIT_WAIT_SECONDS)
            last_error = httpx.HTTPStatusError("429", request=resp.request, response=resp)
            continue
        if resp.status_code >= 500:
            last_error = httpx.HTTPStatusError(
                str(resp.status_code), request=resp.request, response=resp
            )
            await asyncio.sleep(2**attempt)
            continue
        resp.raise_for_status()
        return resp.json()

    assert last_error is not None
    raise last_error
