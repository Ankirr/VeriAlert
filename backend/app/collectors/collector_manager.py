import logging
import asyncio
from typing import List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.collectors.rss_feed import RSSFeedCollector
from app.collectors.news_api import NewsAPICollector
from app.collectors.real_gov_alert import RealGovAlertCollector
from app.collectors.real_social_media import RealSocialMediaCollector
from app.models.schemas import NormalizedDisasterItem
from app.db.models import RawDisasterItemModel

logger = logging.getLogger(__name__)

class CollectorManager:
    def __init__(self):
        self.collectors = [
            RSSFeedCollector(),
            NewsAPICollector(),
            RealGovAlertCollector(),
            RealSocialMediaCollector()
        ]

    async def run_all_collectors(self, db_session: AsyncSession) -> Dict[str, Any]:
        """Runs all 4 collectors concurrently and saves normalized records to Postgres/DB."""
        logger.info("Initializing ingestion across all 4 collector services...")
        
        # Execute collectors in parallel using asyncio.gather
        tasks = [collector.fetch_with_retry() for collector in self.collectors]
        results: List[List[NormalizedDisasterItem]] = await asyncio.gather(*tasks)

        all_items: List[NormalizedDisasterItem] = []
        source_counts: Dict[str, int] = {}

        for items in results:
            for item in items:
                all_items.append(item)
                source_counts[item.source_type] = source_counts.get(item.source_type, 0) + 1

        # Persist normalized items into database
        saved_count = 0
        duplicate_count = 0

        for item in all_items:
            # Simple URL deduplication check
            if item.url:
                stmt = select(RawDisasterItemModel).where(RawDisasterItemModel.url == item.url)
                existing = await db_session.execute(stmt)
                if existing.scalar_one_or_none():
                    duplicate_count += 1
                    continue

            db_model = RawDisasterItemModel(
                id=item.id,
                source=item.source,
                source_type=item.source_type,
                timestamp=item.timestamp,
                location_name=item.location_name,
                latitude=item.latitude,
                longitude=item.longitude,
                raw_text=item.raw_text,
                title=item.title,
                url=item.url,
                raw_metadata=item.raw_metadata
            )
            db_session.add(db_model)
            saved_count += 1

        await db_session.commit()

        summary = {
            "total_collected": len(all_items),
            "saved_to_db": saved_count,
            "duplicates_skipped": duplicate_count,
            "counts_by_source_type": source_counts
        }
        logger.info(f"Ingestion complete! Summary: {summary}")
        return summary
