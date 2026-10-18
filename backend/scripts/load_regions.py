import argparse
import asyncio
import json
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import text

from app.core.logging import logger
from app.db.session import async_session_factory

GADM_INDIA_URL = "https://geodata.ucdavis.edu/gadm/gadm4.1/json/gadm41_IND_2.json"


def download_gadm_india(target_path: Path) -> Path:
    """Download GADM 4.1 India level 2 GeoJSON if not present."""
    target_path.parent.mkdir(parents=True, exist_ok=True)
    if target_path.exists() and target_path.stat().st_size > 1000:
        logger.info("gadm_file_already_exists", path=str(target_path))
        return target_path

    logger.info("downloading_gadm_india_level_2", url=GADM_INDIA_URL, target=str(target_path))
    urllib.request.urlretrieve(GADM_INDIA_URL, target_path)
    logger.info("download_complete", path=str(target_path), size_bytes=target_path.stat().st_size)
    return target_path


async def load_geojson_districts(
    geojson_path: Path, country_code: str = "IN", timezone: str = "Asia/Kolkata"
) -> int:
    if not geojson_path.exists():
        logger.error("file_not_found", path=str(geojson_path))
        raise FileNotFoundError(f"GADM GeoJSON not found at: {geojson_path}")

    with open(geojson_path, encoding="utf-8") as f:
        data = json.load(f)

    features = data.get("features", [])
    if not features:
        raise ValueError(f"No features found in {geojson_path}")

    logger.info("loading_districts", count=len(features), country=country_code)

    loaded = 0
    async with async_session_factory() as session:
        for idx, feat in enumerate(features):
            props = feat.get("properties", {})
            geom = feat.get("geometry", {})

            # GADM properties
            gadm_id = props.get("GID_2")
            if not gadm_id:
                raise ValueError(
                    f"Feature at index {idx} missing GID_2 identifier. Refusing to invent synthetic IDs."
                )

            district_name = props.get("NAME_2") or props.get("district")
            if not district_name:
                raise ValueError(f"Feature {gadm_id} missing NAME_2 property.")

            state_name = props.get("NAME_1") or props.get("state") or "Unknown State"

            geom_json_str = json.dumps(geom)

            # Insert with PostGIS ST_GeomFromGeoJSON, ST_Centroid, and ST_Area
            sql = text(
                """
                INSERT INTO wf.regions (
                    country_code, admin_level, state_name, district_name, gadm_id,
                    geom, centroid, area_km2, landcover, timezone
                ) VALUES (
                    :country_code, 2, :state_name, :district_name, :gadm_id,
                    ST_Multi(ST_SetSRID(ST_GeomFromGeoJSON(:geom_json), 4326)),
                    ST_Centroid(ST_SetSRID(ST_GeomFromGeoJSON(:geom_json), 4326)),
                    ST_Area(ST_Transform(ST_SetSRID(ST_GeomFromGeoJSON(:geom_json), 4326), 3857)) / 1000000.0,
                    '{}'::jsonb,
                    :timezone
                )
                ON CONFLICT (gadm_id) DO UPDATE SET
                    state_name = EXCLUDED.state_name,
                    district_name = EXCLUDED.district_name,
                    geom = EXCLUDED.geom,
                    centroid = EXCLUDED.centroid,
                    area_km2 = EXCLUDED.area_km2,
                    timezone = EXCLUDED.timezone;
                """
            )
            await session.execute(
                sql,
                {
                    "country_code": country_code,
                    "state_name": state_name,
                    "district_name": district_name,
                    "gadm_id": gadm_id,
                    "geom_json": geom_json_str,
                    "timezone": timezone,
                },
            )
            loaded += 1

        await session.commit()

    logger.info("districts_loaded_successfully", total=loaded)
    return loaded


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Load GADM 4.1 India level 2 district boundaries into wf.regions"
    )
    parser.add_argument(
        "--file",
        "-f",
        type=Path,
        default=Path("data/raw/gadm41_IND_2.json"),
        help="Path to GADM GeoJSON file (default: data/raw/gadm41_IND_2.json)",
    )
    parser.add_argument(
        "--download",
        action="store_true",
        help="Download GADM 4.1 India level 2 file if missing",
    )
    parser.add_argument(
        "--country",
        "-c",
        type=str,
        default="IN",
        help="Country ISO code (default: IN)",
    )
    parser.add_argument(
        "--timezone",
        type=str,
        default="Asia/Kolkata",
        help="Timezone for region (default: Asia/Kolkata)",
    )

    args = parser.parse_args()

    geojson_path = args.file
    if args.download or not geojson_path.exists():
        if args.download:
            geojson_path = download_gadm_india(geojson_path)
        else:
            sys.stderr.write(
                f"Error: File {geojson_path} not found. Pass --download to automatically fetch GADM 4.1 data.\n"
            )
            sys.exit(1)

    count = asyncio.run(load_geojson_districts(geojson_path, args.country, args.timezone))
    print(f"Loaded {count} districts.")


if __name__ == "__main__":
    main()
