"""Write the serving coverage file of AQI model B: training stations and, for every district,
the forecast point (district centroid as used in training), distance to the nearest training
station, convex-hull membership and the `extrapolated` flag (app.domain.model_coverage).

Inputs: stations.csv of the dataset the model was trained on (build_aqi_station_dataset.py),
regions_centroids.csv (region_id, district, state, lat, lon: the centroids the training rows and
the weather/CAMS downloads used), GADM 4.1 level 2 (gadm_id of region_id = feature index + 1).

    python ml/pipeline/build_aqi_station_coverage.py --stations data/processed/aqi_station/stations.csv \
        --regions regions_centroids.csv --gadm gadm41_IND_2.json \
        --model-version aqi_station_xgb_v3 --out backend/models/aqi_station_xgb_v3/coverage.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

BACKEND = Path(__file__).resolve().parents[2] / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.domain.model_coverage import (  # noqa: E402
    EXTRAPOLATION_KM,
    extrapolated,
    inside_hull,
    nearest_km,
)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--stations", type=Path, required=True)
    ap.add_argument("--regions", type=Path, required=True)
    ap.add_argument("--gadm", type=Path, required=True)
    ap.add_argument("--model-version", required=True)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()

    st = pd.read_csv(args.stations).sort_values("station_id")
    # Parsed exactly as build_aqi_station_dataset.py parses them: these floats are the lat/lon
    # model inputs and (formatted to 4 decimals) the point CAMS and weather are requested for.
    reg = pd.read_csv(args.regions).sort_values("region_id")
    feats = json.loads(args.gadm.read_text())["features"]
    lat, lon = reg["lat"], reg["lon"]
    near = nearest_km(lat, lon, st["lat"], st["lon"])
    hull = inside_hull(lat, lon, st["lat"], st["lon"])

    districts = []
    for i, r in enumerate(reg.itertuples()):
        pr = feats[int(r.region_id) - 1]["properties"]
        if (pr["NAME_1"], pr["NAME_2"]) != (r.state, r.district):
            raise ValueError(f"region {r.region_id} does not match GADM {pr['GID_2']}")
        districts.append(
            {
                "region_id": int(r.region_id),
                "gadm_id": pr["GID_2"],
                "lat": float(r.lat),
                "lon": float(r.lon),
                "has_training_station": bool((st["region_id"] == r.region_id).any()),
                "nearest_training_station_km": round(float(near[i]), 1),
                "inside_station_hull": hull[i],
                "extrapolated": extrapolated(float(near[i]), hull[i]),
            }
        )
    out = {
        "model_version": args.model_version,
        "rule": f"extrapolated = nearest training station > {EXTRAPOLATION_KM:g} km "
        "OR centroid outside the convex hull of the training stations",
        "stations": [
            {
                "station_id": int(s.station_id),
                "region_id": int(s.region_id),
                "lat": float(s.lat),
                "lon": float(s.lon),
            }
            for s in st.itertuples()
        ],
        "districts": districts,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(out, indent=1) + "\n")
    print(
        json.dumps(
            {
                "districts": len(districts),
                "stations": len(out["stations"]),
                "extrapolated": sum(d["extrapolated"] for d in districts),
                "outside_hull": sum(not d["inside_station_hull"] for d in districts),
                f"gt_{EXTRAPOLATION_KM:g}km": int((near > EXTRAPOLATION_KM).sum()),
            }
        )
    )


if __name__ == "__main__":
    main()
