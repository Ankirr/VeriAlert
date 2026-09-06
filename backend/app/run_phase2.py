import asyncio
import logging
import sys
from pathlib import Path

# Add backend directory to path
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from sqlalchemy import select
from app.db.database import AsyncSessionLocal
from app.db.models import RawDisasterItemModel
from app.classifier.train_classifier import train
from app.classifier.inference import DisasterRelevanceClassifier

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("Phase2Runner")

async def test_inference_on_db_records(classifier: DisasterRelevanceClassifier):
    logger.info("\n" + "=" * 65)
    logger.info("  BATCH INFERENCE VERIFICATION ON PHASE 1 STORED ITEMS")
    logger.info("=" * 65)
    
    async with AsyncSessionLocal() as session:
        stmt = select(RawDisasterItemModel).order_by(RawDisasterItemModel.is_mock.asc(), RawDisasterItemModel.timestamp.desc()).limit(12)
        result = await session.execute(stmt)
        items = result.scalars().all()
        
        logger.info(f"Classifying {len(items)} sample records from PostgreSQL with 0.55 confidence cutoff:\n")
        
        for idx, item in enumerate(items, 1):
            text_to_eval = f"{item.title or ''}. {item.raw_text[:200]}"
            classification = classifier.classify_text(text_to_eval)
            
            status_flag = "[RELEVANT]" if classification["is_relevant"] else "[FILTERED OUT]"
            source_tag = "[MOCK]" if item.is_mock else "[REAL]"
            
            print(f"[{idx}] {status_flag} {source_tag} ({item.source})")
            print(f"     Title:           {(item.title or '')[:70]}...")
            print(f"     Is Relevant:     {classification['is_relevant']}")
            print(f"     Disaster Type:   {classification['disaster_type']}")
            print(f"     Confidence:      {classification['confidence_score']:.4f} (Cutoff: {classifier.cutoff})")
            print(f"     Location Hint:   {item.location_text}")
            print("     " + "-" * 55)

def main():
    logger.info("=" * 65)
    logger.info("  PHASE 2: RELEVANCE CLASSIFICATION & FINE-TUNING PIPELINE")
    logger.info("=" * 65)
    
    # Step 1: Run fine-tuning on HumAID dataset
    metrics = train()
    
    # Step 2: Load fine-tuned model for inference
    logger.info("\nInitializing inference engine with locally saved model...")
    classifier = DisasterRelevanceClassifier()
    
    # Step 3: Run inference on live database items
    asyncio.run(test_inference_on_db_records(classifier))
    
    logger.info("\n" + "=" * 65)
    logger.info("PHASE 2 TRAINING & INFERENCE EXECUTION COMPLETE!")
    logger.info(f"Final Reported Test F1-Score: {metrics.get('eval_f1', 0):.4f}")
    logger.info(f"Final Reported Test Accuracy: {metrics.get('eval_accuracy', 0):.4f}")
    logger.info("=" * 65)

if __name__ == "__main__":
    main()
