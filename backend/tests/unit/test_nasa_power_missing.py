"""NASA POWER: fill values and absent days stay missing; callers skip, never fill."""

from datetime import date, timedelta

import pytest

from app.domain.features import ROLLING_WINDOW_DAYS
from app.jobs.predict_risk import missing_window_dates
from app.providers import nasa_power
from app.providers.nasa_power import NasaPowerWeatherProvider, parse_power_daily


def _payload(**overrides: dict[str, float]) -> dict:
    days = ["20261030", "20261031", "20261101"]
    params = {
        "T2M_MAX": dict.fromkeys(days, 31.0),
        "T2M_MIN": dict.fromkeys(days, 18.0),
        "T2M": dict.fromkeys(days, 24.5),
        "RH2M": dict.fromkeys(days, 55.0),
        "WS10M_MAX": dict.fromkeys(days, 5.0),
        "PRECTOTCORR": dict.fromkeys(days, 0.0),
    }
    for k, v in overrides.items():
        params[k] = {**params[k], **v}
    return {"header": {"fill_value": -999.0}, "properties": {"parameter": params}}


def test_complete_day_parsed_with_training_units():
    r = parse_power_daily(_payload())[0]
    assert r.record_date == date(2026, 10, 30)
    assert (r.temp_max, r.temp_min, r.temp_mean, r.rh_mean) == (31.0, 18.0, 24.5, 55.0)
    assert r.wind_max == pytest.approx(18.0)  # WS10M_MAX 5 m/s -> km/h, as in training
    assert r.precip_sum == 0.0
    assert r.provider == "nasa_power"
    # POWER has no RH minimum / FAO ET0 / volumetric soil moisture: never invented
    assert r.rh_min is None and r.et0 is None and r.soil_moisture is None


def test_fill_value_becomes_none_not_a_number():
    recs = parse_power_daily(
        _payload(
            RH2M={"20261101": -999.0},
            WS10M_MAX={"20261101": -999.0},
            PRECTOTCORR={"20261101": -999.0},
            T2M_MIN={"20261101": -999.0},
        )
    )
    last = recs[-1]
    assert last.record_date == date(2026, 11, 1)
    assert last.rh_mean is None
    assert last.wind_max is None
    assert last.precip_sum is None
    assert last.temp_min is None  # not temp_max - 5
    assert last.temp_max == 31.0
    assert recs[0].rh_mean == 55.0  # other days untouched


def test_header_fill_value_and_absent_day():
    data = _payload()
    data["header"]["fill_value"] = -99.0
    data["properties"]["parameter"]["T2M"]["20261031"] = -99.0
    del data["properties"]["parameter"]["RH2M"]["20261030"]
    del data["properties"]["parameter"]["T2M_MAX"]["20261101"]  # absent day in T2M_MAX only
    recs = {r.record_date: r for r in parse_power_daily(data)}
    assert len(recs) == 3  # a day missing from one parameter is still returned, not dropped
    assert recs[date(2026, 10, 30)].rh_mean is None
    assert recs[date(2026, 10, 31)].temp_mean is None
    assert recs[date(2026, 11, 1)].temp_max is None


def test_empty_response():
    assert parse_power_daily({}) == []


@pytest.mark.asyncio
async def test_fetch_forecast_requests_past_days_across_month_start(monkeypatch):
    captured: dict = {}

    async def fake_get_json(self, params):
        captured.update(params)
        return _payload(PRECTOTCORR={"20261101": -999.0})

    monkeypatch.setattr(NasaPowerWeatherProvider, "_get_json", fake_get_json)
    monkeypatch.setattr(nasa_power, "today_ist", lambda: date(2026, 11, 2))
    recs = await NasaPowerWeatherProvider().fetch_weather_forecast(20.9, 75.5, past_days=3)
    assert captured["start"] == "20261030" and captured["end"] == "20261102"
    assert "WS10M_MAX" in captured["parameters"]
    assert recs[-1].precip_sum is None


def test_window_complete():
    t = date(2026, 11, 3)
    days = {t - timedelta(days=k) for k in range(ROLLING_WINDOW_DAYS)}
    assert missing_window_dates(days, t) == []


def test_window_gap_or_short_history_is_reported():
    t = date(2026, 11, 3)
    days = {t - timedelta(days=k) for k in range(ROLLING_WINDOW_DAYS)}
    assert missing_window_dates(days - {t - timedelta(days=10)}, t) == [t - timedelta(days=10)]
    six_days = {t - timedelta(days=k) for k in range(6)}
    assert len(missing_window_dates(six_days, t)) == ROLLING_WINDOW_DAYS - 6
    # days outside the window do not count
    assert len(missing_window_dates(six_days | {t - timedelta(days=40)}, t)) == 25
