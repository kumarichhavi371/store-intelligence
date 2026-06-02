# Store Intelligence API

Real-time retail analytics platform built on CCTV event streams. The system ingests visitor movement events, computes store KPIs, detects anomalies, and exposes insights through REST APIs and a live dashboard.

## Features

* Event ingestion API with idempotency support
* Real-time store metrics
* Conversion funnel analytics
* Zone heatmap analytics
* Operational anomaly detection
* Health monitoring endpoint
* Interactive Swagger documentation
* Dockerized deployment
* Live dashboard

---

## Tech Stack

* FastAPI
* SQLAlchemy
* SQLite
* Docker & Docker Compose
* Python 3.11

---

## Project Structure

```text
app/
├── main.py
├── ingestion.py
├── metrics.py
├── funnel.py
├── heatmap.py
├── anomalies.py
├── health.py
├── database.py
└── models.py

dashboard/
docs/
data/
tests/
```

## Running Locally

### API

```bash
uvicorn app.main:app --reload
```

API available at:

```text
http://localhost:8000
```

Swagger UI:

```text
http://localhost:8000/docs
```

### Docker

```bash
docker compose up --build
```

Services:

```text
Dashboard : http://localhost:3000
API       : http://localhost:8000
Swagger   : http://localhost:8000/docs
```

---

## Available APIs

### Event Ingestion

```http
POST /events/ingest
```

Accepts up to 500 events per batch.

### Store Metrics

```http
GET /stores/{store_id}/metrics
```

Returns:

* Unique visitors
* Conversion rate
* Average dwell time
* Queue depth
* Abandonment rate

### Funnel Analytics

```http
GET /stores/{store_id}/funnel
```

Stages:

```text
Entry → Zone Visit → Billing → Purchase
```

### Heatmap Analytics

```http
GET /stores/{store_id}/heatmap
```

Returns zone visit frequency and dwell statistics.

### Anomaly Detection

```http
GET /stores/{store_id}/anomalies
```

Detects:

* Dead zones
* Queue issues
* Conversion drops

### Health Check

```http
GET /health
```

Returns service and store status.

---

## Sample Store

```text
STORE_BLR_002
```

---

## Assumptions

* Events are timestamped in UTC.
* Event IDs are globally unique.
* Billing activity is inferred from billing-zone events.
* Staff activity is excluded from customer analytics.

---

## Documentation

* docs/DESIGN.md
* docs/CHOICES.md

---

## Author

Purplle Tech Challenge 2026 Submission
