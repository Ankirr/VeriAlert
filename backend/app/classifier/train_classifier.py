import os
import json
import logging
import time
from pathlib import Path
import numpy as np
import torch
from transformers import (
    AutoTokenizer,
    AutoModelForSequenceClassification,
    Trainer,
    TrainingArguments,
    DataCollatorWithPadding
)
from datasets import Dataset
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score, confusion_matrix

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("DistilRoBERTaTrainer")

CURRENT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = CURRENT_DIR.parent.parent
DATA_PATH = CURRENT_DIR / "data" / "humaid_processed.json"
MODEL_SAVE_DIR = BACKEND_DIR / "models" / "fine_tuned_distilroberta"
MODEL_SAVE_DIR.mkdir(parents=True, exist_ok=True)

MODEL_NAME = "distilroberta-base"

def compute_metrics(eval_pred):
    logits, labels = eval_pred
    preds = np.argmax(logits, axis=-1)
    
    acc = accuracy_score(labels, preds)
    f1 = f1_score(labels, preds, average="binary")
    f1_macro = f1_score(labels, preds, average="macro")
    precision = precision_score(labels, preds, average="binary", zero_division=0)
    recall = recall_score(labels, preds, average="binary", zero_division=0)
    cm = confusion_matrix(labels, preds).tolist()
    
    return {
        "accuracy": acc,
        "f1": f1,
        "f1_macro": f1_macro,
        "precision": precision,
        "recall": recall,
        "confusion_matrix": cm
    }

def train():
    logger.info("=" * 60)
    logger.info("  PHASE 2: FINE-TUNING DISTILROBERTA-BASE ON HUMAID DATASET")
    logger.info("=" * 60)
    
    if not DATA_PATH.exists():
        raise FileNotFoundError(f"Prepared HumAID data not found at {DATA_PATH}. Run prepare_dataset.py first.")
        
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    train_records = data["train"]
    test_records = data["test"]
    
    logger.info(f"Loaded {len(train_records)} training records and {len(test_records)} held-out test records.")
    
    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
    
    def tokenize_fn(batch):
        return tokenizer(batch["text"], truncation=True, max_length=128, padding=False)
        
    train_ds = Dataset.from_list(train_records).map(tokenize_fn, batched=True)
    test_ds = Dataset.from_list(test_records).map(tokenize_fn, batched=True)
    
    logger.info(f"Loading pre-trained base model: {MODEL_NAME} for binary sequence classification...")
    id2label = {0: "non_disaster", 1: "disaster_relevant"}
    label2id = {"non_disaster": 0, "disaster_relevant": 1}
    
    model = AutoModelForSequenceClassification.from_pretrained(
        MODEL_NAME,
        num_labels=2,
        id2label=id2label,
        label2id=label2id
    )
    
    has_cuda = torch.cuda.is_available()
    device_name = torch.cuda.get_device_name(0) if has_cuda else "CPU"
    logger.info(f"Training device detected: {device_name} (CUDA available: {has_cuda})")
    
    training_args = TrainingArguments(
        output_dir=str(MODEL_SAVE_DIR / "checkpoints"),
        eval_strategy="epoch",
        save_strategy="epoch",
        learning_rate=2e-5,
        warmup_steps=120,
        per_device_train_batch_size=16,
        per_device_eval_batch_size=32,
        num_train_epochs=3,
        weight_decay=0.01,
        logging_steps=100,
        load_best_model_at_end=True,
        metric_for_best_model="f1",
        greater_is_better=True,
        report_to="none",
        use_cpu=(not has_cuda),
        fp16=has_cuda
    )
    
    data_collator = DataCollatorWithPadding(tokenizer=tokenizer)
    
    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=train_ds,
        eval_dataset=test_ds,
        processing_class=tokenizer,
        data_collator=data_collator,
        compute_metrics=compute_metrics
    )
    
    logger.info(f"Starting fine-tuning on {device_name}...")
    start_time = time.time()
    train_result = trainer.train()
    elapsed = time.time() - start_time
    logger.info(f"Training completed in {elapsed:.1f} seconds ({elapsed/60:.2f} minutes).")
    
    logger.info(f"Evaluating on held-out test split ({len(test_records)} samples)...")
    eval_metrics = trainer.evaluate()
    
    # Save the final fine-tuned model and tokenizer
    logger.info(f"Saving fine-tuned model to: {MODEL_SAVE_DIR}")
    trainer.save_model(str(MODEL_SAVE_DIR))
    tokenizer.save_pretrained(str(MODEL_SAVE_DIR))
    
    # Save evaluation metrics JSON
    metrics_path = MODEL_SAVE_DIR / "evaluation_metrics.json"
    with open(metrics_path, "w", encoding="utf-8") as f:
        json.dump({
            "metrics": eval_metrics,
            "training_time_seconds": elapsed,
            "train_samples": len(train_records),
            "test_samples": len(test_records)
        }, f, indent=2)
        
    logger.info("=" * 60)
    logger.info("  EVALUATION RESULTS ON HELD-OUT TEST SPLIT:")
    logger.info(f"    - Accuracy:         {eval_metrics.get('eval_accuracy', 0):.4f}")
    logger.info(f"    - F1-Score (Binary): {eval_metrics.get('eval_f1', 0):.4f}")
    logger.info(f"    - F1-Score (Macro):  {eval_metrics.get('eval_f1_macro', 0):.4f}")
    logger.info(f"    - Precision:        {eval_metrics.get('eval_precision', 0):.4f}")
    logger.info(f"    - Recall:           {eval_metrics.get('eval_recall', 0):.4f}")
    cm = eval_metrics.get("eval_confusion_matrix", [[0, 0], [0, 0]])
    logger.info(f"    - Confusion Matrix: [TN={cm[0][0]}, FP={cm[0][1]} | FN={cm[1][0]}, TP={cm[1][1]}]")
    logger.info("=" * 60)
    
    return eval_metrics

if __name__ == "__main__":
    train()
