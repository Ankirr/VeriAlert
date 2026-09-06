"""
Deterministic Trust Scoring Module with Strict Multi-Tier Veracity Guardrails.
Implements:
  Trust = (w_source * S_auth) + (w_corrob * Corrob_Factor) - Penalty_contradiction

Strict Veracity Bands:
  - VERIFIED (MULTI-SOURCE OR OFFICIAL) (>= 0.75): Requires N_indep >= 2 OR Official Agency (NDMA/IMD)
  - CREDIBLE (SINGLE REPUTABLE SOURCE - DEVELOPING) (0.55 - 0.74): Reputable news without second confirmation
  - UNVERIFIED (CROWDSOURCED / LOW CONFIDENCE) (0.35 - 0.54): Unconfirmed social media or solitary blog
  - DISPUTED (CONFLICTING REPORTS) (< 0.35 or NLI Contradiction): Factual or numerical clashes
"""
import math
import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

# Authority scoring by reporting source category
SOURCE_AUTHORITY_SCORES: Dict[str, float] = {
    # Official Government / Meteorological Authorities (Highest standard)
    "ndma": 1.00,
    "imd": 1.00,
    "cwc": 1.00,
    "disaster management authority": 1.00,
    "official": 1.00,

    # Tier-1 Reputable National & Global Investigative Journalism
    "bbc": 0.90,
    "reuters": 0.90,
    "the hindu": 0.88,
    "the times of india": 0.86,
    "times of india": 0.86,
    "businessline": 0.85,
    "hindustan times": 0.85,
    "indian express": 0.85,
    "dw": 0.85,

    # Regional Indian News & Wire Services
    "ndtv": 0.80,
    "khabarhub": 0.76,
    "the citizen": 0.75,
    "ani": 0.80,
    "pti": 0.82,

    # Automated Global Web Ingestion & Backups
    "gdelt": 0.70,
    "newsapi": 0.75,

    # Crowdsourced Social Media (Prone to rumors without independent confirmation)
    "reddit": 0.45,
    "twitter": 0.45,
    "social": 0.45
}

def get_source_authority(source_name: str) -> float:
    """Computes authority score S_auth in [0.45, 1.0] for a source."""
    if not source_name:
        return 0.50
    s_lower = source_name.lower()
    
    for key, score in SOURCE_AUTHORITY_SCORES.items():
        if key in s_lower:
            return score
    return 0.65  # Default baseline for unrecognized source

class DeterministicTrustScorer:
    """
    Computes rigorous mathematical trust score and veracity classifications.
    Enforces strict guardrails so no single uncorroborated newspaper or rumor
    can ever claim 'VERIFIED' status prematurely.
    """
    def __init__(self, w_source: float = 0.50, w_corrob: float = 0.50):
        self.w_source = w_source
        self.w_corrob = w_corrob

    def score_cluster(self, cluster: Dict[str, Any], nli_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculates deterministic trust score for an incident cluster:
        """
        sources: List[str] = cluster.get("sources", [])
        
        # 1. Source Authority: Highest authority among all sources present
        authorities = [get_source_authority(s) for s in sources]
        s_auth = max(authorities) if authorities else 0.50
        is_official = (s_auth >= 0.98)

        # 2. Corroboration Term: log10(N_indep) / log10(4)
        # Strictly 0 if only 1 source exists (no corroboration has occurred)
        n_indep = len(sources)
        if n_indep <= 1:
            normalized_corrob = 0.0
        else:
            # log10(4) ≈ 0.602; 4 or more independent outlets = 1.0 (100% corroboration)
            norm_factor = math.log10(4.0)
            corrob_raw = math.log10(float(n_indep))
            normalized_corrob = min(1.0, corrob_raw / norm_factor)

        # 3. NLI Contradiction Penalty
        has_contradiction = nli_result.get("has_contradiction", False)
        nli_agreement = nli_result.get("nli_agreement_score", 0.85)

        penalty = 0.0
        if has_contradiction:
            penalty = 0.35
        elif nli_agreement < 0.60:
            penalty = 0.15

        # 4. Compute Base Trust Score
        if is_official and n_indep == 1:
            # Official bulletins start with a high certified baseline
            base_trust = 0.78
        elif n_indep == 1:
            # Single source has zero corroboration; relies strictly on source authority
            base_trust = self.w_source * s_auth + 0.20  # Max: 0.50*0.90 + 0.20 = 0.65
        else:
            # Multi-source cluster combines authority + independent corroboration
            base_trust = (self.w_source * s_auth) + (self.w_corrob * normalized_corrob)

        raw_trust = base_trust - penalty
        trust_score = round(max(0.05, min(0.99, raw_trust)), 4)

        # 5. Strict Guardrails for Trust Bands
        if has_contradiction or trust_score < 0.35:
            trust_band = "DISPUTED (CONFLICTING REPORTS)"
        elif trust_score >= 0.75:
            # STRICT GUARDRAIL: Only Official civil agencies OR 2+ corroborated outlets can be VERIFIED
            if n_indep >= 2 or is_official:
                trust_band = "VERIFIED (MULTI-SOURCE)" if n_indep >= 2 else "VERIFIED (OFFICIAL ADVISORY)"
            else:
                trust_score = 0.70  # Cap single news report below verified
                trust_band = "CREDIBLE (SINGLE SOURCE - DEVELOPING)"
        elif trust_score >= 0.55:
            if n_indep >= 2:
                trust_band = "LIKELY TRUE (CORROBORATED)"
            else:
                trust_band = "CREDIBLE (SINGLE SOURCE - DEVELOPING)"
        else:
            trust_band = "UNVERIFIED (CROWDSOURCED)"

        return {
            "trust_score": trust_score,
            "trust_band": trust_band,
            "source_authority_score": round(s_auth, 4),
            "corroboration_score": round(normalized_corrob, 4),
            "independent_sources_count": n_indep,
            "contradiction_penalty": round(penalty, 4),
            "has_contradiction": has_contradiction,
            "nli_agreement_score": round(nli_agreement, 4)
        }
