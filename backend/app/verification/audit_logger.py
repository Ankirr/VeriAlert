"""
Structured Veracity Audit Logger for Viva & Panel Defense.
Produces auditable JSON records and formatted terminal explanations detailing
the mathematical derivation of every disaster incident's deterministic trust score:
  Trust = (w_source * S_auth) + (w_corrob * Corrob_Factor) - Penalty_contradiction
"""
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List

logger = logging.getLogger("VeracityAudit")

LOGS_DIR = Path(__file__).resolve().parent.parent.parent / "logs"
LOGS_DIR.mkdir(parents=True, exist_ok=True)
AUDIT_FILE = LOGS_DIR / "audit_veracity.jsonl"
AUDIT_HUMAN_FILE = LOGS_DIR / "audit_veracity.log"

class VeracityAuditLogger:
    @staticmethod
    def log_cluster_audit(
        cluster_id: str,
        event_name: str,
        disaster_type: str,
        location_name: str,
        sources: List[str],
        score_res: Dict[str, Any],
        nli_res: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Creates and writes a rigorous mathematical audit entry for viva examination.
        """
        ts = datetime.now(timezone.utc).isoformat()
        s_auth = score_res.get("source_authority_score", 0.65)
        corrob_score = score_res.get("corroboration_score", 0.0)
        n_indep = score_res.get("independent_sources_count", len(sources))
        penalty = score_res.get("contradiction_penalty", 0.0)
        has_contra = score_res.get("has_contradiction", False)
        nli_agreement = score_res.get("nli_agreement_score", 1.0)
        final_trust = score_res.get("trust_score", 0.5)
        trust_band = score_res.get("trust_band", "UNVERIFIED")

        audit_entry = {
            "timestamp": ts,
            "cluster_id": cluster_id,
            "event_name": event_name,
            "disaster_type": disaster_type,
            "location_name": location_name,
            "reporting_sources": sources,
            "mathematical_formula": "Trust = (w_source * S_auth) + (w_corrob * Corrob_Factor) - Penalty_contradiction",
            "weights": {
                "w_source": 0.50,
                "w_corrob": 0.50
            },
            "formula_terms": {
                "S_auth": {
                    "value": s_auth,
                    "weighted_contribution": round(0.50 * s_auth, 4),
                    "rationale": f"Max credibility among sources: {', '.join(sources)}"
                },
                "Corrob_Factor": {
                    "value": corrob_score,
                    "independent_sources_count": n_indep,
                    "weighted_contribution": round(0.50 * corrob_score, 4),
                    "rationale": f"log10({n_indep})/log10(4) saturated at 4 outlets"
                },
                "Penalty_contradiction": {
                    "value": penalty,
                    "has_contradiction": has_contra,
                    "rationale": "DeBERTa-v3 detected claim conflict" if has_contra else "No conflict"
                },
                "nli_agreement_score": nli_agreement
            },
            "final_trust_score": final_trust,
            "veracity_band": trust_band,
            "viva_defense_summary": (
                f"Cluster '{event_name}' in {location_name} received Trust Score {final_trust:.2f} ({trust_band}). "
                f"Derived from S_auth={s_auth:.2f} (+{0.5*s_auth:.2f}), Corroboration={corrob_score:.2f} (+{0.5*corrob_score:.2f}), "
                f"Penalty=-{penalty:.2f} across {n_indep} sources."
            )
        }

        # 1. Append JSON Lines record
        try:
            with open(AUDIT_FILE, "a", encoding="utf-8") as f:
                f.write(json.dumps(audit_entry, ensure_ascii=False) + "\n")
        except Exception as ex:
            logger.warning(f"Could not append to JSON audit log: {ex}")

        # 2. Append Human-Readable Viva Log
        try:
            with open(AUDIT_HUMAN_FILE, "a", encoding="utf-8") as f:
                f.write("=" * 80 + "\n")
                f.write(f"TIMESTAMP: {ts} | CLUSTER: {cluster_id}\n")
                f.write(f"INCIDENT:  {event_name} ({disaster_type.upper()}) at {location_name}\n")
                f.write(f"SOURCES:   {', '.join(sources)} ({n_indep} distinct outlets)\n")
                f.write(f"FORMULA:   Trust = (0.50 * {s_auth:.2f}) + (0.50 * {corrob_score:.2f}) - {penalty:.2f} = {final_trust:.2f}\n")
                f.write(f"BAND:      {trust_band}\n")
                f.write(f"NLI CHECK: Agreement: {nli_agreement:.1%}, Contradiction: {has_contra}\n")
                f.write(f"DEFENSE:   {audit_entry['viva_defense_summary']}\n")
                f.write("=" * 80 + "\n\n")
        except Exception as ex:
            logger.warning(f"Could not append to text audit log: {ex}")

        return audit_entry
