import csv
import io
from collections.abc import Sequence
from datetime import UTC, datetime

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from app.core.config import settings
from app.core.logging import logger
from app.providers.base import FireProvider, RawFireDetection


class FirmsProvider(FireProvider):
    def __init__(self, map_key: str | None = None, sources: Sequence[str] | None = None):
        self.map_key = map_key or settings.FIRMS_MAP_KEY
        self.sources = list(sources or settings.FIRMS_SOURCES)

    @retry(
        retry=retry_if_exception_type((httpx.RequestError, httpx.HTTPStatusError)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1.5, min=2, max=10),
        reraise=False,
    )
    async def _fetch_source_csv(
        self, client: httpx.AsyncClient, source: str, bbox: Sequence[float], day_range: int
    ) -> str:
        west, south, east, north = bbox
        if not self.map_key:
            # Fallback public URL for South Asia 24h
            url = "https://firms.modaps.eosdis.nasa.gov/data/active_fire/noaa-20-viirs-c2/csv/J1_VIIRS_C2_South_Asia_24h.csv"
            resp = await client.get(url, timeout=15.0)
            resp.raise_for_status()
            return resp.text

        url = f"https://firms.modaps.eosdis.nasa.gov/api/area/csv/{self.map_key}/{source}/{west},{south},{east},{north}/{day_range}"
        resp = await client.get(url, timeout=20.0)
        resp.raise_for_status()
        return resp.text

    def parse_firms_csv(self, content: str, default_source: str) -> list[RawFireDetection]:
        results: list[RawFireDetection] = []
        if not content or "latitude" not in content.lower():
            return results

        f = io.StringIO(content)
        reader = csv.DictReader(f)
        for row in reader:
            try:
                lat = float(row.get("latitude", 0.0))
                lon = float(row.get("longitude", 0.0))
                bright_str = row.get("bright_ti4") or row.get("brightness")
                brightness = float(bright_str) if bright_str else None
                frp_str = row.get("frp")
                frp = float(frp_str) if frp_str else None
                confidence = str(row.get("confidence", "nominal"))
                daynight = str(row.get("daynight", "D"))
                satellite = str(row.get("satellite", "NOAA-20"))
                instrument = str(row.get("instrument", "VIIRS"))

                acq_date = row.get("acq_date", "2026-01-01")
                acq_time = row.get("acq_time", "0000").zfill(4)
                dt_str = f"{acq_date} {acq_time[:2]}:{acq_time[2:]}:00"
                acq_datetime = datetime.strptime(dt_str, "%Y-%m-%d %H:%M:%S").replace(tzinfo=UTC)

                results.append(
                    RawFireDetection(
                        lat=lat,
                        lon=lon,
                        brightness=brightness,
                        frp=frp,
                        confidence=confidence,
                        acq_datetime_utc=acq_datetime,
                        satellite=satellite,
                        instrument=instrument,
                        daynight=daynight,
                        source=default_source,
                    )
                )
            except Exception as e:
                logger.warn("firms_row_parse_error", error=str(e), row=row)
                continue

        return results

    async def fetch_live_fires(
        self, bbox: Sequence[float], day_range: int = 1
    ) -> list[RawFireDetection]:
        all_detections: list[RawFireDetection] = []
        day_range = max(1, min(5, day_range))

        async with httpx.AsyncClient(headers={"User-Agent": "WildfireRiskPlatform/2.0"}) as client:
            for src in self.sources:
                try:
                    csv_text = await self._fetch_source_csv(client, src, bbox, day_range)
                    if csv_text:
                        parsed = self.parse_firms_csv(csv_text, default_source=src)
                        all_detections.extend(parsed)
                except Exception as e:
                    logger.error("firms_fetch_failed", source=src, error=str(e))

        return all_detections
