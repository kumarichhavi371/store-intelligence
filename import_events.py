import json
from app.database import SessionLocal, EventRecord

files = [
    "data/cam1_events.jsonl",
    "data/cam2_events.jsonl",
    "data/cam4_events.jsonl",
    "data/cam5_events.jsonl",
    "data/events_output.jsonl"
]

db = SessionLocal()
count = 0

for file in files:
    with open(file, "r", encoding="utf-8") as f:
        for line in f:
            event = json.loads(line)

            exists = db.query(EventRecord).filter(
                EventRecord.event_id == event["event_id"]
            ).first()

            if exists:
                continue

            db.add(
                EventRecord(
                    event_id=event["event_id"],
                    store_id=event["store_id"],
                    camera_id=event["camera_id"],
                    visitor_id=event["visitor_id"],
                    event_type=event["event_type"],
                    timestamp=event["timestamp"],
                    zone_id=event.get("zone_id"),
                    dwell_ms=event.get("dwell_ms", 0),
                    is_staff=event.get("is_staff", False),
                    confidence=event.get("confidence", 0.0),
                    queue_depth=event.get("metadata", {}).get("queue_depth"),
                    sku_zone=event.get("metadata", {}).get("sku_zone"),
                    session_seq=event.get("metadata", {}).get("session_seq", 0),
                )
            )
            count += 1

db.commit()
db.close()

print(f"Imported {count} events")