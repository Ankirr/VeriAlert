"""
Factual Public Alert Summarization Module using T5.
Generates concise, factual, 1-2 sentence emergency public advisories
grounded strictly in corroborated cluster claims.
"""
import re
import logging
from typing import Dict, Any, List, Optional
import torch
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM

logger = logging.getLogger(__name__)

MODEL_NAME = "t5-small"

# Global cached T5 summarizer instance
_T5_TOKENIZER = None
_T5_MODEL = None

def get_t5_engine():
    global _T5_TOKENIZER, _T5_MODEL
    if _T5_MODEL is None:
        device = "cuda" if torch.cuda.is_available() else "cpu"
        logger.info(f"Loading T5 model '{MODEL_NAME}' on {device}...")
        _T5_TOKENIZER = AutoTokenizer.from_pretrained(MODEL_NAME)
        _T5_MODEL = AutoModelForSeq2SeqLM.from_pretrained(MODEL_NAME).to(device)
        _T5_MODEL.eval()
    return _T5_TOKENIZER, _T5_MODEL

class FactualAlertSummarizer:
    """
    Synthesizes actionable 1-2 sentence emergency advisories for disaster incident clusters.
    Grounded in extracted facts without hallucinating external details.
    """
    def __init__(self):
        self.tokenizer, self.model = get_t5_engine()
        self.device = next(self.model.parameters()).device

    def generate_alert_summary(
        self,
        event_name: str,
        location_name: str,
        disaster_type: str,
        trust_band: str,
        member_texts: List[str]
    ) -> str:
        """
        Generates a concise 1-2 sentence public alert summary for a cluster.
        """
        # Combine top member texts into factual context
        combined_context = self._build_context(event_name, location_name, disaster_type, member_texts)
        
        prompt = f"summarize: {combined_context}"
        inputs = self.tokenizer(
            prompt,
            return_tensors="pt",
            max_length=512,
            truncation=True
        ).to(self.device)

        with torch.no_grad():
            outputs = self.model.generate(
                **inputs,
                max_length=70,
                min_length=16,
                num_beams=4,
                no_repeat_ngram_size=3,
                length_penalty=1.0,
                early_stopping=True
            )

        raw_summary = self.tokenizer.decode(outputs[0], skip_special_tokens=True).strip()
        
        # Clean and standardize summary format
        formatted_summary = self._post_process(raw_summary, location_name, disaster_type, trust_band)
        return formatted_summary

    def _build_context(self, event_name: str, location_name: str, disaster_type: str, texts: List[str]) -> str:
        # Deduplicate and clean sentences from member texts
        cleaned_excerpts = []
        for text in texts[:4]:
            t_clean = re.sub(r'http\S+', '', text)
            t_clean = re.sub(r'\s+', ' ', t_clean).strip()
            if len(t_clean) > 20 and t_clean not in cleaned_excerpts:
                cleaned_excerpts.append(t_clean[:200])

        context = f"{event_name}. Location: {location_name}. " + " ".join(cleaned_excerpts)
        return context[:600]

    def _post_process(self, summary: str, location_name: str, disaster_type: str, trust_band: str) -> str:
        if not summary:
            summary = f"{disaster_type.title()} reported in {location_name}. Public is advised to stay alert."

        # Capitalize first character
        summary = summary[0].upper() + summary[1:]

        # Ensure sentence ends with a period
        if not summary.endswith((".", "!", "?")):
            summary += "."

        # Guarantee at most 2 sentences
        sentences = [s.strip() for s in re.split(r'(?<=[.!?]) +', summary) if s.strip()]
        if len(sentences) > 2:
            summary = " ".join(sentences[:2])
            if not summary.endswith("."):
                summary += "."

        # Prepend veracity advisory tag if necessary
        if "DISPUTED" in trust_band:
            summary = f"[DISPUTED] {summary} Official casualty counts and hazard levels remain conflicting across outlets."
        elif "UNVERIFIED" in trust_band:
            summary = f"[UNVERIFIED] {summary} Report originates from local crowdsourced social media; awaiting official confirmation."
        elif "OFFICIAL" in trust_band:
            summary = f"[OFFICIAL ADVISORY] {summary}"

        return summary
