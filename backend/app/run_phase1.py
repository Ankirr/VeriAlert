import asyncio
import logging
import sys
from pathlib import Path

# Add backend root directory to sys.path
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from sqlalchemy import select
from app.db.database import init_db, AsyncSessionLocal
from app.db.models import RawDisasterItemModel
from app.collectors.collector_manager import CollectorManager

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("Phase1Runner")

async def main():
    logger.info("=" * 65)
    logger.info("  PHASE 1: MULTI-SOURCE DISASTER DATA INGESTION & NORMALIZATION")
    logger.info("=" * 65)

    # Step 1: Initialize Database Tables
    logger.info("1. Initializing database schema...")
    await init_db()

    # Step 2: Execute Collector Services
    manager = CollectorManager()
    async with AsyncSessionLocal() as session:
        logger.info("2. Executing 5 Modular Collectors...")
        logger.info("   a) NewsAPI (Live with API key)")
        logger.info("   b) GDELT (Live free news backup/supplement)")
        logger.info("   c) Reddit (PRAW with graceful mock fallback)")
        logger.info("   d) IMD RSS (Official weather bulletins labeled MOCK)")
        logger.info("   e) NDMA Sachet (Official disaster alerts labeled MOCK)")

        summary = await manager.run_all_collectors(session)
        
        logger.info("-" * 65)
        logger.info("Ingestion Result Summary:")
        logger.info(f"  - Total Collected:    {summary['total_collected']}")
        logger.info(f"  - Saved to DB:        {summary['saved_to_db']}")
        logger.info(f"  - Duplicates Skipped: {summary['duplicates_skipped']}")
        logger.info("  - Breakdown by Collector Source:")
        for col, count in summary.get('counts_by_collector', {}).items():
            logger.info(f"      * {col:<24}: {count} items")
        logger.info("  - Breakdown by Source Type:")
        for stype, count in summary.get('counts_by_source_type', {}).items():
            logger.info(f"      * {stype:<12}: {count} items")
        logger.info("-" * 65)

        # Step 3: Query and Inspect DB Records to Verify Schema
        logger.info("3. Querying stored database records to verify unified schema...")
        stmt = select(RawDisasterItemModel).order_by(RawDisasterItemModel.is_mock.asc(), RawDisasterItemModel.timestamp.desc())
        result = await session.execute(stmt)
        stored_items = result.scalars().all()

        real_count = sum(1 for item in stored_items if not item.is_mock)
        mock_count = sum(1 for item in stored_items if item.is_mock)

        logger.info(f"Total Stored in Database: {len(stored_items)} (Real: {real_count}, Mock: {mock_count})")
        logger.info("\n" + "=" * 65)
        logger.info("  SAMPLE OF 10 STORED DISASTER ITEMS (UNIFIED 8-FIELD SCHEMA)")
        logger.info("=" * 65)

        for idx, item in enumerate(stored_items[:10], start=1):
            mock_flag = "[MOCK]" if item.is_mock else "[REAL]"
            print(f"\n--- Item #{idx} {mock_flag} ---")
            print(f"  ID:            {item.id}")
            print(f"  Source:        {item.source}")
            print(f"  Source Type:   {item.source_type}")
            print(f"  Timestamp:     {item.timestamp}")
            print(f"  Location Text: {item.location_text or '(None - to be enriched in Phase 3)'}")
            print(f"  URL:           {item.url}")
            print(f"  Is Mock:       {item.is_mock}")
            raw_preview = item.raw_text.replace('\n', ' ')[:140]
            print(f"  Raw Text:      {raw_preview}...")

        assert len(stored_items) > 0, "Database should contain ingested disaster items!"
        logger.info("\n" + "=" * 65)
        logger.info("SUCCESS: Phase 1 execution completed and verified!")
        logger.info("=" * 65)

if __name__ == "__main__":
    asyncio.run(main())
