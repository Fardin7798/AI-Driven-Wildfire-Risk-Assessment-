"""
Indian National Air Quality Index (NAQI) Standard Implementation.
Reference: Central Pollution Control Board (CPCB), Ministry of Environment, Forest & Climate Change (2014).
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class AQIResult:
    aqi: int
    category: str
    prominent_pollutant: str
    sub_indices: dict[str, int]


# Breakpoint format: (B_low, B_high, I_low, I_high)
BREAKPOINTS: dict[str, list[tuple[float, float, int, int]]] = {
    "pm25": [
        (0.0, 30.0, 0, 50),
        (31.0, 60.0, 51, 100),
        (61.0, 90.0, 101, 200),
        (91.0, 120.0, 201, 300),
        (121.0, 250.0, 301, 400),
        (251.0, 500.0, 401, 500),
    ],
    "pm10": [
        (0.0, 50.0, 0, 50),
        (51.0, 100.0, 51, 100),
        (101.0, 250.0, 101, 200),
        (251.0, 350.0, 201, 300),
        (351.0, 430.0, 301, 400),
        (431.0, 600.0, 401, 500),
    ],
    "no2": [
        (0.0, 40.0, 0, 50),
        (41.0, 80.0, 51, 100),
        (81.0, 180.0, 101, 200),
        (181.0, 280.0, 201, 300),
        (281.0, 400.0, 301, 400),
        (401.0, 1000.0, 401, 500),
    ],
    "so2": [
        (0.0, 40.0, 0, 50),
        (41.0, 80.0, 51, 100),
        (81.0, 380.0, 101, 200),
        (381.0, 800.0, 201, 300),
        (801.0, 1600.0, 301, 400),
        (1601.0, 2000.0, 401, 500),
    ],
    "co": [
        (0.0, 1.0, 0, 50),
        (1.1, 2.0, 51, 100),
        (2.1, 10.0, 101, 200),
        (10.1, 17.0, 201, 300),
        (17.1, 34.0, 301, 400),
        (34.1, 60.0, 401, 500),
    ],
    "o3": [
        (0.0, 50.0, 0, 50),
        (51.0, 100.0, 51, 100),
        (101.0, 168.0, 101, 200),
        (169.0, 208.0, 201, 300),
        (209.0, 748.0, 301, 400),
        (749.0, 1000.0, 401, 500),
    ],
    "nh3": [
        (0.0, 200.0, 0, 50),
        (201.0, 400.0, 51, 100),
        (401.0, 800.0, 101, 200),
        (801.0, 1200.0, 201, 300),
        (1201.0, 1800.0, 301, 400),
        (1801.0, 2400.0, 401, 500),
    ],
}


def calculate_sub_index(pollutant: str, conc: float) -> int | None:
    """Sub-index for one pollutant by the CPCB piecewise-linear formula.

    CPCB tables give breakpoints at the reporting precision (PM2.5 0-30, 31-60; CO 1.0, 1.1).
    A value between two rows (PM2.5 30.4) is rounded to that precision: it belongs to the row
    whose edge is nearer, with the midpoint going up, and is then clamped to that row.
    """
    if conc < 0.0 or pollutant not in BREAKPOINTS:
        return None

    ranges = BREAKPOINTS[pollutant]
    if conc > ranges[-1][1]:
        return 500
    for i, (b_low, b_high, i_low, i_high) in enumerate(ranges):
        upper = (b_high + ranges[i + 1][0]) / 2 if i + 1 < len(ranges) else b_high
        if conc < upper or i + 1 == len(ranges):
            c = min(max(conc, b_low), b_high)
            return round(((i_high - i_low) / (b_high - b_low)) * (c - b_low) + i_low)
    return None


def get_aqi_category(aqi: int) -> str:
    """Map numeric AQI to official CPCB health category."""
    if aqi <= 50:
        return "Good"
    elif aqi <= 100:
        return "Satisfactory"
    elif aqi <= 200:
        return "Moderate"
    elif aqi <= 300:
        return "Poor"
    elif aqi <= 400:
        return "Very Poor"
    else:
        return "Severe"


def calculate_cpcb_aqi(pollutants: dict[str, float | None]) -> AQIResult | None:
    """
    Composite CPCB National AQI from a pollutant dictionary.
    Keys expected: pm25, pm10, no2, so2, co, o3, nh3 (concentrations in µg/m³, CO in mg/m³).

    CPCB rule: the AQI is reported only when at least three pollutants are available and one of
    them is PM2.5 or PM10. Otherwise there is no valid AQI and None is returned.
    """
    sub_indices: dict[str, int] = {}

    for pol, val in pollutants.items():
        if val is not None:
            sub = calculate_sub_index(pol.lower(), val)
            if sub is not None:
                sub_indices[pol.lower()] = sub

    if len(sub_indices) < 3 or not ({"pm25", "pm10"} & sub_indices.keys()):
        return None

    # Composite AQI is the maximum of the sub-indices
    prominent = max(sub_indices, key=sub_indices.get)  # type: ignore[arg-type]
    max_aqi = sub_indices[prominent]

    return AQIResult(
        aqi=max_aqi,
        category=get_aqi_category(max_aqi),
        prominent_pollutant=prominent.upper(),
        sub_indices=sub_indices,
    )
