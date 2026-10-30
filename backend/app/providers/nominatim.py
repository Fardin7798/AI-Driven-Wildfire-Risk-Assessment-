from typing import Any

import httpx

from app.core.logging import logger
from app.schemas.geo import CitySuggestion

NOMINATIM_SEARCH_URL = "https://nominatim.openstreetmap.org/search"


class NominatimGeocodingProvider:
    """Pure provider for geocoding Indian settlements via OpenStreetMap Nominatim API."""

    def __init__(
        self,
        base_url: str = NOMINATIM_SEARCH_URL,
        user_agent: str = "WildfireRiskPlatform/2.0 (contact: info@wildfire-platform.local)",
    ) -> None:
        self.base_url = base_url
        self.headers = {
            "User-Agent": user_agent,
            "Accept": "application/json",
        }

    async def search_cities(self, query: str, limit: int = 5) -> list[CitySuggestion]:
        clean_q = query.strip()
        if not clean_q or len(clean_q) < 2:
            return []

        params: dict[str, Any] = {
            "q": clean_q,
            "countrycodes": "in",
            "format": "json",
            "featuretype": "settlement",
            "addressdetails": 1,
            "limit": limit,
        }

        try:
            async with httpx.AsyncClient(timeout=4.0) as client:
                resp = await client.get(self.base_url, params=params, headers=self.headers)
                if resp.status_code != 200:
                    logger.warn("nominatim_status_error", status_code=resp.status_code)
                    return []

                data = resp.json()
                if not isinstance(data, list):
                    return []

                results: list[CitySuggestion] = []
                for item in data:
                    try:
                        raw_name = (
                            item.get("name") or item.get("display_name", "").split(",")[0].strip()
                        )
                        lat_val = float(item["lat"])
                        lon_val = float(item["lon"])
                        addr = item.get("address", {})
                        state = addr.get("state")
                        district = (
                            addr.get("county") or addr.get("state_district") or addr.get("district")
                        )
                        display_name = item.get("display_name", raw_name)

                        results.append(
                            CitySuggestion(
                                name=raw_name,
                                state=state,
                                district=district,
                                lat=lat_val,
                                lon=lon_val,
                                display_name=display_name,
                            )
                        )
                    except (KeyError, ValueError, TypeError) as parse_err:
                        logger.debug("nominatim_row_skip", error=str(parse_err))
                        continue

                return results

        except Exception as err:
            logger.warn("nominatim_request_failed", error=str(err), query=clean_q)
            return []
