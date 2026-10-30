from fastapi import APIRouter, Query

from app.providers.nominatim import NominatimGeocodingProvider
from app.schemas.geo import CitySuggestion

router = APIRouter(prefix="/geo", tags=["Geocoding"])

nominatim_provider = NominatimGeocodingProvider()


@router.get("/cities", response_model=list[CitySuggestion])
async def search_cities(
    q: str = Query(
        ..., min_length=2, max_length=100, description="City, town, or settlement search query"
    ),
    limit: int = Query(
        default=5, ge=1, le=20, description="Maximum number of city suggestions to return"
    ),
) -> list[CitySuggestion]:
    """Search Indian cities, towns, and settlements directly via OpenStreetMap Nominatim."""
    return await nominatim_provider.search_cities(query=q, limit=limit)
