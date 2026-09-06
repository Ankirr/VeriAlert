"""
FastAPI REST API for VeriAlert Disaster Response & Veracity Verification System.
Exposes filtered incident clusters, statistics, mathematical audit breakdowns, and GeoJSON coordinates.
Serves the interactive geospatial frontend dashboard at / and provides live pipeline orchestration.
"""
import math
import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional, List, Dict, Any

from fastapi import FastAPI, Depends, HTTPException, Query, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db.database import get_db, init_db, AsyncSessionLocal
from app.db.models import DisasterClusterModel, RawDisasterItemModel
from app.orchestrator import orchestrator

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("VeriAlertAPI")

CURRENT_DIR = Path(__file__).resolve().parent
STATIC_DIR = CURRENT_DIR / "static"
STATIC_DIR.mkdir(parents=True, exist_ok=True)

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing VeriAlert API services...")
    await init_db()
    yield
    logger.info("Shutting down VeriAlert API services...")

app = FastAPI(
    title="VeriAlert API",
    description="Multi-Agent Real-Time Disaster Aggregation & NLI Veracity Verification Platform",
    version="1.1.0",
    lifespan=lifespan
)

# Enable CORS for cross-origin browser access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files directory
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

def compute_trust_breakdown(cluster: DisasterClusterModel) -> Dict[str, Any]:
    """Computes a detailed mathematical breakdown of the deterministic trust score for audit/viva defense."""
    w_source = 0.50
    w_corrob = 0.50
    s_auth = cluster.source_authority_score or 0.65
    n_indep = cluster.corroborating_sources_count or len(cluster.sources or [])
    
    if n_indep <= 1:
        norm_corrob = 0.0
    else:
        norm_corrob = min(1.0, math.log10(float(n_indep)) / math.log10(4.0))

    has_contra = cluster.has_contradiction
    penalty = 0.35 if has_contra else (0.15 if (cluster.nli_agreement_score or 1.0) < 0.60 else 0.0)
    
    sources_text = ", ".join(cluster.sources or ["Single outlet"])
    if has_contra:
        audit_exp = (
            f"Factual or numerical contradictions detected across claims by DeBERTa-v3 NLI. "
            f"A heavy contradiction penalty of -{penalty:.2f} was deducted, classifying this event as DISPUTED "
            f"(Score: {cluster.trust_score * 100:.1f}%)."
        )
    elif "VERIFIED" in (cluster.trust_band or "").upper():
        audit_exp = (
            f"Corroborated across {n_indep} distinct outlets ({sources_text}) with high source credibility "
            f"(S_auth = {s_auth:.2f}) and strong semantic alignment ({cluster.nli_agreement_score * 100:.0f}%). "
            f"Certified as VERIFIED with deterministic trust score of {cluster.trust_score * 100:.1f}%."
        )
    elif "CREDIBLE" in (cluster.trust_band or "").upper() or "LIKELY" in (cluster.trust_band or "").upper():
        audit_exp = (
            f"Reported by reputable source ({sources_text}) with credibility S_auth = {s_auth:.2f}. "
            f"Classified as CREDIBLE/DEVELOPING ({cluster.trust_score * 100:.1f}%). Awaiting second independent confirmation "
            f"to reach verified threshold (>= 75%)."
        )
    else:
        audit_exp = (
            f"Crowdsourced or single-source unverified alert from {sources_text}. "
            f"Current confidence score is {cluster.trust_score * 100:.1f}%."
        )

    return {
        "formula": "Trust = (w_source · S_auth) + (w_corrob · log10(N_indep)/log10(4)) − Penalty_contradiction",
        "weights": {"w_source": w_source, "w_corrob": w_corrob},
        "components": {
            "source_authority": {
                "symbol": "S_auth",
                "score": round(s_auth, 4),
                "weight": w_source,
                "weighted_value": round(w_source * s_auth, 4),
                "description": f"Highest authority among reporting sources ({sources_text})"
            },
            "corroboration": {
                "symbol": "Corrob_Factor",
                "independent_sources_count": n_indep,
                "score": round(norm_corrob, 4),
                "weight": w_corrob,
                "weighted_value": round(w_corrob * norm_corrob, 4),
                "description": f"{n_indep} independent reporting outlets (log-scaled against 4-outlet saturation)"
            },
            "contradiction_penalty": {
                "symbol": "Penalty_contradiction",
                "has_contradiction": has_contra,
                "penalty_value": round(penalty, 4),
                "description": "Deducted if DeBERTa-v3 detects factual or numerical contradiction between claims"
            },
            "nli_agreement": {
                "score": round(cluster.nli_agreement_score, 4),
                "percentage": f"{round(cluster.nli_agreement_score * 100)}%"
            }
        },
        "final_trust_score": round(cluster.trust_score, 4),
        "trust_band": cluster.trust_band,
        "veracity_band": cluster.trust_band,
        "audit_explanation": audit_exp
    }

@app.get("/", response_class=FileResponse)
async def serve_dashboard():
    """Serves the interactive geospatial dashboard."""
    index_path = STATIC_DIR / "index.html"
    if not index_path.exists():
        raise HTTPException(status_code=404, detail="Dashboard index.html not found.")
    return FileResponse(str(index_path))

