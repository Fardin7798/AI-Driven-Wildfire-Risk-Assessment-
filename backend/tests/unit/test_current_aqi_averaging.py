"""Current AQI: CPCB averaging of Open-Meteo CAMS hourly values (fixed fixtures, network mocked)."""

from datetime import UTC, datetime, timedelta

import httpx
import pytest
import respx

from app.api.v1.air_quality import _serialize_aq
from app.db.models.air_quality import AQObservation
from app.domain.aqi import calculate_sub_index
from app.domain.aqi_features import CAMS_AVERAGED_PROVIDER, CPCB_AQI_DOC_URL
from app.providers.open_meteo_air import OpenMeteoAirProvider

URL = "https://air-quality-api.open-meteo.com/v1/air-quality"
NOW = datetime(2026, 11, 3, 3, 40, tzinfo=UTC)  # window = 2026-11-02T04:00 .. 2026-11-03T03:00
END = datetime(2026, 11, 3, 3, 0)
HOURS = [END - timedelta(hours=23 - i) for i in range(24)]


def _payload(**columns: list[float | None]) -> dict:
    hourly: dict[str, list] = {"time": [h.strftime("%Y-%m-%dT%H:%M") for h in HOURS]}
    for var in (
        "pm2_5",
        "pm10",
        "nitrogen_dioxide",
        "sulphur_dioxide",
        "carbon_monoxide",
        "ozone",
    ):
        hourly[var] = columns.get(var, [None] * 24)
    return {"hourly": hourly}


def _with_nulls(value: float, null_hours: range) -> list[float | None]:
    return [None if i in null_hours else value for i in range(24)]


async def _fetch(payload, coords=((20.9, 75.5),)):
    route = respx.get(URL).mock(return_value=httpx.Response(200, json=payload))
    out = await OpenMeteoAirProvider(air_url=URL).fetch_air_quality_batch(list(coords), now=NOW)
    return route, out


@pytest.mark.asyncio
@respx.mock
async def test_24h_means_and_16_hour_rule():
    payload = _payload(
        pm2_5=[float(i) for i in range(24)],  # mean 11.5
        pm10=[100.0] * 24,
        nitrogen_dioxide=_with_nulls(50.0, range(9)),  # 15 valid hours -> missing
        sulphur_dioxide=[None] * 8 + [float(i) for i in range(16)],  # 16 valid -> mean 7.5
    )
    route, out = await _fetch(payload)
    q = route.calls[0].request.url.params
    assert (q["start_hour"], q["end_hour"], q["timezone"]) == (
        "2026-11-02T04:00",
        "2026-11-03T03:00",
        "UTC",
    )
    assert "current" not in q
    obs = out[0][0]
    assert obs.observed_at_utc == END.replace(tzinfo=UTC)
    assert obs.provider == CAMS_AVERAGED_PROVIDER
    assert obs.pm25 == pytest.approx(11.5)
    assert obs.pm10 == pytest.approx(100.0)
    assert obs.no2 is None
    assert obs.so2 == pytest.approx(7.5)
    assert obs.co is None and obs.o3 is None
    # 3 pollutants incl. PM -> AQI = max sub-index (PM10 100 -> 100)
    assert obs.aqi == max(calculate_sub_index("pm25", 11.5), 100, calculate_sub_index("so2", 7.5))
    assert obs.aqi_category == "Satisfactory"


@pytest.mark.asyncio
@respx.mock
async def test_co_o3_max_8h_running_mean_with_6_of_8_rule():
    co = [1000.0] * 24
    co[10:18] = [5000.0] * 8  # one 8-h block at 5 mg/m3
    o3: list[float | None] = [None] * 24
    o3[0:6] = [60.0] * 6  # window hours 0..7 has exactly 6 valid hours -> 60
    o3[8:13] = [50.0] * 5  # 5 valid hours: no 8-h window here has 6
    o3[14:19] = [40.0] * 5  # 5 more (16 valid in total)
    o3[23] = 400.0  # isolated hour: no 8-h window around it has 6 valid hours
    assert sum(v is not None for v in o3) == 17
    _, out = await _fetch(_payload(carbon_monoxide=co, ozone=o3))
    obs = out[0][0]
    assert obs.co == pytest.approx(5.0)  # µg/m³ -> mg/m³ after averaging
    assert obs.o3 == pytest.approx(60.0)
    assert obs.aqi is None  # no PM2.5/PM10 -> no CPCB AQI


@pytest.mark.asyncio
@respx.mock
async def test_o3_missing_when_no_window_has_6_valid_hours():
    o3 = [None] * 24
    o3[0:5] = [60.0] * 5
    _, out = await _fetch(_payload(ozone=o3, pm2_5=[40.0] * 24, pm10=[80.0] * 24))
    obs = out[0][0]
    assert obs.o3 is None
    assert obs.aqi is None  # only two pollutants -> fewer than three -> no AQI


