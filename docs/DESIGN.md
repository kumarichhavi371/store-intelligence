# DESIGN.md — Store Intelligence System Architecture

## Overview

Store Intelligence converts CCTV-derived visitor events into real-time retail analytics.

The system follows a four-stage architecture:

### Stage 1 — Detection Layer

Location: `pipeline/`

Responsibilities:

* Read CCTV video streams
* Detect people using YOLOv8
* Track identities across frames
* Generate structured retail events
* Export events as JSONL

Output:

```text
events_output.jsonl
```

---

### Stage 2 — Event Stream

Location: `data/`

The detection pipeline produces newline-delimited JSON events.

Characteristics:

* One event per line
* Schema-compliant structure
* Replayable and auditable
* Decouples detection from analytics

---

### Stage 3 — Intelligence API

Location: `app/`

Built using FastAPI and SQLite.

Responsibilities:

* Event ingestion
* KPI computation
* Funnel analytics
* Heatmap analytics
* Anomaly detection
* Health monitoring

Exposed Endpoints:

```text
POST /events/ingest
GET  /stores/{store_id}/metrics
GET  /stores/{store_id}/funnel
GET  /stores/{store_id}/heatmap
GET  /stores/{store_id}/anomalies
GET  /health
```

---

### Stage 4 — Dashboard

Location: `dashboard/`

Responsibilities:

* Poll APIs periodically
* Display KPIs
* Visualize funnel performance
* Display anomaly alerts
* Present live operational insights

---

## Architecture Flow

```text
CCTV Video
     │
     ▼
YOLOv8 Detection
     │
     ▼
ByteTrack Tracking
     │
     ▼
JSON Event Stream
     │
     ▼
FastAPI Ingestion
     │
     ▼
SQLite Storage
     │
     ▼
Analytics Engine
     │
     ▼
Dashboard + APIs
```

---

## Technology Choices

| Component        | Technology        | Reason                                      |
| ---------------- | ----------------- | ------------------------------------------- |
| Detection        | YOLOv8n           | Fast person detection                       |
| Tracking         | ByteTrack         | Stable multi-object tracking                |
| API              | FastAPI           | High performance and automatic OpenAPI docs |
| Database         | SQLite            | Lightweight and zero-configuration          |
| Containerization | Docker Compose    | One-command deployment                      |
| Dashboard        | HTML + JavaScript | Lightweight and simple deployment           |

---

## Scalability Considerations

The current implementation targets a single-node deployment.

Future improvements:

* PostgreSQL instead of SQLite
* Kafka event streaming
* Redis caching layer
* Multi-store aggregation service
* Dedicated analytics workers

---

## Assumptions

* Event timestamps are UTC.
* Event IDs are unique.
* Staff events are excluded from customer analytics.
* Billing activity is inferred from billing-zone behaviour.
