"""
Zone heatmap — visit frequency + avg dwell, normalised 0-100.
"""

from sqlalchemy.orm import Session
from sqlalchemy import func
from app.database import EventRecord
from app.models import HeatmapResponse, HeatmapZone


def get_heatmap(store_id: str, db: Session) -> HeatmapResponse:

    rows = (
        db.query(
            EventRecord.zone_id,
            func.count(EventRecord.visitor_id).label("freq"),
            func.avg(EventRecord.dwell_ms).label("avg_dwell"),
            func.count(EventRecord.visitor_id.distinct()).label("unique_visitors")
        )
        .filter(EventRecord.store_id == store_id)
        .filter(EventRecord.is_staff == False)
        .filter(EventRecord.zone_id != None)
        .filter(EventRecord.event_type.in_(["ZONE_ENTER", "ZONE_DWELL"]))
        .group_by(EventRecord.zone_id)
        .all()
    )

    if not rows:
        return HeatmapResponse(store_id=store_id, zones=[])

    max_freq = max(r.freq for r in rows) or 1

    zones = []
    for r in rows:
        normalised = round((r.freq / max_freq) * 100, 1)
        confidence = "HIGH" if r.unique_visitors >= 20 else "LOW"

        zones.append(
            HeatmapZone(
                zone_id=r.zone_id,
                visit_frequency=r.freq,
                avg_dwell_ms=float(r.avg_dwell or 0),
                normalised_score=normalised,
                data_confidence=confidence
            )
        )

    return HeatmapResponse(
        store_id=store_id,
        zones=zones
    )