"""
Anomaly detection — queue spikes, conversion drops, dead zones.
"""

from sqlalchemy.orm import Session
from datetime import datetime, timezone, timedelta
from app.database import EventRecord
from app.models import AnomalyResponse, Anomaly


def get_anomalies(store_id: str, db: Session) -> AnomalyResponse:
    now        = datetime.now(timezone.utc)
    now_str    = now.strftime("%Y-%m-%dT%H:%M:%SZ")
    hour_ago   = (now - timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
    day_ago    = (now - timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
    seven_days = (now - timedelta(days=7)).strftime("%Y-%m-%dT%H:%M:%SZ")
    thirty_min = (now - timedelta(minutes=30)).strftime("%Y-%m-%dT%H:%M:%SZ")

    anomalies = []

    # ── 1. Queue spike: more than 5 people in billing right now ──
    latest_queue = (
        db.query(EventRecord)
          .filter(EventRecord.store_id == store_id)
          .filter(EventRecord.queue_depth != None)
          .order_by(EventRecord.timestamp.desc())
          .first()
    )
    if latest_queue and (latest_queue.queue_depth or 0) > 5:
        anomalies.append(Anomaly(
            anomaly_type     = "BILLING_QUEUE_SPIKE",
            severity         = "CRITICAL" if latest_queue.queue_depth > 8 else "WARN",
            description      = f"Queue depth is {latest_queue.queue_depth} at billing counter.",
            suggested_action = "Open an additional billing counter immediately.",
            detected_at      = now_str
        ))

    # ── 2. Conversion drop vs 7-day average ──
    def conversion_for_period(start: str, end: str) -> float:
        visitors = (db.query(EventRecord)
                      .filter(EventRecord.store_id == store_id)
                      .filter(EventRecord.is_staff == False)
                      .filter(EventRecord.event_type == "ENTRY")
                      .filter(EventRecord.timestamp >= start)
                      .filter(EventRecord.timestamp <= end)
                      .with_entities(EventRecord.visitor_id).distinct().count())
        buyers = (db.query(EventRecord)
                    .filter(EventRecord.store_id == store_id)
                    .filter(EventRecord.is_staff == False)
                    .filter(EventRecord.zone_id == "BILLING_ZONE")
                    .filter(EventRecord.timestamp >= start)
                    .filter(EventRecord.timestamp <= end)
                    .with_entities(EventRecord.visitor_id).distinct().count())
        return buyers / visitors if visitors > 0 else 0.0

    today_conv   = conversion_for_period(day_ago, now_str)
    week_conv    = conversion_for_period(seven_days, now_str)

    if week_conv > 0 and today_conv < week_conv * 0.7:
        anomalies.append(Anomaly(
            anomaly_type     = "CONVERSION_DROP",
            severity         = "WARN",
            description      = f"Today's conversion {today_conv:.1%} is 30%+ below 7-day avg {week_conv:.1%}.",
            suggested_action = "Check staff presence on floor and review product placement.",
            detected_at      = now_str
        ))

    # ── 3. Dead zone: no visits in 30 min ──
    recent_zone_event = (
        db.query(EventRecord)
          .filter(EventRecord.store_id == store_id)
          .filter(EventRecord.is_staff == False)
          .filter(EventRecord.event_type.in_(["ZONE_ENTER", "ZONE_DWELL"]))
          .filter(EventRecord.zone_id == "MAIN_FLOOR")
          .filter(EventRecord.timestamp >= thirty_min)
          .first()
    )
    if not recent_zone_event:
        anomalies.append(Anomaly(
            anomaly_type     = "DEAD_ZONE",
            severity         = "INFO",
            description      = "No customer visits to MAIN_FLOOR in the last 30 minutes.",
            suggested_action = "Check if the zone is accessible and attractively merchandised.",
            detected_at      = now_str
        ))

    return AnomalyResponse(store_id=store_id, anomalies=anomalies)
