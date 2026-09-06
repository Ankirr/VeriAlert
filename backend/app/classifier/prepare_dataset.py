import os
import json
import logging
import random
from pathlib import Path
from datasets import load_dataset

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("HumAIDPreparer")

DATA_DIR = Path(__file__).resolve().parent / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

OUTPUT_FILE = DATA_DIR / "humaid_processed.json"

EVENT_TYPES = ["flood", "earthquake", "hurricane", "fire"]

# Non-humanitarian class label in HumAID
NON_DISASTER_LABEL = "not_humanitarian"

def prepare_humaid_dataset(target_train_size: int = 6400, target_test_size: int = 1600):
    """
    Downloads and pre-processes the HumAID dataset into balanced disaster-relevant
    vs non-disaster-relevant sets with disaster_type annotations.
    Saves the processed dataset locally as JSON.
    """
    logger.info("Loading HumAID disaster subsets from Hugging Face (QCRI/HumAID-event-type)...")
    
    all_records = []
    
    for event_type in EVENT_TYPES:
        for split in ["train", "dev", "test"]:
            try:
                ds = load_dataset("QCRI/HumAID-event-type", event_type, split=split)
                
                for item in ds:
                    text = item.get("tweet_text", "").strip()
                    if not text or len(text) < 15:
                        continue
                    
                    raw_label = item.get("class_label", "")
                    is_relevant = 0 if raw_label == NON_DISASTER_LABEL else 1
                    disaster_type = event_type if is_relevant == 1 else "non_disaster"
                    
                    all_records.append({
                        "text": text,
                        "label": is_relevant,
                        "disaster_type": disaster_type,
                        "fine_label": raw_label
                    })
            except Exception as e:
                logger.warning(f"Could not load partition '{event_type}' split '{split}': {e}")

    logger.info(f"Total raw items gathered from HumAID: {len(all_records)}")
    
    # Balance relevant vs non-relevant
    relevant = [r for r in all_records if r["label"] == 1]
    non_relevant = [r for r in all_records if r["label"] == 0]
    
    logger.info(f"Raw breakdown: Relevant={len(relevant)}, Non-Relevant={len(non_relevant)}")
    
    random.seed(42)
    random.shuffle(relevant)
    random.shuffle(non_relevant)
    
    # We want a balanced dataset
    n_each = min(len(relevant), len(non_relevant), (target_train_size + target_test_size) // 2)
    selected_relevant = relevant[:n_each]
    selected_non_relevant = non_relevant[:n_each]
    
    combined = selected_relevant + selected_non_relevant
    random.shuffle(combined)
    
    split_idx = int(len(combined) * 0.8)
    train_data = combined[:split_idx]
    test_data = combined[split_idx:]
    
    dataset_dict = {
        "train": train_data,
        "test": test_data,
        "metadata": {
            "total_samples": len(combined),
            "train_samples": len(train_data),
            "test_samples": len(test_data),
            "positive_ratio": sum(1 for x in combined if x["label"] == 1) / len(combined)
        }
    }
    
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(dataset_dict, f, indent=2, ensure_ascii=False)
        
    logger.info(f"Dataset successfully saved to: {OUTPUT_FILE}")
    logger.info(f"Train samples: {len(train_data)} | Test samples: {len(test_data)}")
    logger.info(f"Positive balance: {dataset_dict['metadata']['positive_ratio']:.2%}")
    return dataset_dict

if __name__ == "__main__":
    prepare_humaid_dataset()
