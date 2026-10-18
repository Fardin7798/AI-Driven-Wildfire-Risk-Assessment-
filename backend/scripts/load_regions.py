import argparse
import asyncio
import json
from pathlib import Path

from sqlalchemy import text

from app.core.logging import logger
from app.db.session import async_session_factory


async def load_geojson_districts(geojson_path: Path, country_code: str = "IN") -> int:
    if not geojson_path.exists():
        logger.error("file_not_found", path=str(geojson_path))
        return 0

    with open(geojson_path, encoding="utf-8") as f:
        data = json.load(f)

    features = data.get("features", [])
    logger.info("loading_districts", count=len(features), country=country_code)

    loaded = 0
    async with async_session_factory() as session:
        for idx, feat in enumerate(features):
            props = feat.get("properties", {})
            geom = feat.get("geometry", {})

            # GADM properties or standard GeoJSON
            district_name = (
                props.get("NAME_2")
                or props.get("district")
                or props.get("dtname")
                or props.get("name")
                or f"District_{idx}"
            )
            state_name = (
                props.get("NAME_1") or props.get("state") or props.get("stname") or "Unknown State"
            )
            gadm_id = (
                props.get("GID_2")
                or props.get("gadm_id")
                or f"{country_code}.{state_name.replace(' ', '')}.{district_name.replace(' ', '')}"
            )

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
                    'Asia/Kolkata'
                )
                ON CONFLICT (gadm_id) DO UPDATE SET
                    state_name = EXCLUDED.state_name,
                    district_name = EXCLUDED.district_name,
                    geom = EXCLUDED.geom,
                    centroid = EXCLUDED.centroid,
                    area_km2 = EXCLUDED.area_km2;
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
                },
            )
            loaded += 1

        await session.commit()

    logger.info("districts_loaded_successfully", total=loaded)
    return loaded


def main():
    parser = argparse.ArgumentParser(
        description="Load GADM/GeoJSON district boundaries into wf.regions"
    )
    parser.add_argument("--file", "-f", type=Path, required=True, help="Path to GADM GeoJSON file")
    parser.add_argument(
        "--country", "-c", type=str, default="IN", help="Country ISO code (default: IN)"
    )

    args = parser.parse_args()
    count = asyncio.run(load_geojson_districts(args.file, args.country))
    print(f"Loaded {count} districts.")


if __name__ == "__main__":
    main()
