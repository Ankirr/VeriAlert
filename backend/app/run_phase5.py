"""
Phase 5 Pipeline Runner: Factual Public Alert Summarization using T5.
Generates concise 1-2 sentence emergency advisories for each incident cluster
and persists them into PostgreSQL.
"""
import asyncio
import logging
import sys
from pathlib import Path
from typing import List, Dict, Any

# Ensure stdout handles UTF-8 on Windows
if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Add backend directory to sys.path
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from sqlalchemy import select, update
from app.db.database import AsyncSessionLocal
from app.db.models import DisasterClusterModel, RawDisasterItemModel
from app.summarizer.alert_generator import FactualAlertSummarizer

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("Phase5Runner")

async def run_phase5_pipeline():
    logger.info("=" * 80)
    logger.info("  PHASE 5: FACTUAL PUBLIC ALERT SUMMARIZATION PIPELINE (T5 ON GPU)")
    logger.info("=" * 80)

    logger.info("1. Initializing T5-small Factual Alert Summarizer...")
    summarizer = FactualAlertSummarizer()

    async with AsyncSessionLocal() as session:
        # Fetch all clusters
        stmt = select(DisasterClusterModel).order_by(DisasterClusterModel.trust_score.desc())
        result = await session.execute(stmt)
        clusters = result.scalars().all()

        logger.info(f"Retrieved {len(clusters)} incident clusters from PostgreSQL.\n")

        # Fetch all raw items to map text to clusters
        items_stmt = select(RawDisasterItemModel)
        items_result = await session.execute(items_stmt)
        all_items = {it.id: it for it in items_result.scalars().all()}

        print("\n" + "=" * 120)
        print(f"{'#':<3} | {'INCIDENT NAME':<28} | {'LOCATION':<16} | {'VERACITY BAND':<24} | {'FACTUAL 1-2 SENTENCE PUBLIC ALERT'}")
        print("=" * 120)

        summarized_count = 0

        for idx, cluster in enumerate(clusters, 1):
            # Gather member texts
            member_texts = []
            for item_id in (cluster.item_ids or []):
                if item_id in all_items:
                    it = all_items[item_id]
                    t = f"{it.title or ''}. {it.raw_text}"
                    member_texts.append(t)

            # Generate factual 1-2 sentence alert summary
            summary = summarizer.generate_alert_summary(
                event_name=cluster.event_name,
                location_name=cluster.location_name,
                disaster_type=cluster.disaster_type,
                trust_band=cluster.trust_band,
                member_texts=member_texts
            )

            # Update cluster in database
            cluster.summary = summary
            summarized_count += 1

            # Print formatted row
            name_display = cluster.event_name[:28]
            loc_display = cluster.location_name[:16]
            band_display = cluster.trust_band[:24]
            alert_display = summary[:65] + "..." if len(summary) > 65 else summary

            print(f"{idx:<3} | {name_display:<28} | {loc_display:<16} | {band_display:<24} | {alert_display}")

        # Commit updates
        await session.commit()
        logger.info(f"\nAll {summarized_count} incident clusters updated with factual emergency summaries in PostgreSQL.")

    print("=" * 120)
    print("\n" + "=" * 65)
    print("  PHASE 5: PUBLIC ALERT SUMMARIZATION SUMMARY")
    print("=" * 65)
    print(f"  - Total Incident Clusters Summarized: {summarized_count}")
    print(f"  - Model Used:                         t5-small (on CUDA/GPU)")
    print(f"  - Summary Length:                     Strictly 1-2 Sentences")
    print(f"  - Grounding & Guardrails:             Active (Veracity & Context Guided)")
    print(f"  - PostgreSQL Persistence:             Committed to disaster_clusters.summary")
    print("=" * 65 + "\n")

if __name__ == "__main__":
    asyncio.run(run_phase5_pipeline())
