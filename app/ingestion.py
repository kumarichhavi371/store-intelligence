from sqlalchemy.orm import Session
from app.models import IngestRequest, IngestResponse
from app.database import EventRecord
import logging

logger = logging.getLogger(__name__)


def ingest_events(request: IngestRequest, db: Session) -> IngestResponse:
    accepted  = 0
    rejected  = 0
    duplicate = 0
    errors    = []

    for event in request.events:
        try:
            existing = db.query(EventRecord).filter(
                EventRecord.event_id == event.event_id
            ).first()
            if existing:
                duplicate += 1
                continue
            record = EventRecord(
                event_id    = event.event_id,
                store_id    = event.store_id,
                camera_id   = event.camera_id,
                visitor_id  = event.visitor_id,
                event_type  = event.event_type.value,
                timestamp   = event.timestamp,
                zone_id     = event.zone_id,
                dwell_ms    = event.dwell_ms,
                is_staff    = event.is_staff,
                confidence  = event.confidence,
                queue_depth = event.metadata.queue_depth,
                sku_zone    = event.metadata.sku_zone,
                session_seq = event.metadata.session_seq,
            )
            db.add(record)
            accepted += 1
        except Exception as e:
            rejected += 1
            errors.append({'event_id': getattr(event, 'event_id', 'unknown'), 'error': str(e)})
            logger.error(f'Ingestion error: {e}')

    db.commit()
    return IngestResponse(accepted=accepted, rejected=rejected,
                          duplicate=duplicate, errors=errors)
