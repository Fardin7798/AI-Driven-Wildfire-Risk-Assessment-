"""NASA FIRMS Country Yearly Summary Ingestion & Downloader."""

import argparse
from pathlib import Path
import pandas as pd

RAW_FIRMS_DIR = Path("data/raw/firms")
YEARS = list(range(2019, 2026))


def verify_and_index_firms_history(raw_dir: Path) -> dict[str, list[Path]]:
    """Scan and index yearly FIRMS CSV archives placed in raw data directory."""
    raw_dir.mkdir(parents=True, exist_ok=True)
    indexed: dict[str, list[Path]] = {"modis": [], "viirs_noaa20": [], "viirs_snpp": []}

    csv_files = list(raw_dir.glob("*.csv")) + list(raw_dir.glob("*.csv.gz"))
    print(f"Found {len(csv_files)} FIRMS archive files in {raw_dir}")

    for f in csv_files:
        fname = f.name.lower()
        if "modis" in fname:
            indexed["modis"].append(f)
        elif "noaa20" in fname or "noaa-20" in fname or "j1" in fname:
            indexed["viirs_noaa20"].append(f)
        elif "snpp" in fname or "suomi" in fname:
            indexed["viirs_snpp"].append(f)

    for source, files in indexed.items():
        print(f"  - Source '{source}': {len(files)} files found.")

    if not csv_files:
        print("\n[NOTE] No raw FIRMS country CSVs found.")
        print("Please follow the manual download steps documented in docs/DATASETS.md:")
        print("1. Visit: https://firms.modaps.eosdis.nasa.gov/country/")
        print("2. Select Country: India")
        print("3. Download Yearly archives (2019-2025) for MODIS, VIIRS NOAA-20, and VIIRS S-NPP.")
        print(f"4. Place downloaded files in: {raw_dir.resolve()}\n")

    return indexed


def load_firms_year(file_path: Path) -> pd.DataFrame:
    """Read a FIRMS country yearly summary CSV with standardized columns."""
    df = pd.read_csv(file_path, low_memory=False)
    # Standardize column casing
    df.columns = [c.lower().strip() for c in df.columns]

    # Required columns: latitude, longitude, acq_date, acq_time, confidence, frp
    rename_map = {
        "latitude": "lat",
        "longitude": "lon",
        "brightness": "brightness",
        "bright_ti4": "brightness",
    }
    df = df.rename(columns=rename_map)
    df["acq_date"] = pd.to_datetime(df["acq_date"])
    return df


def main():
    parser = argparse.ArgumentParser(description="Index and verify FIRMS historical CSV datasets")
    parser.add_argument("--raw-dir", type=Path, default=RAW_FIRMS_DIR, help="Path to raw FIRMS CSV directory")
    args = parser.parse_args()

    indexed = verify_and_index_firms_history(args.raw_dir)
    print("FIRMS Historical indexing complete.")


if __name__ == "__main__":
    main()
