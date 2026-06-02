"""
Real-time metric computation.
Reads events from DB and computes store KPIs.
"""

from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timezone, timedelta
from app.database import EventRecord
from app.models import StoreMetrics, ZoneDwellMetric


def get_store_metrics(store_id: str, db: Session) -> StoreMetrics:
    # Today's date window
    today_start = datetime.now(timezone.utc).replace(
        hour=0, minute=0, second=0, microsecond=0
    ).strftime("%Y-%m-%dT%H:%M:%SZ")

    # Base query — exclude staff
    base = (db.query(EventRecord)
          .filter(EventRecord.store_id == store_id)
          .filter(EventRecord.is_staff == False))

    # ── Unique visitors (ENTRY events, unique visitor_id) ──
    unique_visitors = (
        base.filter(EventRecord.event_type == "ENTRY")
            .with_entities(EventRecord.visitor_id)
            .distinct()
            .count()
    )

    # ── Visitors who reached billing zone ──
    billing_visitors = (
        base.filter(EventRecord.zone_id == "BILLING_ZONE")
            .with_entities(EventRecord.visitor_id)
            .distinct()
            .count()
    )

    # ── Conversion rate ──
    conversion_rate = 0.0
    if unique_visitors > 0:
        conversion_rate = round(billing_visitors / unique_visitors, 4)

    # ── Average dwell across all zones ──
    avg_dwell_row = (
        base.filter(EventRecord.event_type == "ZONE_DWELL")
            .with_entities(func.avg(EventRecord.dwell_ms))
            .scalar()
    )
    avg_dwell_ms = float(avg_dwell_row or 0)

    # ── Current queue depth ──
    latest_queue = (
        db.query(EventRecord)
          .filter(EventRecord.store_id == store_id)
          .filter(EventRecord.queue_depth != None)
          .order_by(EventRecord.timestamp.desc())
          .first()
    )
    queue_depth = latest_queue.queue_depth if latest_queue else 0

    # ── Abandonment rate ──
    abandon_count = (
        base.filter(EventRecord.event_type == "BILLING_QUEUE_ABANDON")
            .count()
    )
    queue_join_count = (
        base.filter(EventRecord.event_type == "BILLING_QUEUE_JOIN")
            .count()
    )
    abandonment_rate = 0.0
    if queue_join_count > 0:
        abandonment_rate = round(abandon_count / queue_join_count, 4)

    # ── Per-zone dwell ──
    zone_rows = (
        base.filter(EventRecord.event_type == "ZONE_DWELL")
            .filter(EventRecord.zone_id != None)
            .with_entities(
                EventRecord.zone_id,
                func.avg(EventRecord.dwell_ms).label("avg_dwell"),
                func.count(EventRecord.visitor_id).label("visits")
            )
            .group_by(EventRecord.zone_id)
            .all()
    )
    zone_dwell = [
        ZoneDwellMetric(zone_id=r.zone_id,
                        avg_dwell_ms=float(r.avg_dwell or 0),
                        visit_count=r.visits)
        for r in zone_rows
    ]

    return StoreMetrics(
        store_id         = store_id,
        unique_visitors  = unique_visitors,
        conversion_rate  = conversion_rate,
        avg_dwell_ms     = avg_dwell_ms,
        queue_depth      = queue_depth or 0,
        abandonment_rate = abandonment_rate,
        zone_dwell       = zone_dwell,
        as_of            = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    )