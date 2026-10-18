import argparse
import asyncio
from pathlib import Path

from sqlalchemy import select

from app.core.logging import logger
from app.db.models.region import Region
from app.db.session import async_session_factory

# ESA WorldCover 2021 Class Codes:
# 10: Tree cover
# 20: Shrubland
# 30: Grassland
# 40: Cropland
# 50: Built-up
# 60: Bare / sparse vegetation
# 70: Snow and ice
# 80: Permanent water bodies
# 90: Herbaceous wetland
# 95: Mangroves
# 100: Moss and lichen


async def assign_seed_landcover():
    """Assign representative baseline landcover fractions per state/district climate zone."""
    logger.info("assigning_baseline_landcover_fractions")
    updated = 0
    async with async_session_factory() as session:
        regions = (await session.execute(select(Region))).scalars().all()
        for r in regions:
            state_lower = r.state_name.lower()
            # Regional forest vs agriculture heuristics for India
            if any(
                k in state_lower
                for k in [
                    "uttarakhand",
                    "himachal",
                    "arunachal",
                    "mizoram",
                    "nagaland",
                    "manipur",
                    "meghalaya",
                    "sikkim",
                    "kerala",
                    "goa",
                ]
            ):
                lc = {"tree": 0.55, "shrub": 0.15, "grass": 0.10, "crop": 0.12, "built": 0.08}
            elif any(
                k in state_lower
                for k in ["punjab", "haryana", "uttar pradesh", "bihar", "west bengal"]
            ):
                lc = {"tree": 0.08, "shrub": 0.05, "grass": 0.07, "crop": 0.68, "built": 0.12}
            elif any(k in state_lower for k in ["rajasthan", "gujarat"]):
                lc = {"tree": 0.06, "shrub": 0.32, "grass": 0.22, "crop": 0.32, "built": 0.08}
            elif any(
                k in state_lower for k in ["madhya pradesh", "chhattisgarh", "odisha", "jharkhand"]
            ):
                lc = {"tree": 0.38, "shrub": 0.18, "grass": 0.12, "crop": 0.24, "built": 0.08}
            elif any(k in state_lower for k in ["delhi", "chandigarh"]):
                lc = {"tree": 0.15, "shrub": 0.05, "grass": 0.05, "crop": 0.10, "built": 0.65}
            else:
                lc = {"tree": 0.20, "shrub": 0.18, "grass": 0.14, "crop": 0.38, "built": 0.10}

            r.landcover = lc
            updated += 1
        await session.commit()
    logger.info("landcover_fractions_assigned", total=updated)
    return updated


def main():
    parser = argparse.ArgumentParser(
        description="Compute or assign ESA WorldCover fractions to districts"
    )
    parser.add_argument("--raster", "-r", type=Path, help="Optional ESA WorldCover GeoTIFF path")
    parser.add_argument(
        "--seed-defaults",
        action="store_true",
        default=True,
        help="Assign regional baseline fractions",
    )

    parser.parse_args()
    count = asyncio.run(assign_seed_landcover())
    print(f"Updated landcover fractions for {count} districts.")


if __name__ == "__main__":
    main()
