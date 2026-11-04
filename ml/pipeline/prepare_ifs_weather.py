"""Convert the ECMWF IFS HRES 9 km daily archive into the weather schema the wildfire builder reads.

Live serving takes weather from Open-Meteo (ECMWF IFS), so training on the same model removes the
NASA POWER -> IFS input shift. The IFS archive (one row per region_id x local day) is produced
by the IFS extraction (Open-Meteo AWS archive, model ecmwf_ifs, local day 19:00-19:00 UTC).

Input:
  --ifs        ifs_daily_<start>_<end>.parquet  keyed region_id, date
  --cells      ifs_served_cells.csv             region_id, district, state, centroid_lat, centroid_lon
  --gadm       GADM 4.1 level-2 GeoJSON          (GID_2, the builder's district id)
Output:
  --out        parquet with the builder's schema:
               gadm_id, date, temp_max, temp_mean, rh_mean, wind_max, precip_sum

Column mapping (units already match the live Open-Meteo provider):
  temperature_2m_max        -> temp_max    (deg C)
  temperature_2m_mean       -> temp_mean   (deg C)
  relative_humidity_2m_mean -> rh_mean     (%)
  wind_speed_10m_max        -> wind_max    (km/h)
  precipitation_sum         -> precip_sum  (mm/day)

region_id -> GID_2: the GADM geometry.centroid (the same call the builder uses for lat/lon) must
equal the cell's centroid_lat/lon to within 4-decimal rounding, uniquely, AND the GID_2 must be
one of the GADM districts whose NAME_2/NAME_1 (spaces removed) equal district/state. Any region
that fails either check aborts the run; nothing is guessed. Missing values stay NaN; days with
nan_hours_any > 0 are kept as they are and counted (the builder skips a day whose FWI inputs are
missing).
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
from scipy.spatial import cKDTree

MAPPING = {
    "temperature_2m_max": "temp_max",
    "temperature_2m_mean": "temp_mean",
    "relative_humidity_2m_mean": "rh_mean",
    "wind_speed_10m_max": "wind_max",
    "precipitation_sum": "precip_sum",
}
MAX_CENTROID_DIST_DEG = 1e-4  # 4-decimal rounding of both coordinates: <= 7.1e-5


def region_to_gid(cells: pd.DataFrame, gadm: gpd.GeoDataFrame) -> pd.DataFrame:
    cent = gadm.geometry.centroid
    tree = cKDTree(np.c_[cent.y.values, cent.x.values])
    dist, idx = tree.query(np.c_[cells["centroid_lat"].values, cells["centroid_lon"].values])
    out = cells[["region_id", "district", "state"]].copy()
    out["gadm_id"] = gadm["GID_2"].values[idx]
    out["centroid_dist_deg"] = dist
    name_key = gadm["NAME_2"].str.replace(" ", "") + "|" + gadm["NAME_1"].str.replace(" ", "")
    gid_by_name = pd.Series(gadm["GID_2"].values).groupby(name_key.values).agg(set)
    cell_key = out["district"].str.replace(" ", "") + "|" + out["state"].str.replace(" ", "")
    out["name_ok"] = [
        gid in gid_by_name.get(k, set()) for gid, k in zip(out["gadm_id"], cell_key, strict=True)
    ]
    bad = out[(out["centroid_dist_deg"] > MAX_CENTROID_DIST_DEG) | ~out["name_ok"]]
    if len(bad) or out["gadm_id"].duplicated().any():
        raise SystemExit(f"region_id -> GID_2 mapping failed:\n{bad.to_string()}")
    return out


def main() -> None:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("--ifs", type=Path, required=True)
    ap.add_argument("--cells", type=Path, required=True)
    ap.add_argument("--gadm", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()

    gadm = gpd.read_file(args.gadm)
    cells = pd.read_csv(args.cells)
    mapping = region_to_gid(cells, gadm)
    if len(mapping) != len(gadm):
        raise SystemExit(f"{len(mapping)} IFS regions vs {len(gadm)} GADM districts")

    ifs = pd.read_parquet(args.ifs, columns=["region_id", "date", "nan_hours_any", *MAPPING])
    if ifs.duplicated(["region_id", "date"]).any():
        raise SystemExit("duplicate region_id x date rows in IFS archive")
    unknown = set(ifs["region_id"]) - set(mapping["region_id"])
    if unknown:
        raise SystemExit(f"IFS region_ids without a mapping: {sorted(unknown)[:10]}")
    out = ifs.merge(mapping[["region_id", "gadm_id"]], on="region_id", how="left")
    out = out.rename(columns=MAPPING)
    out["date"] = pd.to_datetime(out["date"]).dt.date
    cols = ["gadm_id", "date", *MAPPING.values()]
    stats = {
        "rows": int(len(out)),
        "districts": int(out["gadm_id"].nunique()),
        "date_min": str(out["date"].min()),
        "date_max": str(out["date"].max()),
        "nan_per_column": {c: int(out[c].isna().sum()) for c in MAPPING.values()},
        "days_with_nan_hours": int((out["nan_hours_any"] > 0).sum()),
    }
    out = out[cols].sort_values(["gadm_id", "date"]).reset_index(drop=True)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    out.to_parquet(args.out, index=False)
    mapping.to_csv(args.out.with_name(args.out.stem + "_region_map.csv"), index=False)
    print(json.dumps(stats, indent=1))


if __name__ == "__main__":
    main()
