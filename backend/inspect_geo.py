import asyncio
from sqlalchemy import select
from app.db.database import AsyncSessionLocal
from app.db.models import RawDisasterItemModel, DisasterClusterModel

async def main():
    async with AsyncSessionLocal() as session:
        res = await session.execute(select(DisasterClusterModel))
        clusters = res.scalars().all()
        lines = []
        lines.append(f"=== TOTAL CLUSTERS: {len(clusters)} ===")
        for c in clusters:
            lines.append(f"Cluster: '{c.event_name[:55]}' | Type: {c.disaster_type} | Loc: '{c.location_name}' | ({c.latitude}, {c.longitude}) | Reports: {len(c.item_ids)}")

        lines.append("\n=== RAW ITEMS ===")
        res = await session.execute(select(RawDisasterItemModel))
        items = res.scalars().all()
        for i, it in enumerate(items, 1):
            meta = it.raw_metadata or {}
            geo_info = meta.get("geo_resolution", {})
            loc_primary = geo_info.get("primary_location") or it.location_text
            lines.append(f"{i:2d}. Title: '{it.title[:55]}' | Loc: '{loc_primary}' | ({it.latitude}, {it.longitude})")

        with open("geo_inspection_report.txt", "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
        print("Inspection saved to geo_inspection_report.txt successfully.")

if __name__ == "__main__":
    asyncio.run(main())