@pytest.mark.asyncio
@respx.mock
async def test_co_o3_need_16_valid_hours_in_24h_window():
    # 15 valid hours: hours 0..14 are 8 consecutive-valid windows, but CPCB needs >= 16 hours
    co15 = _with_nulls(2000.0, range(15, 24))
    o3_15 = _with_nulls(70.0, range(15, 24))
    _, out = await _fetch(_payload(carbon_monoxide=co15, ozone=o3_15))
    obs = out[0][0]
    assert obs.co is None and obs.o3 is None
    # 16 valid hours (one more) -> values computed
    co16 = _with_nulls(2000.0, range(16, 24))
    o3_16 = _with_nulls(70.0, range(16, 24))
    _, out = await _fetch(_payload(carbon_monoxide=co16, ozone=o3_16))
    obs = out[0][0]
    assert obs.co == pytest.approx(2.0)
    assert obs.o3 == pytest.approx(70.0)


def test_co_o3_16_hour_rule_direct_and_invalid_hours_do_not_count():
    import numpy as np
    import pandas as pd

    from app.domain.aqi_features import current_concentrations

    idx = pd.DatetimeIndex(HOURS)
    o3 = np.full(24, 30.0)
    o3[:8] = np.nan  # 16 valid
    co = np.full(24, 900.0)
    co[:9] = np.nan  # 15 valid
    frame = pd.DataFrame(dict.fromkeys(("pm25", "pm10", "no2", "so2"), np.nan), index=idx)
    frame["o3"], frame["co"] = o3, co
    out = current_concentrations(frame, END)
    assert out["o3"] == pytest.approx(30.0)
    assert out["co"] is None


@pytest.mark.asyncio
@respx.mock
async def test_invalid_and_out_of_window_hours_are_not_used():
    payload = _payload(pm2_5=[-5.0] * 9 + [20.0] * 15, pm10=[3270.0] * 24, ozone=[50.0] * 24)
    # an extra hour before the window with a huge value must be ignored
    payload["hourly"]["time"].insert(0, "2026-11-02T03:00")
    for var, val in payload["hourly"].items():
        if var != "time":
            val.insert(0, 900.0)
    _, out = await _fetch(payload)
    obs = out[0][0]
    assert obs.pm25 is None  # 9 negative hours -> 15 valid
    assert obs.pm10 is None  # CAMS PM10 ceiling = invalid
    assert obs.o3 == pytest.approx(50.0)


@pytest.mark.asyncio
@respx.mock
async def test_batch_one_request_and_unparseable_location_is_empty():
    good = _payload(pm2_5=[40.0] * 24, pm10=[80.0] * 24, ozone=[50.0] * 24)
    route, out = await _fetch([good, {"latitude": 21.1}], coords=((20.9, 75.5), (21.1, 79.0)))
    assert route.call_count == 1
    assert route.calls[0].request.url.params["latitude"] == "20.9000,21.1000"
    assert out[0][0].aqi == max(calculate_sub_index("pm25", 40.0), 80, 50)
    assert out[1] == []


@pytest.mark.asyncio
@respx.mock
async def test_single_fetch_uses_same_window():
    route, _ = await _fetch(_payload(pm2_5=[40.0] * 24))
    route.reset()
    out = await OpenMeteoAirProvider(air_url=URL).fetch_air_quality(20.9, 75.5, now=NOW)
    assert route.calls[0].request.url.params["end_hour"] == "2026-11-03T03:00"
    assert out[0].pm25 == pytest.approx(40.0)


def _orm(provider: str) -> AQObservation:
    return AQObservation(
        region_id=1,
        observed_at_utc=END.replace(tzinfo=UTC),
        pm25=40.0,
        pm10=80.0,
        aqi=80,
        aqi_category="Satisfactory",
        provider=provider,
    )


def test_response_exposes_averaging_window():
    resp = _serialize_aq(_orm(CAMS_AVERAGED_PROVIDER))
    a = resp.averaging
    assert a is not None
    assert a.window_start_utc == datetime(2026, 11, 2, 4, 0, tzinfo=UTC)
    assert a.window_end_utc == datetime(2026, 11, 3, 3, 0, tzinfo=UTC)
    assert a.window_hours == 24
    assert set(a.methods) == {"pm25", "pm10", "no2", "so2", "co", "o3"}
    assert "not a CPCB rule" in a.methods["o3"]
    for p in ("co", "o3"):
        assert a.methods[p].startswith(">= 16 valid hours in the 24h window")
    assert a.reference == CPCB_AQI_DOC_URL


def test_old_instantaneous_rows_get_no_averaging():
    assert _serialize_aq(_orm("copernicus_cams")).averaging is None
