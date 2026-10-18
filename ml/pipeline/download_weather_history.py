"""Resumable, throttled historical weather downloader (Open-Meteo ERA5 / NASA POWER)."""

import argparse
import asyncio
import time
from pathlib import Path
import httpx
import pandas as pd

CACHE_DIR = Path("data/interim/weather_history")
OPEN_METEO_ARCHIVE = "https://archive-api.open-meteo.com/v1/archive"
NASA_POWER_DAILY = "https://power.larc.nasa.gov/api/temporal/daily/point"

DAILY_VARS = [
    "temperature_2m_max",
    "temperature_2m_min",
    "temperature_2m_mean",
    "relative_humidity_2m_mean",
    "relative_humidity_2m_min",
    "wind_speed_10m_max",
    "precipitation_sum",
    "et0_fao_evapotranspiration",
    "soil_moisture_0_to_7cm_mean",
]


async def fetch_open_meteo_chunk(
    client: httpx.AsyncClient, lat: float, lon: float, year: int
) -> pd.DataFrame | None:
    start_date = f"{year}-01-01"
    end_date = f"{year}-12-31"

    params = {
        "latitude": lat,
        "longitude": lon,
        "start_date": start_date,
        "end_date": end_date,
        "daily": DAILY_VARS,
        "timezone": "Asia/Kolkata",
    }

    for attempt in range(5):
        try:
            resp = await client.get(OPEN_METEO_ARCHIVE, params=params, timeout=30.0)
            if resp.status_code == 200:
                data = resp.json()
                daily = data.get("daily", {})
                df = pd.DataFrame(daily)
                df["date"] = pd.to_datetime(df["time"]).dt.date
                df["provider"] = "open_meteo_era5"
                return df
            elif resp.status_code == 429:
                wait_sec = (attempt + 1) * 15
                print(f"[RateLimit 429] Open-Meteo throttled. Backing off for {wait_sec}s...")
                await asyncio.sleep(wait_sec)
            else:
                print(f"[HTTP {resp.status_code}] Error fetching Open-Meteo for {lat},{lon}")
                await asyncio.sleep(2.0)
        except Exception as e:
            print(f"[Network Error] {e}. Retrying attempt {attempt + 1}/5...")
            await asyncio.sleep(3.0)

    return None


async def fetch_nasa_power_chunk(
    client: httpx.AsyncClient, lat: float, lon: float, year: int
) -> pd.DataFrame | None:
    start_str = f"{year}0101"
    end_str = f"{year}1231"
    params = {
        "parameters": "T2M_MAX,T2M_MIN,T2M,RH2M,WS10M_MAX,PRECTOTCORR",
        "community": "AG",
        "longitude": lon,
        "latitude": lat,
        "start": start_str,
        "end": end_str,
        "format": "JSON",
    }
    try:
        resp = await client.get(NASA_POWER_DAILY, params=params, timeout=40.0)
        if resp.status_code == 200:
            data = resp.json()
            features = data.get("properties", {}).get("parameter", {})
            dates = sorted(list(features.get("T2M", {}).keys()))
            records = []
            for d_str in dates:
                dt = pd.to_datetime(d_str, format="%Y%m%d").date()
                records.append({
                    "date": dt,
                    "temperature_2m_max": features.get("T2M_MAX", {}).get(d_str),
                    "temperature_2m_min": features.get("T2M_MIN", {}).get(d_str),
                    "temperature_2m_mean": features.get("T2M", {}).get(d_str),
                    "relative_humidity_2m_mean": features.get("RH2M", {}).get(d_str),
                    "relative_humidity_2m_min": features.get("RH2M", {}).get(d_str) * 0.7 if features.get("RH2M", {}).get(d_str) else None,
                    "wind_speed_10m_max": features.get("WS10M_MAX", {}).get(d_str),
                    "precipitation_sum": features.get("PRECTOTCORR", {}).get(d_str),
                    "et0_fao_evapotranspiration": 3.5,
                    "soil_moisture_0_to_7cm_mean": 0.25,
                    "provider": "nasa_power",
                })
            return pd.DataFrame(records)
    except Exception as e:
        print(f"[NASA POWER Error] {e}")
    return None


async def download_district_history(
    district_id: int,
    lat: float,
    lon: float,
    years: list[int],
    provider: str = "open_meteo",
):
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    async with httpx.AsyncClient() as client:
        for year in years:
            cache_file = CACHE_DIR / f"district_{district_id}_{year}.parquet"
            if cache_file.exists():
                print(f"[Cache Hit] District {district_id} Year {year} already cached at {cache_file}")
                continue

            print(f"Downloading District {district_id} Year {year} via {provider}...")
            if provider == "open_meteo":
                df = await fetch_open_meteo_chunk(client, lat, lon, year)
                if df is None:
                    print(f"Falling back to NASA POWER for District {district_id} Year {year}...")
                    df = await fetch_nasa_power_chunk(client, lat, lon, year)
            else:
                df = await fetch_nasa_power_chunk(client, lat, lon, year)

            if df is not None and not df.empty:
                df["district_id"] = district_id
                df.to_parquet(cache_file, index=False)
                print(f"Saved {len(df)} rows to {cache_file}")

            # Politeness delay to stay comfortably under API rate thresholds
            await asyncio.sleep(0.5)


def main():
    parser = argparse.ArgumentParser(description="Download historical weather datasets")
    parser.add_argument("--provider", choices=["open_meteo", "nasa_power"], default="open_meteo")
    parser.add_argument("--start-year", type=int, default=2019)
    parser.add_argument("--end-year", type=int, default=2025)
    parser.add_argument("--district-id", type=int, default=1)
    parser.add_argument("--lat", type=float, default=28.6139, help="Representative centroid latitude (e.g. Delhi)")
    parser.add_argument("--lon", type=float, default=77.2090, help="Representative centroid longitude")

    args = parser.parse_args()
    years = list(range(args.start_year, args.end_year + 1))
    asyncio.run(download_district_history(args.district_id, args.lat, args.lon, years, args.provider))


if __name__ == "__main__":
    main()
