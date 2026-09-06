"""
Unified Pipeline Orchestrator for VeriAlert Multi-Agent AI Framework.
Executes Phases 1 to 5 end-to-end:
  Stage 1: Multi-source Data Ingestion & Normalization
  Stage 2: Disaster Relevance Classification & Noise Filtering
  Stage 3: spaCy NER Location Extraction & Cached Geocoding
  Stage 4: Semantic Event Clustering & NLI Cross-Source Veracity Scoring
  Stage 5: Factual Public Alert Summarization using T5
Provides real-time execution status, progress %, and structured logging for API & UI.
"""
import asyncio
import logging
import math
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List, Optional

from sqlalchemy import select, delete
from app.db.database import AsyncSessionLocal, init_db
from app.db.models import RawDisasterItemModel, DisasterClusterModel
from app.collectors.collector_manager import CollectorManager
from app.classifier.inference import DisasterRelevanceClassifier
from app.geo.extractor import DisasterLocationExtractor
from app.geo.geocoder import CachedDisasterGeocoder
from app.verification.clusterer import DisasterEventClusterer
from app.verification.nli_verifier import NLIVeracityVerifier
from app.verification.trust_scorer import DeterministicTrustScorer
from app.verification.audit_logger import VeracityAuditLogger
from app.summarizer.alert_generator import FactualAlertSummarizer

logger = logging.getLogger("VeriAlertOrchestrator")

