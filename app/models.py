"""
Pydantic models — the shape of every request/response in the API.
"""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum


class EventType(str, Enum):
    ENTRY                  = "ENTRY"
    EXIT                   = "EXIT"
    ZONE_ENTER             = "ZONE_ENTER"
    ZONE_EXIT              = "ZONE_EXIT"
    ZONE_DWELL             = "ZONE_DWELL"
    BILLING_QUEUE_JOIN     = "BILLING_QUEUE_JOIN"
    BILLING_QUEUE_ABANDON  = "BILLING_QUEUE_ABANDON"
    REENTRY                = "REENTRY"


class EventMetadata(BaseModel):
    queue_depth: Optional[int]   = None
    sku_zone:    Optional[str]   = None
    session_seq: int             = 0


class StoreEvent(BaseModel):
    event_id:   str
    store_id:   str
    camera_id:  str
    visitor_id: str
    event_type: EventType
    timestamp:  str
    zone_id:    Optional[str]    = None
    dwell_ms:   int              = 0
    is_staff:   bool             = False
    confidence: float            = Field(ge=0.0, le=1.0)
    metadata:   EventMetadata    = Field(default_factory=EventMetadata)


class IngestRequest(BaseModel):
    events: List[StoreEvent]


class IngestResponse(BaseModel):
    accepted:  int
    rejected:  int
    duplicate: int
    errors:    List[dict] = []


class ZoneDwellMetric(BaseModel):
    zone_id:      str
    avg_dwell_ms: float
    visit_count:  int


class StoreMetrics(BaseModel):
    store_id:          str
    unique_visitors:   int
    conversion_rate:   float
    avg_dwell_ms:      float
    queue_depth:       int
    abandonment_rate:  float
    zone_dwell:        List[ZoneDwellMetric]
    as_of:             str


class FunnelStage(BaseModel):
    stage:      str
    count:      int
    dropoff_pct: float


class FunnelResponse(BaseModel):
    store_id: str
    stages:   List[FunnelStage]


class HeatmapZone(BaseModel):
    zone_id:          str
    visit_frequency:  int
    avg_dwell_ms:     float
    normalised_score: float
    data_confidence:  str   # "HIGH" / "LOW"


class HeatmapResponse(BaseModel):
    store_id: str
    zones:    List[HeatmapZone]


class Anomaly(BaseModel):
    anomaly_type:     str
    severity:         str   # INFO / WARN / CRITICAL
    description:      str
    suggested_action: str
    detected_at:      str


class AnomalyResponse(BaseModel):
    store_id:  str
    anomalies: List[Anomaly]


class StoreHealth(BaseModel):
    store_id:          str
    status:            str
    last_event_time:   Optional[str]
    feed_status:       str   # LIVE / STALE_FEED / NO_DATA
    events_last_hour:  int


class HealthResponse(BaseModel):
    service_status: str
    stores:         List[StoreHealth]
    checked_at:     str