"""
Conversion funnel — Entry → Zone Visit → Billing → Purchase.
Uses sessions as the unit (not raw events).
Re-entries don't double-count a visitor.
"""

from sqlalchemy.orm import Session
from datetime import datetime, timezone
from app.database import EventRecord
from app.models import FunnelResponse, FunnelStage


def get_funnel(store_id: str, db: Session) -> FunnelResponse:
    today_start = datetime.now(timezone.utc).replace(
        hour=0, minute=0, second=0, microsecond=0
    ).strftime("%Y-%m-%dT%H:%M:%SZ")

    # All non-staff events today
    events = (db.query(EventRecord)
                .filter(EventRecord.store_id == store_id)
                .filter(EventRecord.is_staff == False)
                .filter(EventRecord.timestamp >= today_start)
                .all())

    # Collect unique visitors per stage
    entered_visitors  = set()
    zone_visitors     = set()
    billing_visitors  = set()
    purchase_visitors = set()  # approximated by billing zone dwellers

    for e in events:
        if e.event_type == "ENTRY" or e.event_type == "REENTRY":
            entered_visitors.add(e.visitor_id)
        if e.event_type in ("ZONE_ENTER", "ZONE_DWELL") and e.zone_id == "MAIN_FLOOR":
            zone_visitors.add(e.visitor_id)
        if e.zone_id == "BILLING_ZONE":
            billing_visitors.add(e.visitor_id)
            # Visitors who dwelled > 60s in billing = likely purchased
            if e.event_type == "ZONE_DWELL" and e.dwell_ms >= 60000:
                purchase_visitors.add(e.visitor_id)

    total = len(entered_visitors) or 1  # avoid division by zero

    stages = [
        FunnelStage(stage="Entry",       count=len(entered_visitors),
                    dropoff_pct=0.0),
        FunnelStage(stage="Zone Visit",  count=len(zone_visitors),
                    dropoff_pct=round((1 - len(zone_visitors)/total)*100, 1)),
        FunnelStage(stage="Billing",     count=len(billing_visitors),
                    dropoff_pct=round((1 - len(billing_visitors)/total)*100, 1)),
        FunnelStage(stage="Purchase",    count=len(purchase_visitors),
                    dropoff_pct=round((1 - len(purchase_visitors)/total)*100, 1)),
    ]

    return FunnelResponse(store_id=store_id, stages=stages)