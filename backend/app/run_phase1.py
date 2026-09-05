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
    logger.info("==================================================")
    logger.info("  PHASE 1: DISASTER DATA COLLECTION & NORMALIZATION")
    logger.info("==================================================")

    # Step 1: Initialize Database Tables
    logger.info("1. Initializing database schema...")
    await init_db()

    # Step 2: Execute Collector Services
    manager = CollectorManager()
    async with AsyncSessionLocal() as session:
        logger.info("2. Running collectors (2 Real: RSS + News, 2 Mock: Gov + Social)...")
        summary = await manager.run_all_collectors(session)
        
        logger.info("--------------------------------------------------")
        logger.info(f"Ingestion Result Summary:")
        logger.info(f"  - Total Collected: {summary['total_collected']}")
        logger.info(f"  - Saved to DB: {summary['saved_to_db']}")
        logger.info(f"  - Duplicates Skipped: {summary['duplicates_skipped']}")
        logger.info(f"  - Breakout by Source Type:")
        for stype, count in summary['counts_by_source_type'].items():
            logger.info(f"      * {stype}: {count} items")
        logger.info("--------------------------------------------------")

        # Step 3: Query and Inspect DB Records to Verify Schema
        logger.info("3. Verifying database records...")
        stmt = select(RawDisasterItemModel).order_by(RawDisasterItemModel.timestamp.desc())
        result = await session.execute(stmt)
        stored_items = result.scalars().all()

        logger.info(f"Retrieved {len(stored_items)} raw items from database:")
        for idx, item in enumerate(stored_items[:10], start=1):
            logger.info(f"  [{idx}] Source: {item.source} ({item.source_type})")
            logger.info(f"      Title: {item.title}")
            logger.info(f"      Location: {item.location_name} (Lat: {item.latitude}, Lon: {item.longitude})")
            logger.info(f"      Timestamp: {item.timestamp}")
            logger.info(f"      URL: {item.url}")
            logger.info(f"      Metadata Keys: {list(item.raw_metadata.keys()) if item.raw_metadata else []}")
            logger.info("      " + "-"*40)

        assert len(stored_items) > 0, "Database should contain ingested disaster items!"
        logger.info("SUCCESS: Phase 1 execution completed and verified!")

if __name__ == "__main__":
    asyncio.run(main())
