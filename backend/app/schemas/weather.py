from datetime import date

from pydantic import BaseModel, ConfigDict


class WeatherDailyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    region_id: int
    date: date
    temp_max: float | None = None
    temp_min: float | None = None
    temp_mean: float | None = None
    rh_mean: float | None = None
    rh_min: float | None = None
    wind_max: float | None = None
    precip_sum: float | None = None
    et0: float | None = None
    soil_moisture: float | None = None
    is_forecast: bool
    provider: str
