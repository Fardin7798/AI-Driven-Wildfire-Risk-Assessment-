from app.providers.base import (
    AirQualityProvider,
    FireProvider,
    RawAQObservation,
    RawDailyWeather,
    RawFireDetection,
    WeatherProvider,
)
from app.providers.cpcb_datagovin import CPCBDataGovInProvider
from app.providers.firms import FirmsProvider
from app.providers.nasa_power import NasaPowerWeatherProvider
from app.providers.open_meteo_air import OpenMeteoAirProvider
from app.providers.open_meteo_weather import OpenMeteoWeatherProvider
from app.providers.registry import ProviderRegistry, registry

__all__ = [
    "FireProvider",
    "WeatherProvider",
    "AirQualityProvider",
    "RawFireDetection",
    "RawDailyWeather",
    "RawAQObservation",
    "FirmsProvider",
    "OpenMeteoWeatherProvider",
    "OpenMeteoAirProvider",
    "CPCBDataGovInProvider",
    "NasaPowerWeatherProvider",
    "ProviderRegistry",
    "registry",
]
