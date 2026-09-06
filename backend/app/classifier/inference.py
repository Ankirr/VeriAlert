import logging
import re
from pathlib import Path
from typing import Dict, Any, List, Union
import torch
import torch.nn.functional as F
from transformers import AutoTokenizer, AutoModelForSequenceClassification

logger = logging.getLogger(__name__)

CURRENT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = CURRENT_DIR.parent.parent
MODEL_DIR = BACKEND_DIR / "models" / "fine_tuned_distilroberta"

DEFAULT_CUTOFF = 0.55

DISASTER_TYPE_KEYWORDS = {
    "flood": ["flood", "flooding", "waterlog", "submerged", "inundat", "overflow", "danger mark", "cwc", "river breach", "embankment"],
    "landslide": ["landslide", "mudslide", "rockslide", "debris flow", "slope failure", "boulder", "blocked highway"],
    "cyclone": ["cyclone", "deep depression", "storm surge", "gale", "coastal storm", "low pressure area"],
    "earthquake": ["earthquake", "tremor", "aftershock", "seismic", "richter", "epicenter"],
    "cloudburst": ["cloudburst", "flash flood", "torrential downpour", "excess rainfall"],
    "heatwave": ["heatwave", "severe heat", "maximum temperature", "sunstroke"]
}

class DisasterRelevanceClassifier:
    """
    Inference module using the fine-tuned DistilRoBERTa model.
    Outputs: {is_relevant: bool, disaster_type: str, confidence_score: float}.
    Uses a 0.55 confidence cutoff to reliably discard non-disaster noise.
    """
    def __init__(self, model_path: Union[str, Path] = None, cutoff: float = DEFAULT_CUTOFF):
        self.model_path = Path(model_path) if model_path else MODEL_DIR
        self.cutoff = cutoff
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        
        self.model = None
        self.tokenizer = None
        self._load_model()

    def _load_model(self):
        if not self.model_path.exists() or not (self.model_path / "config.json").exists():
            logger.warning(f"Fine-tuned model not found at {self.model_path}. Fallback to distilroberta-base.")
            model_id = "distilroberta-base"
        else:
            model_id = str(self.model_path)
            
        logger.info(f"Loading classifier model from: {model_id}")
        self.tokenizer = AutoTokenizer.from_pretrained(model_id)
        self.model = AutoModelForSequenceClassification.from_pretrained(model_id)
        self.model.to(self.device)
        self.model.eval()

    def classify_text(self, text: str) -> Dict[str, Any]:
        """
        Classifies input text and returns:
        {
            "is_relevant": bool,
            "disaster_type": str,
            "confidence_score": float,
            "raw_class": str
        }
        """
        if not text or not text.strip():
            return {
                "is_relevant": False,
                "disaster_type": "none",
                "confidence_score": 0.0,
                "raw_class": "non_disaster"
            }

        inputs = self.tokenizer(
            text,
            truncation=True,
            max_length=128,
            padding=True,
            return_tensors="pt"
        )
        inputs = {k: v.to(self.device) for k, v in inputs.items()}

        with torch.no_grad():
            outputs = self.model(**inputs)
            probs = F.softmax(outputs.logits, dim=-1)[0]
            
            # Label 1 is disaster_relevant, Label 0 is non_disaster
            prob_relevant = float(probs[1].item())
            predicted_class_id = int(torch.argmax(probs).item())

        is_relevant = (prob_relevant >= self.cutoff)
        confidence_score = round(prob_relevant, 4)
        
        # Determine disaster type based on text content
        disaster_type = self._infer_disaster_type(text) if is_relevant else "none"

        return {
            "is_relevant": is_relevant,
            "disaster_type": disaster_type,
            "confidence_score": confidence_score,
            "raw_class": "disaster_relevant" if is_relevant else "non_disaster"
        }

    def _infer_disaster_type(self, text: str) -> str:
        text_lower = text.lower()
        
        scores = {}
        for dtype, kws in DISASTER_TYPE_KEYWORDS.items():
            count = sum(1 for kw in kws if kw in text_lower)
            if count > 0:
                scores[dtype] = count
                
        if scores:
            return max(scores, key=scores.get)
        return "general_disaster"

    def classify_batch(self, texts: List[str]) -> List[Dict[str, Any]]:
        return [self.classify_text(t) for t in texts]
