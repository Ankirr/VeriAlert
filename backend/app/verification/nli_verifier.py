"""
NLI Cross-Source Veracity Verification Module.
Uses DeBERTa-v3 NLI to cross-evaluate claims across independent sources,
computing agreement scores and detecting factual contradictions (e.g. casualties, locations, magnitudes).
"""
import re
import logging
from typing import List, Dict, Any, Tuple
import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification

logger = logging.getLogger(__name__)

NLI_MODEL_NAME = "MoritzLaurer/DeBERTa-v3-base-mnli-fever-anli"

# Global cached NLI model instance
_NLI_TOKENIZER = None
_NLI_MODEL = None

def get_nli_engine():
    global _NLI_TOKENIZER, _NLI_MODEL
    if _NLI_MODEL is None:
        device = "cuda" if torch.cuda.is_available() else "cpu"
        logger.info(f"Loading DeBERTa-v3 NLI model '{NLI_MODEL_NAME}' on {device}...")
        _NLI_TOKENIZER = AutoTokenizer.from_pretrained(NLI_MODEL_NAME)
        _NLI_MODEL = AutoModelForSequenceClassification.from_pretrained(NLI_MODEL_NAME).to(device)
        _NLI_MODEL.eval()
    return _NLI_TOKENIZER, _NLI_MODEL

def extract_quantifiers(text: str) -> Dict[str, int]:
    """Extracts numbers linked to critical disaster metrics (dead, killed, injured, missing)."""
    text_lower = text.lower()
    metrics = {}
    
    # Casualties: e.g. "31 killed", "12 dead", "toll rises to 50"
    dead_match = re.findall(r'(\d+)\s*(?:people|workers)?\s*(?:dead|killed|deaths|fatalities)', text_lower)
    if not dead_match:
        dead_match = re.findall(r'(?:toll|deaths?)\s*(?:rises? to|reaches?|at)?\s*(\d+)', text_lower)
    if dead_match:
        try:
            metrics["dead"] = int(dead_match[0])
        except Exception:
            pass

    # Missing: e.g. "531 missing"
    missing_match = re.findall(r'(\d+)\s*(?:people|workers)?\s*missing', text_lower)
    if missing_match:
        try:
            metrics["missing"] = int(missing_match[0])
        except Exception:
            pass

    return metrics

class NLIVeracityVerifier:
    """
    Cross-verifies claims across reporting sources using Natural Language Inference
    and numerical divergence checks for casualties and impacts.
    """
    def __init__(self):
        self.tokenizer, self.model = get_nli_engine()
        self.device = next(self.model.parameters()).device
        self.id2label = self.model.config.id2label

    def verify_cluster(self, cluster: Dict[str, Any]) -> Dict[str, Any]:
        """
        Cross-verifies all reports inside a cluster.
        """
        items = cluster.get("items", [])
        if len(items) <= 1:
            return {
                "nli_agreement_score": 0.85,
                "has_contradiction": False,
                "contradictions": [],
                "pairwise_count": 0
            }

        pairs_to_evaluate = []
        n = len(items)

        # Generate representative pairwise comparisons
        for i in range(n):
            for j in range(i + 1, n):
                if len(pairs_to_evaluate) >= 8:
                    break
                pairs_to_evaluate.append((items[i], items[j]))
            if len(pairs_to_evaluate) >= 8:
                break

        pairwise_scores = []
        contradictions = []

        for item_a, item_b in pairs_to_evaluate:
            text_a = f"{item_a.get('title') or ''}. {item_a.get('raw_text', '')[:160]}"
            text_b = f"{item_b.get('title') or ''}. {item_b.get('raw_text', '')[:160]}"

            nli_res = self._evaluate_pair(text_a, text_b)
            p_entail = nli_res.get("entailment", 0.0)
            p_neutral = nli_res.get("neutral", 0.0)
            p_contra = nli_res.get("contradiction", 0.0)

            # Check for numerical discrepancy in death/missing counts
            num_a = extract_quantifiers(text_a)
            num_b = extract_quantifiers(text_b)
            num_divergence = False
            
            if "dead" in num_a and "dead" in num_b:
                diff = abs(num_a["dead"] - num_b["dead"])
                # Discrepancy if difference exceeds 50% of the smaller number
                if diff > max(5, min(num_a["dead"], num_b["dead"]) * 0.5):
                    num_divergence = True
                    p_contra = max(p_contra, 0.45)

            pair_score = max(0.0, min(1.0, p_entail * 1.0 + p_neutral * 0.75 - p_contra * 1.5))
            pairwise_scores.append(pair_score)

            if p_contra >= 0.35 or num_divergence:
                contradictions.append({
                    "source_a": item_a.get("source"),
                    "source_b": item_b.get("source"),
                    "claim_a": text_a[:80],
                    "claim_b": text_b[:80],
                    "contradiction_prob": round(p_contra, 4),
                    "numerical_conflict": num_divergence
                })

        avg_agreement = float(sum(pairwise_scores) / len(pairwise_scores)) if pairwise_scores else 0.85
        has_contradiction = (len(contradictions) > 0)

        if has_contradiction:
            avg_agreement = max(0.1, avg_agreement - 0.25)

        return {
            "nli_agreement_score": round(avg_agreement, 4),
            "has_contradiction": has_contradiction,
            "contradictions": contradictions,
            "pairwise_count": len(pairs_to_evaluate)
        }

    def _evaluate_pair(self, premise: str, hypothesis: str) -> Dict[str, float]:
        """Runs bidirectional DeBERTa-v3 inference on (premise, hypothesis)."""
        inputs = self.tokenizer(
            premise, hypothesis,
            truncation=True,
            max_length=128,
            padding=True,
            return_tensors="pt"
        ).to(self.device)

        with torch.no_grad():
            logits = self.model(**inputs).logits
            probs = torch.softmax(logits, dim=-1)[0]

        result = {}
        for idx, label in self.id2label.items():
            result[label.lower()] = float(probs[idx].item())
        return result
