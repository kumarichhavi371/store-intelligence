"""
FastAPI entrypoint — defines all API endpoints.
"""

import logging
import time
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI, Depends, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from app.database   import get_db, create_tables
from app.models     import (IngestRequest, IngestResponse, StoreMetrics,
                             FunnelResponse, HeatmapResponse,
                             AnomalyResponse, HealthResponse)
from app.ingestion  import ingest_events
from app.metrics    import get_store_metrics
from app.funnel     import get_funnel
from app.anomalies  import get_anomalies
from app.health     import get_health
from app.heatmap    import get_heatmap

# ── Structured logging ──
logging.basicConfig(
    level=logging.INFO,
    format='{"time":"%(asctime)s","level":"%(levelname)s","msg":"%(message)s"}'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Create DB tables on startup."""
    create_tables()
    logger.info("Database tables created / verified.")
    yield


app = FastAPI(
    title="Store Intelligence API",
    version="1.0.0",
    description="Real-time retail analytics from CCTV events.",
    lifespan=lifespan
)

# Allow browser dashboard to call the API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Request logging middleware ──
@app.middleware("http")
async def log_requests(request: Request, call_next):
    trace_id = str(uuid.uuid4())[:8]
    start    = time.time()
    response = await call_next(request)
    latency  = int((time.time() - start) * 1000)

    store_id = request.path_params.get("store_id", "-")
    logger.info(
        f"trace_id={trace_id} store_id={store_id} "
        f"endpoint={request.url.path} method={request.method} "
        f"status={response.status_code} latency_ms={latency}"
    )
    return response


# ──────────────────────────────────────────────
# ENDPOINTS
# ──────────────────────────────────────────────

@app.post("/events/ingest", response_model=IngestResponse)
async def ingest(request: IngestRequest, db: Session = Depends(get_db)):
    """
    Accept up to 500 events per batch.
    Idempotent by event_id — safe to call twice with same payload.
    Returns partial success on malformed events.
    """
    if len(request.events) > 500:
        raise HTTPException(status_code=400,
                            detail="Batch size exceeds 500 events.")
    try:
        return ingest_events(request, db)
    except Exception as e:
        logger.error(f"Ingest error: {e}")
        raise HTTPException(status_code=503,
                            detail={"error": "Database unavailable", "detail": str(e)})


@app.get("/stores/{store_id}/metrics", response_model=StoreMetrics)
async def metrics(store_id: str, db: Session = Depends(get_db)):
    """Real-time store metrics — visitors, conversion, dwell, queue."""
    try:
        return get_store_metrics(store_id, db)
    except Exception as e:
        logger.error(f"Metrics error: {e}")
        raise HTTPException(status_code=503,
                            detail={"error": "Could not compute metrics", "detail": str(e)})


@app.get("/stores/{store_id}/funnel", response_model=FunnelResponse)
async def funnel(store_id: str, db: Session = Depends(get_db)):
    """Conversion funnel: Entry → Zone → Billing → Purchase."""
    try:
        return get_funnel(store_id, db)
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))


@app.get("/stores/{store_id}/heatmap", response_model=HeatmapResponse)
async def heatmap(store_id: str, db: Session = Depends(get_db)):
    """Zone heatmap — visit frequency + dwell, normalised 0–100."""
    try:
        return get_heatmap(store_id, db)
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))


@app.get("/stores/{store_id}/anomalies", response_model=AnomalyResponse)
async def anomalies(store_id: str, db: Session = Depends(get_db)):
    """Detect active anomalies: queue spike, conversion drop, dead zone."""
    try:
        return get_anomalies(store_id, db)
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))


@app.get("/health", response_model=HealthResponse)
async def health(db: Session = Depends(get_db)):
    """Service health + per-store feed status."""
    try:
        return get_health(db)
    except Exception as e:
        raise HTTPException(status_code=503,
                            detail={"error": "Health check failed", "detail": str(e)})