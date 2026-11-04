from datetime import date

from app.providers.firms import FirmsProvider
from app.providers.open_meteo_weather import (
    PROVIDER_FORECAST,
    OpenMeteoWeatherProvider,
    parse_payload,
)
from app.providers.registry import ProviderRegistry


def test_firms_csv_parser():
    """Verify parsing of FIRMS CSV response text into typed RawFireDetection objects."""
    sample_csv = (
        "latitude,longitude,bright_ti4,scan,track,acq_date,acq_time,satellite,instrument,confidence,version,bright_ti5,frp,daynight\n"
        "30.2541,78.9812,345.2,0.4,0.4,2026-04-10,0815,NOAA-20,VIIRS,nominal,2.0NRT,298.1,12.4,D\n"
        "28.1122,76.5432,362.8,0.5,0.4,2026-04-10,0815,NOAA-20,VIIRS,high,2.0NRT,305.0,24.8,D\n"
    )
    provider = FirmsProvider()
    results = provider.parse_firms_csv(sample_csv, default_source="VIIRS_NOAA20_NRT")

    assert len(results) == 2
    f1 = results[0]
    assert f1.lat == 30.2541
    assert f1.lon == 78.9812
    assert f1.brightness == 345.2
    assert f1.frp == 12.4
    assert f1.confidence == "nominal"
    assert f1.satellite == "NOAA-20"
    assert f1.daynight == "D"
    assert f1.source == "VIIRS_NOAA20_NRT"
    assert f1.acq_datetime_utc.hour == 8
    assert f1.acq_datetime_utc.minute == 15


def test_open_meteo_weather_parser():
    """Daily aggregates from the API, temp_max/temp_min from the 24 hourly values."""
    payload = {
        "daily": {
            "time": ["2026-04-10"],
            "temperature_2m_mean": [28.6],
            "relative_humidity_2m_mean": [35.0],
            "relative_humidity_2m_min": [18.0],
            "wind_speed_10m_max": [16.4],
            "precipitation_sum": [0.0],
            "et0_fao_evapotranspiration": [5.8],
            "soil_moisture_0_to_7cm_mean": [0.14],
        },
        "hourly": {
            "time": [f"2026-04-10T{h:02d}:00" for h in range(24)],
            "temperature_2m": [22.0 + h * 0.5 for h in range(24)],
        },
    }
    parsed = parse_payload(payload, provider_name=PROVIDER_FORECAST)

    assert len(parsed) == 1
    d1 = parsed[0]
    assert d1.record_date == date(2026, 4, 10)
    assert d1.temp_max == 33.5 and d1.temp_min == 22.0
    assert d1.wind_max == 16.4
    assert d1.rh_min == 18.0
    assert d1.precip_sum == 0.0
    assert d1.provider == "open_meteo_ecmwf_ifs"


def test_provider_registry_country_config():
    """Verify registry resolves India country bbox and providers."""
    reg = ProviderRegistry()
    in_cfg = reg.get_country_config("IN")
    assert in_cfg["country_code"] == "IN"
    assert in_cfg["bbox"] == [68.0, 6.5, 97.5, 37.5]
    assert in_cfg["admin_level"] == 2

    # Providers can be instantiated
    fire_prov = reg.get_fire_provider("IN")
    weather_prov = reg.get_weather_provider("IN")
    aq_prov = reg.get_air_quality_provider("IN")

    assert fire_prov is not None
    assert weather_prov is not None
    assert isinstance(weather_prov, OpenMeteoWeatherProvider)
    assert aq_prov is not None


def test_cpcb_datagovin_calculation_integration():
    """Verify that when raw pollutant readings are parsed, CPCB AQI sub-indices correctly match."""
    from app.domain.aqi import calculate_cpcb_aqi

    # Sample reading resembling Anand Vihar, Delhi during post-monsoon
    pollutants = {
        "pm25": 185.0,  # Unhealthy / Very Poor (>120)
        "pm10": 310.0,  # Very Poor (>250)
        "no2": 65.0,  # Moderate
        "so2": 14.0,  # Good
        "co": 1.8,  # Moderate
        "o3": 45.0,  # Good
    }
    aqi_res = calculate_cpcb_aqi(pollutants)
    assert aqi_res is not None
    assert aqi_res.aqi >= 300
    assert aqi_res.category == "Very Poor"
    assert aqi_res.prominent_pollutant in ["PM25", "PM10"]
