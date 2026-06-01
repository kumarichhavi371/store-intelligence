# Creates missing app/ingestion.py and app/__init__.py

ingestion = (
    "from sqlalchemy.orm import Session\n"
    "from app.models import IngestRequest, IngestResponse\n"
    "from app.database import EventRecord\n"
    "import logging\n"
    "\n"
    "logger = logging.getLogger(__name__)\n"
    "\n"
    "\n"
    "def ingest_events(request: IngestRequest, db: Session) -> IngestResponse:\n"
    "    accepted  = 0\n"
    "    rejected  = 0\n"
    "    duplicate = 0\n"
    "    errors    = []\n"
    "\n"
    "    for event in request.events:\n"
    "        try:\n"
    "            existing = db.query(EventRecord).filter(\n"
    "                EventRecord.event_id == event.event_id\n"
    "            ).first()\n"
    "            if existing:\n"
    "                duplicate += 1\n"
    "                continue\n"
    "            record = EventRecord(\n"
    "                event_id    = event.event_id,\n"
    "                store_id    = event.store_id,\n"
    "                camera_id   = event.camera_id,\n"
    "                visitor_id  = event.visitor_id,\n"
    "                event_type  = event.event_type.value,\n"
    "                timestamp   = event.timestamp,\n"
    "                zone_id     = event.zone_id,\n"
    "                dwell_ms    = event.dwell_ms,\n"
    "                is_staff    = event.is_staff,\n"
    "                confidence  = event.confidence,\n"
    "                queue_depth = event.metadata.queue_depth,\n"
    "                sku_zone    = event.metadata.sku_zone,\n"
    "                session_seq = event.metadata.session_seq,\n"
    "            )\n"
    "            db.add(record)\n"
    "            accepted += 1\n"
    "        except Exception as e:\n"
    "            rejected += 1\n"
    "            errors.append({'event_id': getattr(event, 'event_id', 'unknown'), 'error': str(e)})\n"
    "            logger.error(f'Ingestion error: {e}')\n"
    "\n"
    "    db.commit()\n"
    "    return IngestResponse(accepted=accepted, rejected=rejected,\n"
    "                          duplicate=duplicate, errors=errors)\n"
)

with open("app/ingestion.py", "w", encoding="utf-8") as f:
    f.write(ingestion)
print("Created app/ingestion.py")

with open("app/__init__.py", "w", encoding="utf-8") as f:
    f.write("")
print("Created app/__init__.py")

# Also create other missing __init__ files
import os
for folder in ["pipeline", "tests", "scripts"]:
    os.makedirs(folder, exist_ok=True)
    init_path = f"{folder}/__init__.py"
    if not os.path.exists(init_path):
        with open(init_path, "w") as f:
            f.write("")
        print(f"Created {init_path}")

print("\nAll done! Now run: uvicorn app.main:app --reload --port 8000")