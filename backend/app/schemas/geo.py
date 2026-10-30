from pydantic import BaseModel


class CitySuggestion(BaseModel):
    name: str
    state: str | None = None
    district: str | None = None
    lat: float
    lon: float
    display_name: str
