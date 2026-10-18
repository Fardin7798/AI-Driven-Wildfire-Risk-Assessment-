import argparse
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import sys
from typing import Any

import numpy as np
import rasterio
from geoalchemy2.shape import to_shape
from rasterio.mask import mask
from shapely.geometry import box, mapping
from sqlalchemy import select

from app.core.logging import logger
from app.db.models.region import Region
from app.db.session import async_session_factory

# ESA WorldCover 2021 Class Codes:
ESA_CLASSES = {
    10: "tree",
    20: "shrub",
    30: "grass",
    40: "crop",
    50: "built",
    60: "bare",
    70: "snow_ice",
    80: "water",
    90: "wetland",
    95: "mangroves",
    100: "moss_lichen",
}


def compute_zonal_fractions(
    poly: Any,
    raster_paths: list[Path],
) -> dict[str, float] | None:
    """Compute exact landcover fractions for a polygon across one or more ESA WorldCover GeoTIFFs."""
    poly_shape = to_shape(poly) if hasattr(poly, "geom_type") is False else poly
    geojson_geom = [mapping(poly_shape)]
    poly_box = box(*poly_shape.bounds)

    total_counts: dict[int, int] = dict.fromkeys(ESA_CLASSES, 0)
    total_valid = 0

    for rpath in raster_paths:
        try:
            with rasterio.open(rpath) as src:
                src_box = box(*src.bounds)
                if not poly_box.intersects(src_box):
                    continue
                try:
                    out_image, _ = mask(src, geojson_geom, crop=True, nodata=0)
                except ValueError:
                    # Geometry outside this tile bounds
                    continue

                valid = out_image[out_image > 0]
                if valid.size == 0:
                    continue

                total_valid += int(valid.size)
                unique, counts = np.unique(valid, return_counts=True)
                for u, c in zip(unique, counts, strict=False):
                    u_int = int(u)
                    if u_int in total_counts:
                        total_counts[u_int] += int(c)
                    else:
                        total_counts[u_int] = int(c)
        except Exception as exc:
            logger.warning("raster_read_error", path=str(rpath), error=str(exc))

    if total_valid == 0:
        return None

    return {
        ESA_CLASSES.get(k, f"class_{k}"): round(total_counts[k] / total_valid, 4)
        for k in sorted(total_counts.keys())
        if k in ESA_CLASSES
    }


async def process_landcover(raster_paths: list[Path]) -> int:
    """Compute and update wf.regions.landcover using real raster zonal stats."""
    logger.info("computing_landcover_zonal_stats", rasters_count=len(raster_paths))
    updated = 0
    async with async_session_factory() as session:
        result = await session.execute(select(Region).where(Region.geom.isnot(None)))
        regions = list(result.scalars().all())

        for r in regions:
            fractions = compute_zonal_fractions(r.geom, raster_paths)
            if fractions:
                r.landcover = fractions
                updated += 1
            else:
                logger.warning(
                    "no_raster_overlap_for_region",
                    gadm_id=r.gadm_id,
                    district=r.district_name,
                )

        await session.commit()

    logger.info("landcover_fractions_computed", updated=updated, total=len(regions))
    return updated


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Compute ESA WorldCover 2021 landcover fractions per district using rasterio zonal stats"
    )
    parser.add_argument(
        "--raster",
        "-r",
        type=Path,
        help="Path to ESA WorldCover GeoTIFF or VRT",
    )
    parser.add_argument(
        "--tiles-dir",
        "-d",
        type=Path,
        help="Directory containing ESA WorldCover 2021 GeoTIFF tiles",
    )

    args = parser.parse_args()

    raster_paths: list[Path] = []
    if args.raster and args.raster.exists():
        raster_paths.append(args.raster)
    elif args.tiles_dir and args.tiles_dir.exists():
        raster_paths.extend(args.tiles_dir.glob("*.tif"))
        raster_paths.extend(args.tiles_dir.glob("*.tiff"))

    if not raster_paths:
        sys.stderr.write(
            "Error: No ESA WorldCover raster provided or found.\n"
            "Please specify --raster <path_to_file.tif> or --tiles-dir <path_to_tiles/>.\n"
            "State-name heuristics have been removed; real raster data is required.\n"
        )
        sys.exit(1)

    updated = asyncio.run(process_landcover(raster_paths))
    print(f"Successfully computed and stored landcover for {updated} districts.")


if __name__ == "__main__":
    main()
