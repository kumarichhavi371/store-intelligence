"""
Health endpoint — tells on-call engineers if feeds are live.
"""

from sqlalchemy.orm import Session
from datetime import datetime, timezone, timedelta
from app.database import EventRecord
from app.models import HealthResponse, StoreHealth


def get_health(db: Session) -> HealthResponse:
    now     = datetime.now(timezone.utc)
    now_str = now.strftime("%Y-%m-%dT%H:%M:%SZ")
    stale_threshold = (now - timedelta(minutes=10)).strftime("%Y-%m-%dT%H:%M:%SZ")
    hour_ago        = (now - timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%SZ")

    # Get all distinct store_ids we have data for
    store_ids = [r[0] for r in db.query(EventRecord.store_id).distinct().all()]

    stores = []
    for sid in store_ids:
        last_event = (
            db.query(EventRecord)
              .filter(EventRecord.store_id == sid)
              .order_by(EventRecord.timestamp.desc())
              .first()
        )
        events_last_hour = (
            db.query(EventRecord)
              .filter(EventRecord.store_id == sid)
              .filter(EventRecord.timestamp >= hour_ago)
              .count()
        )

        if last_event is None:
            feed_status = "NO_DATA"
        elif last_event.timestamp < stale_threshold:
            feed_status = "STALE_FEED"
        else:
            feed_status = "LIVE"

        stores.append(StoreHealth(
            store_id         = sid,
            status           = "OK" if feed_status == "LIVE" else "DEGRADED",
            last_event_time  = last_event.timestamp if last_event else None,
            feed_status      = feed_status,
            events_last_hour = events_last_hour
        ))

    return HealthResponse(
        service_status = "OK",
        stores         = stores,
        checked_at     = now_str
    )
