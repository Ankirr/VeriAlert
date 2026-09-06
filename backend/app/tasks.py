"""
Celery Background Tasks for Disaster Data Aggregation & Verification.
Executes the unified 5-stage pipeline via Celery Worker or Celery Beat scheduler.
"""
import asyncio
import logging
from typing import Dict, Any
from app.celery_app import celery_app
from app.orchestrator import orchestrator

logger = logging.getLogger("CeleryTasks")

@celery_app.task(name="app.tasks.run_disaster_pipeline_task", bind=True)
def run_disaster_pipeline_task(self) -> Dict[str, Any]:
    """
    Celery task that executes the entire multi-agent disaster framework pipeline.
    Can be scheduled periodically via Celery Beat or triggered on demand.
    """
    logger.info(f"[Celery] Starting disaster pipeline execution (Task ID: {self.request.id})...")
    
    try:
        # Run async orchestrator pipeline in event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(orchestrator.run_pipeline())
        loop.close()

        logger.info(f"[Celery] Disaster pipeline completed successfully: {result.get('status')}")
        return {
            "task_id": self.request.id,
            "status": result.get("status"),
            "summary": result.get("summary", {})
        }
    except Exception as ex:
        logger.exception(f"[Celery] Pipeline task execution failed: {ex}")
        return {
            "task_id": self.request.id,
            "status": "error",
            "error": str(ex)
        }
