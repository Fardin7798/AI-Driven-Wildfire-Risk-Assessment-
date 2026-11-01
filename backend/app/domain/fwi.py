"""
Canadian Forest Fire Weather Index (FWI) System Implementation.
Reference: Van Wagner (1987) Development and structure of the Canadian Forest Fire
Weather Index System. Forestry Technical Report 35. Canadian Forestry Service.
"""

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class FWIResult:
    ffmc: float
    dmc: float
    dc: float
    isi: float
    bui: float
    fwi: float


# Day length adjustment factors for DMC (hours of drying by month for latitudes near India / North of Equator)
DMC_DAY_LENGTH_NORTH: dict[int, float] = {
    1: 6.5,
    2: 7.5,
    3: 9.0,
    4: 12.8,
    5: 13.9,
    6: 13.9,
    7: 12.4,
    8: 10.9,
    9: 9.4,
    10: 8.0,
    11: 7.0,
    12: 6.0,
}

# Day length adjustment factor for DC by month (North of Equator)
DC_DAY_LENGTH_NORTH: dict[int, float] = {
    1: -1.6,
    2: -1.6,
    3: -1.6,
    4: 0.9,
    5: 3.8,
    6: 5.8,
    7: 6.4,
    8: 5.0,
    9: 2.4,
    10: 0.4,
    11: -1.6,
    12: -1.6,
}


def compute_ffmc(
    temp: float, rh: float, wind: float, rain: float, prev_ffmc: float = 85.0
) -> float:
    """Calculate Fine Fuel Moisture Code (FFMC)."""
    # Pre-condition bounds
    rh = max(0.0, min(100.0, rh))
    wind = max(0.0, wind)
    temp = max(-10.0, temp)

    # Initial moisture content
    m_0 = 147.2 * (101.0 - prev_ffmc) / (59.5 + prev_ffmc)

    # Rain reduction
    if rain > 0.5:
        r_f = rain - 0.5
        if m_0 > 150.0:
            m_r = (
                m_0
                + 42.5 * r_f * math.exp(-100.0 / (251.0 - m_0)) * (1.0 - math.exp(-6.93 / r_f))
                + (0.0015 * ((m_0 - 150.0) ** 2)) * math.sqrt(r_f)
            )
        else:
            m_r = m_0 + 42.5 * r_f * math.exp(-100.0 / (251.0 - m_0)) * (
                1.0 - math.exp(-6.93 / r_f)
            )
        m_r = min(250.0, m_r)
        m_0 = m_r

    # Equilibrium Moisture Content (EMC)
    e_d = (
        0.942 * (rh**0.679)
        + 11.0 * math.exp((rh - 100.0) / 10.0)
        + 0.18 * (21.1 - temp) * (1.0 - math.exp(-0.115 * rh))
    )

    if m_0 > e_d:
        # Drying rate k_a and k_d
        k_a = 0.424 * (1.0 - (rh / 100.0) ** 1.7) + 0.0694 * (wind**0.5) * (1.0 - (rh / 100.0) ** 8)
        k_d = k_a * 0.581 * math.exp(0.0365 * temp)
        m = e_d + (m_0 - e_d) * (10.0 ** (-k_d))
    else:
        # Wetting equilibrium E_w and rate k_w
        e_w = (
            0.618 * (rh**0.753)
            + 10.0 * math.exp((rh - 100.0) / 10.0)
            + 0.18 * (21.1 - temp) * (1.0 - math.exp(-0.115 * rh))
        )
        if m_0 < e_w:
            k_a = 0.424 * (1.0 - ((100.0 - rh) / 100.0) ** 1.7) + 0.0694 * (wind**0.5) * (
                1.0 - ((100.0 - rh) / 100.0) ** 8
            )
            k_w = k_a * 0.581 * math.exp(0.0365 * temp)
            m = e_w - (e_w - m_0) * (10.0 ** (-k_w))
        else:
            m = m_0

    ffmc = 59.5 * (250.0 - m) / (147.2 + m)
    return max(0.0, min(101.0, round(ffmc, 2)))


def compute_dmc(temp: float, rh: float, rain: float, month: int, prev_dmc: float = 6.0) -> float:
    """Calculate Duff Moisture Code (DMC)."""
    temp = max(-1.1, temp)
    rh = max(0.0, min(100.0, rh))

    day_length = DMC_DAY_LENGTH_NORTH.get(month, 9.0)

    # Effective rain
    if rain > 1.5:
        r_e = 0.92 * rain - 1.27
        m_0 = 20.0 + 280.0 / math.exp(0.023 * prev_dmc)
        if prev_dmc <= 33.0:
            b = 100.0 / (0.5 + 0.3 * prev_dmc)
        elif prev_dmc <= 65.0:
            b = 14.0 - 1.3 * math.log(prev_dmc)
        else:
            b = 6.2 * math.log(prev_dmc) - 17.2

        m_r = m_0 + 1000.0 * r_e / (48.77 + b * r_e)
        dmc_rain = 43.43 * (5.6348 - math.log(m_r - 20.0))
        prev_dmc = max(0.0, dmc_rain)

    # Daily drying
    if temp > -1.1:
        k = 1.894 * (temp + 1.1) * (100.0 - rh) * day_length * 1e-4
    else:
        k = 0.0

    return max(0.0, round(prev_dmc + k, 2))


