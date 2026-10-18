"""Spatial join fires to districts and derive binary daily wildfire ground-truth labels."""

import argparse
from pathlib import Path
import geopandas as gpd
import pandas as pd
from shapely.geometry import Point

RAW_FIRMS_DIR = Path("data/raw/firms")
OUTPUT_LABELS_PATH = Path("data/processed/fire_labels_daily.parquet")


def is_nominal_or_high_confidence(row: pd.Series) -> bool:
    conf = str(row.get("confidence", "")).lower().strip()
    # VIIRS format: 'n' (nominal), 'h' (high), 'l' (low)
    if conf in ["n", "h", "nominal", "high"]:
        return True
    # MODIS format: 0 to 100 percentage
    try:
        conf_num = float(conf)
        return conf_num >= 30.0
    except (ValueError, TypeError):
        pass
    return False


def is_vegetation_landcover(row: pd.Series) -> bool:
    lc = str(row.get("landcover_class", "tree")).lower().strip()
    return lc in ["tree", "trees", "shrub", "shrubland", "grass", "grassland", "forest", "vegetation"]


def process_fire_labels(
    firms_df: pd.DataFrame, districts_gdf: gpd.GeoDataFrame
) -> pd.DataFrame:
    print(f"Creating spatial points for {len(firms_df)} fire detections...")
    geometry = [Point(xy) for xy in zip(firms_df["lon"], firms_df["lat"])]
    fires_gdf = gpd.GeoDataFrame(firms_df, geometry=geometry, crs="EPSG:4326")

    print("Performing spatial join with district geometries...")
    # sjoin points within district polygons
    joined = gpd.sjoin(fires_gdf, districts_gdf[["district_id", "state_name", "district_name", "geometry"]], how="inner", predicate="within")

    print(f"Joined {len(joined)} detections within district boundaries.")

    joined["is_confident"] = joined.apply(is_nominal_or_high_confidence, axis=1)
    joined["is_vegetation"] = joined.apply(is_vegetation_landcover, axis=1)

    # Core target label definition from section 6
    joined["wildfire_positive"] = joined["is_confident"] & joined["is_vegetation"]

    # Aggregate by district and day
    joined["date"] = pd.to_datetime(joined["acq_date"]).dt.date

    daily_labels = joined.groupby(["district_id", "date"]).agg(
        wildfire_label=("wildfire_positive", lambda x: int(any(x))),
        any_fire_label=("is_confident", lambda x: int(any(x))),
        fire_count=("lat", "count"),
        vegetation_fire_count=("wildfire_positive", "sum"),
        max_frp=("frp", "max"),
        total_frp=("frp", "sum"),
    ).reset_index()

    print(f"Aggregated into {len(daily_labels)} district-day fire events.")
    print(f"Wildfire positive days: {daily_labels['wildfire_label'].sum()} ({daily_labels['wildfire_label'].mean():.2%})")
    print(f"Any fire positive days: {daily_labels['any_fire_label'].sum()} ({daily_labels['any_fire_label'].mean():.2%})")

    return daily_labels


def main():
    parser = argparse.ArgumentParser(description="Build daily district wildfire ground truth labels")
    parser.add_argument("--firms-csv", type=Path, help="Path to combined FIRMS CSV")
    parser.add_argument("--districts-geojson", type=Path, help="Path to districts GeoJSON")
    parser.add_argument("--output", type=Path, default=OUTPUT_LABELS_PATH)

    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    print("Label generation module configured.")


if __name__ == "__main__":
    main()
