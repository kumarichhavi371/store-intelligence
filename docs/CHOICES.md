# CHOICES.md — Key Design Decisions

## Decision 1: Detection Model Selection

### Options Considered

* YOLOv8n
* YOLOv8m
* RT-DETR
* MediaPipe

### Selected

YOLOv8n

### Rationale

The challenge prioritizes a working end-to-end system with reasonable performance on commodity hardware.

YOLOv8n was selected because:

* Fast inference speed
* Small model size
* Good person-detection accuracy
* Easy integration with the pipeline
* Suitable for CPU execution

### Trade-off

Compared with larger models, YOLOv8n may miss partially occluded people in crowded scenes.

This was considered acceptable for the challenge scope.

---

## Decision 2: Event Schema Design

### Options Considered

1. Minimal schema
2. Required challenge schema
3. Extended schema with raw bounding-box coordinates

### Selected

Required challenge schema with lightweight metadata fields.

### Rationale

The provided schema already supports:

* Visitor tracking
* Zone analytics
* Funnel computation
* Queue monitoring
* Anomaly detection

Additional bounding-box data was intentionally excluded because:

* It significantly increases event size
* It is not required by downstream analytics
* It increases storage costs

### Trade-off

Future visual heatmap overlays would benefit from coordinate-level information.

---

## Decision 3: Database Architecture

### Options Considered

* SQLite
* PostgreSQL
* PostgreSQL + Redis
* Kafka-based streaming architecture

### Selected

SQLite

### Rationale

The challenge emphasizes:

* Simple setup
* Minimal dependencies
* Fast local execution
* Docker-based deployment

SQLite provides:

* Zero configuration
* Small footprint
* Reliable local persistence
* Fast development iteration

### Trade-off

SQLite is not ideal for very high write concurrency.

A production deployment could migrate to PostgreSQL without significant application changes because SQLAlchemy abstracts the database layer.

---

## Decision 4: API Framework

### Options Considered

* FastAPI
* Flask
* Django REST Framework

### Selected

FastAPI

### Rationale

FastAPI offers:

* Automatic OpenAPI generation
* Built-in request validation
* High performance
* Simple asynchronous support
* Interactive Swagger documentation

These features significantly reduce development effort while maintaining production-quality APIs.

---

## Decision 5: Containerization Strategy

### Selected

Docker Compose

### Rationale

Docker Compose enables:

* One-command startup
* Consistent environments
* Easy evaluation by reviewers
* Reproducible deployment

The entire platform can be launched using:

```bash
docker compose up --build
```

which aligns with the challenge evaluation requirements.

---

## Future Improvements

If extended beyond the challenge scope:

* PostgreSQL for scalable persistence
* Redis caching
* Kafka event streaming
* Dedicated analytics workers
* Re-identification models for long-term visitor tracking
* Multi-store aggregation and reporting
