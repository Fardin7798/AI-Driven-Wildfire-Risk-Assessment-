"""Resumable, throttled Open-Meteo CAMS Air Quality history downloader."""

import argparse
import asyncio
from pathlib import Path
import httpx
import pandas as pd

CACHE_DIR = Path("data/interim/air_history")
OPEN_METEO_AQ_URL = "https://air-quality-api.open-meteo.com/v1/air-quality"

AQ_VARS = [
    "pm2_5",
    "pm10",
    "nitrogen_dioxide",
    "sulphur_dioxide",
    "carbon_monoxide",
    "ozone",
    "ammonia",
]


async def fetch_cams_air_chunk(
    client: httpx.AsyncClient, lat: float, lon: float, year: int
) -> pd.DataFrame | None:
    # CAMS history is reliably available from September 2022 onwards
    start_date = f"{year}-01-01" if year >= 2023 else "2022-09-01"
    end_date = f"{year}-12-31"

    params = {
        "latitude": lat,
        "longitude": lon,
        "start_date": start_date,
        "end_date": end_date,
        "hourly": AQ_VARS,
        "timezone": "Asia/Kolkata",
    }

    for attempt in range(5):
        try:
            resp = await client.get(OPEN_METEO_AQ_URL, params=params, timeout=35.0)
            if resp.status_code == 200:
                data = resp.json()
                hourly = data.get("hourly", {})
                df = pd.DataFrame(hourly)
                df["time"] = pd.to_datetime(df["time"])
                df["date"] = df["time"].dt.date

                # Aggregate hourly to daily means and maximums
                daily_agg = df.groupby("date").agg({
                    "pm2_5": ["mean", "max"],
                    "pm10": ["mean", "max"],
                    "nitrogen_dioxide": "mean",
                    "sulphur_dioxide": "mean",
                    "carbon_monoxide": "mean",
                    "ozone": "max",
                    "ammonia": "mean",
                }).reset_index()
                # Flatten multiindex columns
                daily_agg.columns = [
                    "_".join(c).strip("_") if isinstance(c, tuple) else c
                    for c in daily_agg.columns
                ]
                daily_agg["provider"] = "open_meteo_cams"
                return daily_agg
            elif resp.status_code == 429:
                wait_sec = (attempt + 1) * 15
                print(f"[RateLimit 429] Open-Meteo AQ throttled. Waiting {wait_sec}s...")
                await asyncio.sleep(wait_sec)
            else:
                print(f"[HTTP {resp.status_code}] Error fetching AQ for {lat},{lon}")
                await asyncio.sleep(2.0)
        except Exception as e:
            print(f"[Network Error] {e}. Attempt {attempt + 1}/5...")
            await asyncio.sleep(3.0)

    return None


async def download_district_air_history(
    district_id: int, lat: float, lon: float, years: list[int]
):
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    async with httpx.AsyncClient() as client:
        for year in years:
            if year < 2022:
                continue
            cache_file = CACHE_DIR / f"district_aq_{district_id}_{year}.parquet"
            if cache_file.exists():
                print(f"[Cache Hit] District {district_id} Year {year} already cached.")
                continue

            print(f"Downloading AQ history for District {district_id} Year {year}...")
            df = await fetch_cams_air_chunk(client, lat, lon, year)
            if df is not None and not df.empty:
                df["district_id"] = district_id
                df.to_parquet(cache_file, index=False)
                print(f"Saved {len(df)} daily AQ rows to {cache_file}")

            await asyncio.sleep(0.5)


def main():
    parser = argparse.ArgumentParser(description="Download historical atmospheric air quality datasets")
    parser.add_argument("--start-year", type=int, default=2022)
    parser.add_argument("--end-year", type=int, default=2025)
    parser.add_argument("--district-id", type=int, default=1)
    parser.add_argument("--lat", type=float, default=28.6139)
    parser.add_argument("--lon", type=float, default=77.2090)

    args = parser.parse_args()
    years = list(range(args.start_year, args.end_year + 1))
    asyncio.run(download_district_air_history(args.district_id, args.lat, args.lon, years))


if __name__ == "__main__":
    main()
