import os
from typing import Any

import yaml

from app.core.config import settings
from app.providers.base import AirQualityProvider, FireProvider, WeatherProvider
from app.providers.cpcb_datagovin import CPCBDataGovInProvider
from app.providers.firms import FirmsProvider
from app.providers.nasa_power import NasaPowerWeatherProvider
from app.providers.open_meteo_air import OpenMeteoAirProvider
from app.providers.open_meteo_weather import OpenMeteoWeatherProvider


class ProviderRegistry:
    def __init__(self, config_path: str | None = None):
        if not config_path:
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            config_path = os.path.join(base_dir, "data", "seed", "countries.yaml")

        self.countries: dict[str, Any] = {}
        if os.path.exists(config_path):
            with open(config_path, encoding="utf-8") as f:
                data = yaml.safe_load(f)
                self.countries = data.get("countries", {})

        # Default singleton instances
        self._firms = FirmsProvider()
        self._open_meteo_weather = OpenMeteoWeatherProvider()
        self._open_meteo_air = OpenMeteoAirProvider()
        self._cpcb = CPCBDataGovInProvider()
        self._nasa_power = NasaPowerWeatherProvider()

    def get_country_config(self, country_code: str | None = None) -> dict[str, Any]:
        code = (country_code or settings.DEFAULT_COUNTRY).upper()
        return self.countries.get(code, self.countries.get("IN", {}))

    def get_fire_provider(self, country_code: str | None = None) -> FireProvider:
        return self._firms

    def get_weather_provider(
        self, country_code: str | None = None, fallback: bool = False
    ) -> WeatherProvider:
        if fallback:
            return self._nasa_power
        return self._open_meteo_weather

    def get_air_quality_provider(self, country_code: str | None = None) -> AirQualityProvider:
        return self._open_meteo_air

    def get_cpcb_station_provider(self) -> CPCBDataGovInProvider:
        return self._cpcb


registry = ProviderRegistry()