@app.get("/api/health")
async def health_check():
    """Returns system service health status."""
    pg_status = "connected"
    try:
        async with AsyncSessionLocal() as session:
            await session.execute(select(func.count(DisasterClusterModel.id)))
    except Exception as e:
        pg_status = f"error: {str(e)}"

    return {
        "status": "online",
        "service": "VeriAlert Multi-Agent Disaster Intelligence System",
        "database": pg_status,
        "environment": "production-ready"
    }

@app.get("/api/config")
async def get_client_config():
    """Returns public client configurations including basemap credentials."""
    return {
        "carto_api_key": settings.CARTO_API_KEY,
        "project_name": settings.PROJECT_NAME
    }

@app.get("/api/stats")
async def get_system_stats(session: AsyncSession = Depends(get_db)):
    """Returns real-time analytics KPI metrics."""
    stmt = select(DisasterClusterModel)
    result = await session.execute(stmt)
    clusters = result.scalars().all()

    total_clusters = len(clusters)
    total_reports = sum(len(c.item_ids or []) for c in clusters)
    
    veracity_counts = {
        "verified": 0,
        "credible": 0,
        "unverified": 0,
        "disputed": 0
    }
    
    type_counts: Dict[str, int] = {}
    trust_scores = []

    for c in clusters:
        band = (c.trust_band or "").upper()
        if "VERIFIED" in band:
            veracity_counts["verified"] += 1
        elif "CREDIBLE" in band or "LIKELY" in band:
            veracity_counts["credible"] += 1
        elif "DISPUTED" in band:
            veracity_counts["disputed"] += 1
        else:
            veracity_counts["unverified"] += 1

        dtype = c.disaster_type or "other"
        type_counts[dtype] = type_counts.get(dtype, 0) + 1
        trust_scores.append(c.trust_score)

    avg_trust = round(sum(trust_scores) / len(trust_scores), 4) if trust_scores else 0.0

    return {
        "total_clusters": total_clusters,
        "total_underlying_reports": total_reports,
        "average_trust_score": avg_trust,
        "veracity_breakdown": veracity_counts,
        "disaster_type_breakdown": type_counts
    }

@app.get("/api/regions")
async def get_regions(session: AsyncSession = Depends(get_db)):
    """Returns a list of distinct geographic regions/locations present in current alerts."""
    stmt = select(DisasterClusterModel.location_name).distinct()
    result = await session.execute(stmt)
    raw_locations = result.scalars().all()
    
    regions_set = set()
    for loc in raw_locations:
        if loc:
            parts = [p.strip() for p in loc.split(",") if p.strip()]
            for p in parts:
                if len(p) > 2 and p.lower() not in ["india", "district", "city"]:
                    regions_set.add(p)
            regions_set.add(loc.strip())
            
    sorted_regions = sorted(list(regions_set))
    return {"regions": sorted_regions}

@app.get("/api/alerts")
async def get_alerts(
    disaster_type: Optional[str] = Query(None, description="Filter by disaster type (e.g. flood, landslide)"),
    veracity_band: Optional[str] = Query(None, description="Filter by veracity band (e.g. VERIFIED, CREDIBLE, DISPUTED)"),
    region: Optional[str] = Query(None, description="Filter by region, state, or city name"),
    severity: Optional[str] = Query(None, description="Filter by severity/trust band: verified, developing, disputed, unverified"),
    min_trust: Optional[float] = Query(None, ge=0.0, le=1.0, description="Minimum trust score cutoff"),
    limit: int = Query(100, ge=1, le=200),
    session: AsyncSession = Depends(get_db)
):
    """Lists disaster incident clusters with flexible filtering by calamity, veracity, region, or severity."""
    stmt = select(DisasterClusterModel).order_by(DisasterClusterModel.trust_score.desc())
    
    if disaster_type and disaster_type.lower() != "all":
        stmt = stmt.where(DisasterClusterModel.disaster_type == disaster_type.lower())

    if min_trust is not None:
        stmt = stmt.where(DisasterClusterModel.trust_score >= min_trust)

    result = await session.execute(stmt)
    clusters = result.scalars().all()

    # Filter by veracity band if provided
    if veracity_band and veracity_band.lower() != "all":
        band_target = veracity_band.upper()
        clusters = [c for c in clusters if band_target in (c.trust_band or "").upper()]

    # Filter by severity (alias for veracity bands)
    if severity and severity.lower() != "all":
        sev = severity.lower()
        if sev == "verified":
            clusters = [c for c in clusters if "VERIFIED" in (c.trust_band or "").upper()]
        elif sev in ["developing", "credible"]:
            clusters = [c for c in clusters if "CREDIBLE" in (c.trust_band or "").upper() or "LIKELY" in (c.trust_band or "").upper()]
        elif sev == "disputed":
            clusters = [c for c in clusters if "DISPUTED" in (c.trust_band or "").upper()]
        elif sev == "unverified":
            clusters = [c for c in clusters if "UNVERIFIED" in (c.trust_band or "").upper()]

    # Filter by region/location name
    if region and region.lower() != "all":
        reg_target = region.lower()
        clusters = [c for c in clusters if reg_target in (c.location_name or "").lower() or reg_target in (c.event_name or "").lower()]

    return [c.to_dict() for c in clusters[:limit]]