def compute_dc(temp: float, rain: float, month: int, prev_dc: float = 15.0) -> float:
    """Calculate Drought Code (DC)."""
    temp = max(-2.8, temp)
    day_length = DC_DAY_LENGTH_NORTH.get(month, 1.4)

    # Effective rain
    if rain > 2.8:
        r_d = 0.83 * rain - 1.27
        q_0 = 800.0 * math.exp(-prev_dc / 400.0)
        q_r = q_0 + 3.937 * r_d
        prev_dc = max(0.0, 400.0 * math.log(800.0 / q_r))

    # Daily potential evapotranspiration
    if temp > -2.8:
        v = 0.36 * (temp + 2.8) + day_length
        v = max(0.0, v)
    else:
        v = 0.0

    return max(0.0, round(prev_dc + 0.5 * v, 2))


def compute_isi(ffmc: float, wind: float) -> float:
    """Calculate Initial Spread Index (ISI)."""
    wind = max(0.0, wind)
    f_w = math.exp(0.05039 * wind)
    m = 147.2 * (101.0 - ffmc) / (59.5 + ffmc)
    f_f = 91.9 * math.exp(-0.1386 * m) * (1.0 + (m**5.31) / (4.93 * 1e7))
    return max(0.0, round(0.208 * f_w * f_f, 2))


def compute_bui(dmc: float, dc: float) -> float:
    """Calculate Buildup Index (BUI)."""
    if dmc <= 0.0 and dc <= 0.0:
        return 0.0
    if dmc <= 0.4 * dc:
        bui = 0.8 * dmc * dc / (dmc + 0.4 * dc)
    else:
        bui = dmc - (1.0 - 0.8 * dc / (dmc + 0.4 * dc)) * (0.92 + (0.0114 * dmc) ** 1.7)
    return max(0.0, round(bui, 2))


def compute_fwi(isi: float, bui: float) -> float:
    """Calculate Fire Weather Index (FWI)."""
    if bui <= 80.0:
        f_d = 0.626 * (bui**0.809) + 2.0
    else:
        f_d = 1000.0 / (25.0 + 108.64 * math.exp(-0.023 * bui))

    b = 0.1 * isi * f_d
    if b > 1.0:
        ln_fwi = 2.72 * ((0.434 * math.log(b)) ** 0.647)
        fwi = math.exp(ln_fwi)
    else:
        fwi = b
    return max(0.0, round(fwi, 2))


def calculate_daily_fwi(
    temp: float,
    rh: float,
    wind: float,
    rain: float,
    month: int,
    prev_ffmc: float = 85.0,
    prev_dmc: float = 6.0,
    prev_dc: float = 15.0,
) -> FWIResult:
    """Roll Canadian FWI forward by one day from previous carry-over state."""
    ffmc = compute_ffmc(temp=temp, rh=rh, wind=wind, rain=rain, prev_ffmc=prev_ffmc)
    dmc = compute_dmc(temp=temp, rh=rh, rain=rain, month=month, prev_dmc=prev_dmc)
    dc = compute_dc(temp=temp, rain=rain, month=month, prev_dc=prev_dc)
    isi = compute_isi(ffmc=ffmc, wind=wind)
    bui = compute_bui(dmc=dmc, dc=dc)
    fwi = compute_fwi(isi=isi, bui=bui)

    return FWIResult(
        ffmc=ffmc,
        dmc=dmc,
        dc=dc,
        isi=isi,
        bui=bui,
        fwi=fwi,
    )


# Standard Van Wagner start-up moisture codes, used only when a region has no carry-over state
# (first run, or a gap longer than FWI_MAX_CARRYOVER_GAP_DAYS).
FWI_STARTUP = {"ffmc": 85.0, "dmc": 6.0, "dc": 15.0}
FWI_MAX_CARRYOVER_GAP_DAYS = 3


def fwi_inputs(
    temp_max: float | None,
    rh_mean: float | None,
    wind_max_kmh: float | None,
    precip_mm: float | None,
) -> dict[str, float] | None:
    """Map one day of weather to FWI inputs. Identical in training and live inference.

    Uses daily max temperature, daily MEAN relative humidity (the training archive, NASA POWER,
    has no daily RH minimum), daily max 10 m wind in km/h and 24 h precipitation.
    Returns None if any input is missing; callers must skip the day rather than invent values.
    """
    values = (temp_max, rh_mean, wind_max_kmh, precip_mm)
    if any(v is None for v in values):
        return None
    return {
        "temp": float(temp_max),  # type: ignore[arg-type]
        "rh": min(100.0, max(0.0, float(rh_mean))),  # type: ignore[arg-type]
        "wind": max(0.0, float(wind_max_kmh)),  # type: ignore[arg-type]
        "rain": max(0.0, float(precip_mm)),  # type: ignore[arg-type]
    }
