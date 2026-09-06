import sys
from pathlib import Path

# Add backend directory to sys.path
backend_dir = Path(__file__).resolve().parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.verification.audit_logger import VeracityAuditLogger

def test_audit():
    entry = VeracityAuditLogger.log_cluster_audit(
        cluster_id="audit-test-101",
        event_name="Flash Floods in Brahmaputra River Basin",
        disaster_type="flood",
        location_name="Guwahati, Assam, India",
        sources=["NewsAPI (The Times of India)", "GDELT", "IMD Weather Bulletin"],
        score_res={
            "source_authority_score": 1.0,
            "corroboration_score": 0.792,
            "independent_sources_count": 3,
            "contradiction_penalty": 0.0,
            "has_contradiction": False,
            "nli_agreement_score": 0.92,
            "trust_score": 0.896,
            "trust_band": "VERIFIED (MULTI-SOURCE)"
        },
        nli_res={
            "has_contradiction": False,
            "nli_agreement_score": 0.92
        }
    )
    print("SUCCESS: Audit entry logged.")
    print("Viva Summary:", entry["viva_defense_summary"])

if __name__ == "__main__":
    test_audit()