class PipelineOrchestrator:
    _instance: Optional["PipelineOrchestrator"] = None

    def __init__(self):
        self.lock = asyncio.Lock()
        self.status: str = "idle"  # idle, running, completed, error
        self.current_phase: int = 0
        self.phase_name: str = "Ready"
        self.progress_pct: int = 0
        self.logs: List[Dict[str, Any]] = []
        self.started_at: Optional[str] = None
        self.finished_at: Optional[str] = None
        self.last_run_summary: Dict[str, Any] = {}
        self.error_message: Optional[str] = None

    @classmethod
    def get_instance(cls) -> "PipelineOrchestrator":
        if cls._instance is None:
            cls._instance = PipelineOrchestrator()
        return cls._instance

    def _add_log(self, stage: str, message: str, level: str = "INFO"):
        ts = datetime.now(timezone.utc).strftime("%H:%M:%S")
        entry = {
            "timestamp": ts,
            "stage": stage,
            "message": message,
            "level": level
        }
        self.logs.append(entry)
        if len(self.logs) > 200:
            self.logs = self.logs[-200:]
        logger.info(f"[{stage}] {message}")

    def get_status(self) -> Dict[str, Any]:
        return {
            "status": self.status,
            "current_phase": self.current_phase,
            "phase_name": self.phase_name,
            "progress_percent": self.progress_pct,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "last_run_summary": self.last_run_summary,
            "error_message": self.error_message,
            "recent_logs": self.logs[-25:]
        }

    async def run_pipeline(self) -> Dict[str, Any]:
        """Runs the entire 5-stage pipeline asynchronously with mutex lock."""
        if self.lock.locked():
            return {
                "status": "already_running",
                "message": "Pipeline execution is already in progress.",
                "progress_percent": self.progress_pct
            }

        async with self.lock:
            start_wall = time.time()
            self.status = "running"
            self.started_at = datetime.now(timezone.utc).isoformat()
            self.finished_at = None
            self.error_message = None
            self.logs = []
            self.progress_pct = 0

            try:
                self._add_log("INIT", "Initializing database tables and schema...")
                await init_db()

                # STAGE 1: INGESTION
                self.current_phase = 1
                self.phase_name = "Stage 1: Multi-Source Data Ingestion"
                self.progress_pct = 10
                self._add_log("STAGE_1", "Starting ingestion across 5 modular collectors (NewsAPI, GDELT, Reddit, RSS, NDMA)...")

                manager = CollectorManager()
                async with AsyncSessionLocal() as session:
                    ingest_summary = await manager.run_all_collectors(session)
                
                self._add_log("STAGE_1", f"Ingestion finished: {ingest_summary.get('total_collected', 0)} collected, {ingest_summary.get('saved_to_db', 0)} new items saved.")
                self.progress_pct = 25

                # STAGE 2: RELEVANCE CLASSIFICATION
                self.current_phase = 2
                self.phase_name = "Stage 2: Relevance Classification & Filtering"
                self.progress_pct = 35
                self._add_log("STAGE_2", "Loading fine-tuned disaster relevance classifier (0.55 confidence cutoff)...")

                classifier = DisasterRelevanceClassifier()
                self._add_log("STAGE_2", "Relevance classifier initialized successfully.")
                self.progress_pct = 45

                # STAGE 3: GEO-EXTRACTION & GEOCODING
                self.current_phase = 3
                self.phase_name = "Stage 3: spaCy NER & Cached Geocoding"
                self.progress_pct = 50
                self._add_log("STAGE_3", "Extracting geographical entities and resolving coordinates with Nominatim...")

                extractor = DisasterLocationExtractor()
                geocoder = CachedDisasterGeocoder()

                relevant_count = 0
                geocoded_count = 0

                async with AsyncSessionLocal() as session:
                    stmt = select(RawDisasterItemModel).order_by(RawDisasterItemModel.timestamp.desc())
                    result = await session.execute(stmt)
                    items = result.scalars().all()

                    for item in items:
                        text_to_eval = f"{item.title or ''}. {item.raw_text}"
                        classification = classifier.classify_text(text_to_eval[:300])

                        if not classification["is_relevant"]:
                            continue

                        relevant_count += 1
                        geo_extraction = extractor.extract_locations(
                            text_to_eval,
                            location_hint=item.location_text,
                            title=item.title
                        )
                        primary_query = geo_extraction["primary_location"]

                        geo_result = geocoder.geocode(
                            primary_query,
                            state_hint=geo_extraction.get("state"),
                            country_hint=geo_extraction.get("country", "India")
                        )

                        lat = geo_result.get("latitude")
                        lon = geo_result.get("longitude")

                        if lat is not None and lon is not None:
                            geocoded_count += 1

                        item.latitude = lat
                        item.longitude = lon
                        item.location_text = geo_result.get("city") or geo_result.get("state") or primary_query

                        meta = dict(item.raw_metadata or {})
                        meta["geo"] = {
                            "extracted_entities": geo_extraction["extracted_entities"],
                            "primary_location": primary_query,
                            "display_name": geo_result.get("display_name"),
                            "city": geo_result.get("city"),
                            "state": geo_result.get("state"),
                            "country": geo_result.get("country"),
                            "confidence": geo_result.get("confidence", 0.0),
                            "cached": geo_result.get("cached", False)
                        }
                        meta["classification"] = classification
                        item.raw_metadata = meta

                    await session.commit()

                self._add_log("STAGE_3", f"Geo-extraction complete: {relevant_count} relevant items found, {geocoded_count} geocoded with coordinates.")
                self.progress_pct = 65

                # STAGE 4: CLUSTERING & NLI VERACITY VERIFICATION
                self.current_phase = 4
                self.phase_name = "Stage 4: Cross-Source Clustering & NLI Veracity Verification"
                self.progress_pct = 70
                self._add_log("STAGE_4", "Clustering disaster events via all-MiniLM-L6-v2 embeddings and evaluating with DeBERTa-v3 NLI...")

                clusterer = DisasterEventClusterer()
                nli_verifier = NLIVeracityVerifier()
                trust_scorer = DeterministicTrustScorer()

                clusters_formed = 0
                verified_clusters = 0

                async with AsyncSessionLocal() as session:
                    stmt = select(RawDisasterItemModel).where(RawDisasterItemModel.latitude.isnot(None)).order_by(RawDisasterItemModel.timestamp.desc())
                    result = await session.execute(stmt)
                    db_items = result.scalars().all()

                    items_data = []
                    for it in db_items:
                        classification = (it.raw_metadata or {}).get("classification", {})
                        items_data.append({
                            "id": it.id,
                            "source": it.source,
                            "source_type": it.source_type,
                            "title": it.title or "",
                            "raw_text": it.raw_text,
                            "location_text": it.location_text or "India",
                            "latitude": it.latitude,
                            "longitude": it.longitude,
                            "disaster_type": classification.get("disaster_type", "general_disaster"),
                            "is_mock": it.is_mock
                        })

                    clusters = clusterer.cluster_items(items_data)
                    clusters_formed = len(clusters)

                    await session.execute(delete(DisasterClusterModel))

                    for cluster in clusters:
                        nli_res = nli_verifier.verify_cluster(cluster)
                        score_res = trust_scorer.score_cluster(cluster, nli_res)

                        trust_score = score_res["trust_score"]
                        trust_band = score_res["trust_band"]

                        if "VERIFIED" in trust_band:
                            verified_clusters += 1

                        cluster_model = DisasterClusterModel(
                            id=cluster["cluster_id"],
                            event_name=cluster["event_name"],
                            disaster_type=cluster["disaster_type"],
                            location_name=cluster["location_name"],
                            latitude=cluster["latitude"],
                            longitude=cluster["longitude"],
                            trust_score=trust_score,
                            trust_band=trust_band,
                            source_authority_score=score_res["source_authority_score"],
                            corroborating_sources_count=score_res["independent_sources_count"],
                            has_contradiction=score_res["has_contradiction"],
                            nli_agreement_score=score_res["nli_agreement_score"],
                            sources=cluster["sources"],
                            item_ids=cluster["item_ids"]
                        )
                        session.add(cluster_model)

                        # Write auditable record to JSONL and human-readable viva logs
                        VeracityAuditLogger.log_cluster_audit(
                            cluster_id=cluster["cluster_id"],
                            event_name=cluster["event_name"],
                            disaster_type=cluster["disaster_type"],
                            location_name=cluster["location_name"],
                            sources=cluster["sources"],
                            score_res=score_res,
                            nli_res=nli_res
                        )

                    await session.commit()

                self._add_log("STAGE_4", f"Veracity scoring complete: Formed {clusters_formed} clusters ({verified_clusters} multi-source verified).")
                self.progress_pct = 85

                # STAGE 5: FACTUAL ALERT SUMMARIZATION
                self.current_phase = 5
                self.phase_name = "Stage 5: Factual Public Alert Summarization (T5)"
                self.progress_pct = 90
                self._add_log("STAGE_5", "Generating grounded 1-2 sentence emergency alerts using T5...")

                summarizer = FactualAlertSummarizer()
                summarized_count = 0

                async with AsyncSessionLocal() as session:
                    stmt = select(DisasterClusterModel).order_by(DisasterClusterModel.trust_score.desc())
                    result = await session.execute(stmt)
                    clusters = result.scalars().all()

                    items_stmt = select(RawDisasterItemModel)
                    items_result = await session.execute(items_stmt)
                    all_items = {it.id: it for it in items_result.scalars().all()}

                    for c in clusters:
                        member_texts = []
                        for item_id in (c.item_ids or []):
                            if item_id in all_items:
                                it = all_items[item_id]
                                member_texts.append(f"{it.title or ''}. {it.raw_text}")

                        summary = summarizer.generate_alert_summary(
                            event_name=c.event_name,
                            location_name=c.location_name,
                            disaster_type=c.disaster_type,
                            trust_band=c.trust_band,
                            member_texts=member_texts
                        )
                        c.summary = summary
                        summarized_count += 1

                    await session.commit()

                self._add_log("STAGE_5", f"Alert summarization complete: Generated factual emergency summaries for {summarized_count} clusters.")

                elapsed = round(time.time() - start_wall, 2)
                self.status = "completed"
                self.phase_name = "Pipeline Completed"
                self.progress_pct = 100
                self.finished_at = datetime.now(timezone.utc).isoformat()

                self.last_run_summary = {
                    "elapsed_seconds": elapsed,
                    "total_collected": ingest_summary.get("total_collected", 0),
                    "relevant_disasters": relevant_count,
                    "geocoded_locations": geocoded_count,
                    "clusters_formed": clusters_formed,
                    "verified_clusters": verified_clusters,
                    "summarized_alerts": summarized_count,
                    "timestamp": self.finished_at
                }

                self._add_log("COMPLETE", f"End-to-End Pipeline executed successfully in {elapsed}s.")
                return {
                    "status": "completed",
                    "summary": self.last_run_summary
                }

            except Exception as ex:
                logger.exception("Pipeline execution failed:")
                self.status = "error"
                self.error_message = str(ex)
                self._add_log("ERROR", f"Pipeline failed: {str(ex)}", level="ERROR")
                return {
                    "status": "error",
                    "error": str(ex)
                }

orchestrator = PipelineOrchestrator.get_instance()
