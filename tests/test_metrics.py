# PROMPT: "Write pytest tests for FastAPI store analytics API using SQLite test DB.
# Cover: ingest happy path, idempotency, batch too large, zero traffic store,
# staff exclusion, re-entry deduplication, health, anomalies."
# CHANGES MADE: Used file-based test.db instead of in-memory so all connections
# share the same schema. Drop and recreate tables before tests run.

import pytest
import uuid
from datetime import datetime, timezone
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.database import Base, get_db

TEST_DB_URL = "sqlite:///./test_temp.db"
engine_test = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
TestSession = sessionmaker(bind=engine_test)
Base.metadata.drop_all(bind=engine_test)
Base.metadata.create_all(bind=engine_test)

def override_get_db():
    db = TestSession()
    try:
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)

def make_event(store_id="STORE_BLR_002", event_type="ENTRY",
               is_staff=False, zone_id=None, dwell_ms=0, visitor_id=None):
    return {
        "event_id":   str(uuid.uuid4()),
        "store_id":   store_id,
        "camera_id":  "CAM_ENTRY_01",
        "visitor_id": visitor_id or f"VIS_{uuid.uuid4().hex[:6]}",
        "event_type": event_type,
        "timestamp":  datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "zone_id":    zone_id,
        "dwell_ms":   dwell_ms,
        "is_staff":   is_staff,
        "confidence": 0.9,
        "metadata":   {"queue_depth": None, "sku_zone": zone_id, "session_seq": 1}
    }

def test_ingest_happy_path():
    events = [make_event() for _ in range(3)]
    r = client.post("/events/ingest", json={"events": events})
    assert r.status_code == 200
    assert r.json()["accepted"] == 3
    assert r.json()["rejected"] == 0

def test_ingest_idempotent():
    events = [make_event()]
    r1 = client.post("/events/ingest", json={"events": events})
    r2 = client.post("/events/ingest", json={"events": events})
    assert r1.json()["accepted"] == 1
    assert r2.json()["duplicate"] == 1

def test_ingest_batch_too_large():
    events = [make_event() for _ in range(501)]
    r = client.post("/events/ingest", json={"events": events})
    assert r.status_code == 400

def test_metrics_zero_traffic():
    r = client.get("/stores/STORE_EMPTY_999/metrics")
    assert r.status_code == 200
    assert r.json()["unique_visitors"] == 0
    assert r.json()["conversion_rate"] == 0.0

def test_metrics_staff_excluded():
    staff_event = make_event(store_id="STORE_TEST_001", event_type="ENTRY", is_staff=True)
    client.post("/events/ingest", json={"events": [staff_event]})
    r = client.get("/stores/STORE_TEST_001/metrics")
    assert r.status_code == 200
    assert r.json()["unique_visitors"] == 0

def test_funnel_no_double_count_reentry():
    vid = f"VIS_{uuid.uuid4().hex[:6]}"
    entry   = make_event(store_id="STORE_FUNNEL_01", event_type="ENTRY",   visitor_id=vid)
    reentry = make_event(store_id="STORE_FUNNEL_01", event_type="REENTRY", visitor_id=vid)
    client.post("/events/ingest", json={"events": [entry, reentry]})
    r = client.get("/stores/STORE_FUNNEL_01/funnel")
    assert r.status_code == 200
    stages = {s["stage"]: s["count"] for s in r.json()["stages"]}
    assert stages["Entry"] == 1

def test_health_endpoint():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["service_status"] == "OK"

def test_anomalies_endpoint():
    r = client.get("/stores/STORE_BLR_002/anomalies")
    assert r.status_code == 200
    assert "anomalies" in r.json()