@app.get("/api/alerts/{cluster_id}")
async def get_alert_detail(cluster_id: str, session: AsyncSession = Depends(get_db)):
    """Returns detailed cluster metadata, member reports, and mathematical audit breakdown."""
    stmt = select(DisasterClusterModel).where(DisasterClusterModel.id == cluster_id)
    result = await session.execute(stmt)
    cluster = result.scalar_one_or_none()

    if not cluster:
        raise HTTPException(status_code=404, detail="Incident cluster not found.")

    # Retrieve all underlying member raw items
    item_ids = cluster.item_ids or []
    items_stmt = select(RawDisasterItemModel).where(RawDisasterItemModel.id.in_(item_ids))
    items_result = await session.execute(items_stmt)
    raw_items = items_result.scalars().all()

    detail = cluster.to_dict()
    detail["member_reports"] = [
        {
            "id": item.id,
            "source": item.source,
            "source_type": item.source_type,
            "title": item.title,
            "raw_text": item.raw_text,
            "url": item.url,
            "timestamp": item.timestamp.isoformat() if item.timestamp else None,
            "is_mock": item.is_mock
        }
        for item in raw_items
    ]

    # Attach mathematical breakdown for audit / viva presentation
    detail["trust_score_breakdown"] = compute_trust_breakdown(cluster)
    return detail

@app.get("/api/map/points")
async def get_map_points(
    disaster_type: Optional[str] = Query(None),
    veracity_band: Optional[str] = Query(None),
    region: Optional[str] = Query(None),
    severity: Optional[str] = Query(None),
    session: AsyncSession = Depends(get_db)
):
    """Returns GeoJSON FeatureCollection formatted for Leaflet map markers."""
    stmt = select(DisasterClusterModel)
    if disaster_type and disaster_type.lower() != "all":
        stmt = stmt.where(DisasterClusterModel.disaster_type == disaster_type.lower())

    result = await session.execute(stmt)
    clusters = result.scalars().all()

    features = []
    for c in clusters:
        band = (c.trust_band or "").upper()
        if veracity_band and veracity_band.lower() != "all" and veracity_band.upper() not in band:
            continue

        if severity and severity.lower() != "all":
            sev = severity.lower()
            if sev == "verified" and "VERIFIED" not in band:
                continue
            if sev in ["developing", "credible"] and ("CREDIBLE" not in band and "LIKELY" not in band):
                continue
            if sev == "disputed" and "DISPUTED" not in band:
                continue
            if sev == "unverified" and "UNVERIFIED" not in band:
                continue

        if region and region.lower() != "all":
            reg_target = region.lower()
            if reg_target not in (c.location_name or "").lower() and reg_target not in (c.event_name or "").lower():
                continue

        # Determine visual color category
        if "VERIFIED" in band:
            color_theme = "green"
            severity_code = "high_trust"
        elif "DISPUTED" in band:
            color_theme = "red"
            severity_code = "disputed"
        elif "CREDIBLE" in band or "LIKELY" in band:
            color_theme = "amber"
            severity_code = "developing"
        else:
            color_theme = "grey"
            severity_code = "unverified"

        features.append({
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [c.longitude, c.latitude]
            },
            "properties": {
                "id": c.id,
                "event_name": c.event_name,
                "disaster_type": c.disaster_type,
                "location_name": c.location_name,
                "trust_score": c.trust_score,
                "trust_band": c.trust_band,
                "color_theme": color_theme,
                "severity_code": severity_code,
                "summary": c.summary or f"{c.disaster_type.title()} reported in {c.location_name}.",
                "source_count": len(c.sources or []),
                "report_count": len(c.item_ids or []),
                "sources": c.sources
            }
        })

    return {
        "type": "FeatureCollection",
        "features": features
    }

# ==============================================================================
# PIPELINE ORCHESTRATION & TRIGGER ENDPOINTS
# ==============================================================================

@app.post("/api/pipeline/trigger")
async def trigger_pipeline(background_tasks: BackgroundTasks):
    """
    Triggers the end-to-end multi-agent pipeline (Phases 1 to 5) asynchronously.
    """
    if orchestrator.lock.locked():
        return {
            "status": "already_running",
            "message": "Pipeline execution is currently running. Please observe live progress.",
            "current_phase": orchestrator.current_phase,
            "phase_name": orchestrator.phase_name,
            "progress_percent": orchestrator.progress_pct
        }

    background_tasks.add_task(orchestrator.run_pipeline)
    return {
        "status": "started",
        "message": "End-to-End Disaster Pipeline triggered. Tracking execution...",
        "progress_percent": 0
    }

@app.get("/api/pipeline/status")
async def get_pipeline_status():
    """Returns the live execution state, progress percent, and step logs of the pipeline."""
    return orchestrator.get_status()
