import logging
import asyncio
from typing import List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.collectors.news_api import NewsAPICollector
from app.collectors.rss_feed import RegionalRSSCollector
from app.collectors.gdelt_collector import GDELTCollector
from app.collectors.reddit_collector import RedditCollector
from app.collectors.mock_rss_collector import MockRSSCollector
from app.collectors.mock_ndma_collector import MockNDMACollector
from app.models.schemas import NormalizedDisasterItem
from app.db.models import RawDisasterItemModel

logger = logging.getLogger(__name__)

class CollectorManager:
    """
    Orchestrates the ingestion sources:
    1. NewsAPI (live domestic & regional disasters in India/subcontinent)
    2. Regional Indian News RSS (live NDTV Cities, TOI, The Hindu localized alerts)
    3. GDELT (live supplementary news with timeout fallback)
    4. Reddit (PRAW with graceful mock fallback)
    5. IMD RSS (official weather bulletins labeled MOCK)
    6. NDMA Sachet (official alerts labeled MOCK)
    """
    def __init__(self):
        self.collectors = [
            NewsAPICollector(),
            RegionalRSSCollector(),
            GDELTCollector(),
            RedditCollector(),
            MockRSSCollector(),
            MockNDMACollector(),
        ]

    async def run_all_collectors(self, db_session: AsyncSession) -> Dict[str, Any]:
        """Runs all collectors concurrently and stores validated normalized records in the DB."""
        logger.info(f"Initializing ingestion across all {len(self.collectors)} collector services...")
        
        # Execute collectors in parallel with error isolation
        tasks = [collector.fetch_with_retry() for collector in self.collectors]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        all_items: List[NormalizedDisasterItem] = []
        source_counts: Dict[str, int] = {}
        collector_counts: Dict[str, int] = {}

        for collector, result in zip(self.collectors, results):
            if isinstance(result, Exception):
                logger.error(f"[{collector.source_name}] Collector encountered error: {result}")
                collector_counts[collector.source_name] = 0
                continue
            
            items: List[NormalizedDisasterItem] = result or []
            collector_counts[collector.source_name] = len(items)
            
            for item in items:
                all_items.append(item)
                source_counts[item.source_type] = source_counts.get(item.source_type, 0) + 1

        # Persist normalized items into database with URL deduplication
        saved_count = 0
        duplicate_count = 0

        for item in all_items:
            # Prevent duplicate URLs
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
                location_text=item.location_text,
                raw_text=item.raw_text,
                title=item.title,
                url=item.url,
                is_mock=item.is_mock,
                latitude=item.latitude,
                longitude=item.longitude,
                raw_metadata=item.raw_metadata
            )
            db_session.add(db_model)
            saved_count += 1

        await db_session.commit()

        summary = {
            "total_collected": len(all_items),
            "saved_to_db": saved_count,
            "duplicates_skipped": duplicate_count,
            "counts_by_source_type": source_counts,
            "counts_by_collector": collector_counts
        }
        logger.info(f"Ingestion complete! Summary: {summary}")
        return summary
