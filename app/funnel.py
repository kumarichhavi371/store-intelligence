"""
Conversion funnel — Entry → Zone Visit → Billing → Purchase.
Uses sessions as the unit (not raw events).
Re-entries don't double-count a visitor.
"""

from sqlalchemy.orm import Session
from app.database import EventRecord
from app.models import FunnelResponse, FunnelStage


def get_funnel(store_id: str, db: Session) -> FunnelResponse:

    # All non-staff events
    events = (
        db.query(EventRecord)
        .filter(EventRecord.store_id == store_id)
        .filter(EventRecord.is_staff == False)
        .all()
    )

    # Collect unique visitors per stage
    entered_visitors = set()
    zone_visitors = set()
    billing_visitors = set()
    purchase_visitors = set()

    for e in events:
        if e.event_type in ("ENTRY", "REENTRY"):
            entered_visitors.add(e.visitor_id)

        if (
            e.event_type in ("ZONE_ENTER", "ZONE_DWELL")
            and e.zone_id == "MAIN_FLOOR"
        ):
            zone_visitors.add(e.visitor_id)

        if e.zone_id == "BILLING_ZONE":
         billing_visitors.add(e.visitor_id)

    # Heuristic: reaching billing zone indicates purchase intent
        purchase_visitors.add(e.visitor_id)
    # Funnel sanity checks
        entry_count = len(entered_visitors)

    zone_count = min(len(zone_visitors), entry_count)
    billing_count = min(len(billing_visitors), zone_count)
    purchase_count = min(len(purchase_visitors), billing_count)

    total = max(entry_count, 1)

    stages = [
        FunnelStage(
            stage="Entry",
            count=entry_count,
            dropoff_pct=0.0
        ),
        FunnelStage(
            stage="Zone Visit",
            count=zone_count,
            dropoff_pct=round((1 - zone_count / total) * 100, 1)
        ),
        FunnelStage(
            stage="Billing",
            count=billing_count,
            dropoff_pct=round((1 - billing_count / total) * 100, 1)
        ),
        FunnelStage(
            stage="Purchase",
            count=purchase_count,
            dropoff_pct=round((1 - purchase_count / total) * 100, 1)
        ),
    ]

    return FunnelResponse(
        store_id=store_id,
        stages=stages
    )