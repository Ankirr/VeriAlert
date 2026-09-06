"""
Phase 4 Pipeline Runner: Semantic Event Clustering, NLI Veracity Verification,
and Deterministic Trust Scoring.
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

from sqlalchemy import select, delete
from app.db.database import AsyncSessionLocal
from app.db.models import RawDisasterItemModel, DisasterClusterModel
from app.verification.clusterer import DisasterEventClusterer
from app.verification.nli_verifier import NLIVeracityVerifier
from app.verification.trust_scorer import DeterministicTrustScorer

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("Phase4Runner")

async def run_phase4_pipeline():
    logger.info("=" * 75)
    logger.info("  PHASE 4: CROSS-SOURCE VERACITY VERIFICATION & NLI TRUST SCORING")
    logger.info("=" * 75)

    # 1. Initialize Verification Engine
    logger.info("1. Initializing Semantic Event Clusterer (SentenceTransformers all-MiniLM-L6-v2 on GPU)...")
    clusterer = DisasterEventClusterer()

    logger.info("2. Initializing DeBERTa-v3 Natural Language Inference Verifier on GPU...")
    nli_verifier = NLIVeracityVerifier()

    logger.info("3. Initializing Deterministic Trust Scoring Formula Engine...")
    trust_scorer = DeterministicTrustScorer()

    # 2. Fetch enriched items from PostgreSQL
    async with AsyncSessionLocal() as session:
        stmt = select(RawDisasterItemModel).where(RawDisasterItemModel.latitude.isnot(None)).order_by(RawDisasterItemModel.timestamp.desc())
        result = await session.execute(stmt)
        db_items = result.scalars().all()

        logger.info(f"Retrieved {len(db_items)} geocoded disaster records from PostgreSQL.")

        items_data = []
        for item in db_items:
            classification = (item.raw_metadata or {}).get("classification", {})
            items_data.append({
                "id": item.id,
                "source": item.source,
                "source_type": item.source_type,
                "title": item.title or "",
                "raw_text": item.raw_text,
                "location_text": item.location_text or "India",
                "latitude": item.latitude,
                "longitude": item.longitude,
                "disaster_type": classification.get("disaster_type", "general_disaster"),
                "is_mock": item.is_mock
            })

        # 3. Cluster items into incidents
        clusters = clusterer.cluster_items(items_data)

        # 4. Clear existing clusters and prepare for fresh sync
        await session.execute(delete(DisasterClusterModel))

        print("\n" + "=" * 115)
        print(f"{'#':<3} | {'EVENT / CALAMITY':<34} | {'LOCATION':<18} | {'SOURCES':<7} | {'NLI AGREE':<9} | {'TRUST':<7} | {'VERACITY BAND'}")
        print("=" * 115)

        verified_count = 0
        corroborated_count = 0
        single_source_count = 0
        disputed_count = 0

        # Map item IDs to cluster info for updating RawDisasterItemModel
        item_updates = {}

        for idx, cluster in enumerate(clusters, 1):
            # A. Cross-verify with DeBERTa-v3 NLI
            nli_res = nli_verifier.verify_cluster(cluster)

            # B. Score cluster using Deterministic Trust Formula
            score_res = trust_scorer.score_cluster(cluster, nli_res)

            trust_score = score_res["trust_score"]
            trust_band = score_res["trust_band"]

            if "VERIFIED" in trust_band:
                verified_count += 1
            elif "LIKELY" in trust_band:
                corroborated_count += 1
            elif "DISPUTED" in trust_band:
                disputed_count += 1
            else:
                single_source_count += 1

            # C. Create persistent DisasterClusterModel record
            cluster_model = DisasterClusterModel(
                id=cluster["cluster_id"],
                event_name=cluster["event_name"],
                disaster_type=cluster["disaster_type"],
                location_name=cluster["location_name"],
                latitude=cluster["latitude"],
                longitude=cluster["longitude"],
                trust_score=trust_score,
                trust_band=trust_band,
                source_authority_score=score_res["source_authority_score"],
                corroborating_sources_count=score_res["independent_sources_count"],
                has_contradiction=score_res["has_contradiction"],
                nli_agreement_score=score_res["nli_agreement_score"],
                sources=cluster["sources"],
                item_ids=cluster["item_ids"]
            )
            session.add(cluster_model)

            # Save updates for member items
            for item_id in cluster["item_ids"]:
                item_updates[item_id] = {
                    "cluster_id": cluster["cluster_id"],
                    "trust_score": trust_score,
                    "trust_band": trust_band
                }

            # Format and print row
            event_display = cluster["event_name"][:34]
            loc_display = cluster["location_name"][:18]
            sources_str = f"{len(cluster['sources'])} ({cluster['item_count']} rpts)"
            nli_str = f"{score_res['nli_agreement_score']:.2f}"
            trust_str = f"{trust_score:.2f}"

            print(f"{idx:<3} | {event_display:<34} | {loc_display:<18} | {sources_str:<7} | {nli_str:<9} | {trust_str:<7} | {trust_band}")

        # Update member items in database
        for item in db_items:
            if item.id in item_updates:
                item.cluster_id = item_updates[item.id]["cluster_id"]
                item.trust_score = item_updates[item.id]["trust_score"]
                item.trust_band = item_updates[item.id]["trust_band"]

        await session.commit()
        logger.info(f"\nAll {len(clusters)} incident clusters and {len(item_updates)} member records committed to PostgreSQL.")

    print("=" * 115)
    print("\n" + "=" * 65)
    print("  PHASE 4: VERACITY VERIFICATION & TRUST METRICS SUMMARY")
    print("=" * 65)
    print(f"  - Total Disaster Reports Clustered:    {len(items_data)}")
    print(f"  - Distinct Incident Clusters Formed:  {len(clusters)}")
    print(f"  - Multi-Source Verified Alert Events: {verified_count}")
    print(f"  - Likely True / Corroborated Events:  {corroborated_count}")
    print(f"  - Single-Source / Unverified Reports: {single_source_count}")
    print(f"  - Disputed / Contradicted Events:     {disputed_count}")
    print("=" * 65 + "\n")

if __name__ == "__main__":
    asyncio.run(run_phase4_pipeline())
