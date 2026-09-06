"""
Phase 3 Pipeline Runner: Geo-Extraction & Entity Resolution.
Extracts locations using spaCy NER + Gazetteer, geocodes via GeoPy Nominatim
with Redis + Disk 2-tier caching, and updates PostgreSQL database items.
"""
import asyncio
import logging
import sys
from pathlib import Path
from typing import List, Dict, Any

# Ensure stdout handles UTF-8 characters without Windows cp1252 crash
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
from app.db.models import RawDisasterItemModel
from app.classifier.inference import DisasterRelevanceClassifier
from app.geo.extractor import DisasterLocationExtractor
from app.geo.geocoder import CachedDisasterGeocoder

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("Phase3Runner")

async def run_phase3_pipeline():
    logger.info("=" * 70)
    logger.info("  PHASE 3: GEO-EXTRACTION & ENTITY RESOLUTION PIPELINE")
    logger.info("=" * 70)

    # Initialize components
    logger.info("1. Initializing fine-tuned relevance classifier from Phase 2...")
    classifier = DisasterRelevanceClassifier()

    logger.info("2. Initializing spaCy NER Location Extractor & Regional Gazetteer...")
    extractor = DisasterLocationExtractor()

    logger.info("3. Initializing 2-Tier Cached Geocoder (Redis + Disk + Nominatim)...")
    geocoder = CachedDisasterGeocoder()

    # Query items from database
    async with AsyncSessionLocal() as session:
        stmt = select(RawDisasterItemModel).order_by(RawDisasterItemModel.timestamp.desc())
        result = await session.execute(stmt)
        items = result.scalars().all()
        
        logger.info(f"Retrieved {len(items)} items from PostgreSQL database for processing.\n")

        processed_count = 0
        relevant_count = 0
        geocoded_count = 0
        cache_hits = 0

        print("\n" + "=" * 95)
        print(f"{'#':<3} | {'SOURCE':<14} | {'CALAMITY':<10} | {'LOCATION RESOLVED':<24} | {'COORDINATES (LAT, LON)':<22} | {'CACHE'}")
        print("=" * 95)

        for idx, item in enumerate(items, 1):
            text_to_eval = f"{item.title or ''}. {item.raw_text}"
            classification = classifier.classify_text(text_to_eval[:300])

            if not classification["is_relevant"]:
                continue

            relevant_count += 1
            
            # Step A: Extract geographical entities with Title Priority
            geo_extraction = extractor.extract_locations(
                text_to_eval,
                location_hint=item.location_text,
                title=item.title
            )
            primary_query = geo_extraction["primary_location"]

            # Step B: Geocode coordinates with Redis + Disk caching
            geo_result = geocoder.geocode(
                primary_query,
                state_hint=geo_extraction.get("state"),
                country_hint=geo_extraction.get("country", "India")
            )

            if geo_result.get("cached"):
                cache_hits += 1

            lat = geo_result.get("latitude")
            lon = geo_result.get("longitude")

            if lat is not None and lon is not None:
                geocoded_count += 1

            # Step C: Update item in database
            item.latitude = lat
            item.longitude = lon
            item.location_text = geo_result.get("city") or geo_result.get("state") or primary_query
            
            # Update metadata
            meta = dict(item.raw_metadata or {})
            meta["geo"] = {
                "extracted_entities": geo_extraction["extracted_entities"],
                "primary_location": primary_query,
                "display_name": geo_result.get("display_name"),
                "city": geo_result.get("city"),
                "state": geo_result.get("state"),
                "country": geo_result.get("country"),
                "confidence": geo_result.get("confidence", 0.0),
                "is_fallback": geo_result.get("is_fallback", False),
                "cached": geo_result.get("cached", False)
            }
            meta["classification"] = classification
            item.raw_metadata = meta

            processed_count += 1

            # Print formatted line
            source_abbr = item.source[:14]
            disaster_type = classification["disaster_type"][:10]
            loc_display = (item.location_text or primary_query)[:24]
            coords_str = f"{lat:.4f}, {lon:.4f}" if (lat and lon) else "N/A"
            cache_status = "HIT" if geo_result.get("cached") else "LIVE API"

            print(f"{processed_count:<3} | {source_abbr:<14} | {disaster_type:<10} | {loc_display:<24} | {coords_str:<22} | {cache_status}")

        # Commit all geo-enrichments to PostgreSQL
        await session.commit()
        logger.info("\nDatabase transaction committed. All relevant records enriched with coordinates.")

    print("=" * 95)
    print("\n" + "=" * 65)
    print("  PHASE 3: GEO-EXTRACTION & RESOLUTION SUMMARY")
    print("=" * 65)
    print(f"  - Total Database Records Examined:  {len(items)}")
    print(f"  - Relevant Disasters (Phase 2):    {relevant_count}")
    print(f"  - Successfully Geocoded with Lat/Lon: {geocoded_count} ({geocoded_count/relevant_count:.1%})")
    print(f"  - Cache Hits (Instant Resolution):  {cache_hits}")
    print(f"  - Live Nominatim Queries:          {relevant_count - cache_hits}")
    print("=" * 65 + "\n")

if __name__ == "__main__":
    asyncio.run(run_phase3_pipeline())
