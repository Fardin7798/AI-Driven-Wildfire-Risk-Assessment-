import json
import os

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.preparedness import PreparednessItem


async def get_preparedness_items(
    session: AsyncSession,
    hazard: str | None = None,
    stage: str | None = None,
    audience: str | None = None,
    lang: str = "en",
) -> list[PreparednessItem]:
    query = select(PreparednessItem).where(PreparednessItem.lang == lang)
    if hazard:
        query = query.where(PreparednessItem.hazard == hazard.lower().strip())
    if stage:
        query = query.where(PreparednessItem.stage == stage.lower().strip())
    if audience:
        query = query.where(PreparednessItem.audience == audience.lower().strip())

    result = await session.execute(query)
    items = list(result.scalars().all())

    # If empty, attempt to load from seed JSON
    if not items:
        seed_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
            "data",
            "seed",
            "preparedness.json",
        )
        if os.path.exists(seed_path):
            with open(seed_path, encoding="utf-8") as f:
                seed_data = json.load(f)
            for item in seed_data:
                p_item = PreparednessItem(
                    hazard=item["hazard"],
                    stage=item["stage"],
                    audience=item["audience"],
                    title=item["title"],
                    body=item["body"],
                    source_url=item["source_url"],
                    lang=item.get("lang", "en"),
                )
                session.add(p_item)
            await session.commit()

            # Re-query
            result = await session.execute(query)
            items = list(result.scalars().all())

    return items
