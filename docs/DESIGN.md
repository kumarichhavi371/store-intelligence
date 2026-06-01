# DESIGN.md — Store Intelligence System Architecture

## Overview

The system is a four-stage pipeline that converts raw CCTV footage into live retail analytics.

**Stage 1 — Detection Layer** (`pipeline/`): Reads video frames using OpenCV, runs YOLOv8n for person detection, uses ByteTrack for cross-frame identity persistence, and emits structured JSON events to a `.jsonl` file.

**Stage 2 — Event Stream** (`data/events_output.jsonl`): A newline-delimited JSON file that acts as the handoff between the detection pipeline and the API. Each line is one event conforming to the required schema.

**Stage 3 — Intelligence API** (`app/`): A FastAPI application backed by SQLite. Ingests events via POST, computes real-time metrics, detects anomalies, and exposes five queryable endpoints.

**Stage 4 — Dashboard** (`dashboard/`): A single-page HTML/JS dashboard that polls the API every 5 seconds and renders KPIs, anomalies, and a conversion funnel live.

## Technology Choices

| Component | Choice | Reason |
|---|---|---|
| Detection | YOLOv8n | Fast, accurate, pre-trained on COCO (includes "person" class) |
| Tracking | ByteTrack (via supervision) | State-of-the-art MOT, handles occlusion well |
| API Framework | FastAPI | Async, automatic OpenAPI docs, fast to build |
| Database | SQLite | Zero-ops, sufficient for single-node deployment |
| Containerisation | Docker Compose | One-command startup |

## AI-Assisted Decisions

### 1. Event Schema Design
I asked Claude to review the required schema and suggest edge cases I might miss. It pointed out that `BILLING_QUEUE_ABANDON` requires POS correlation and suggested storing `billing_entries` as a dict keyed by `visitor_id` so I could detect when someone left the billing zone without a following transaction. I adopted this approach.

### 2. Staff Detection Heuristic
I asked an LLM to suggest methods for staff detection without a dedicated model. It suggested two heuristics: (a) persistent presence (staff are tracked across many more frames than customers) and (b) bounding box height ratio (staff tend to be closer to cameras). I implemented both and combined them with OR logic. In testing this works reasonably well, though a proper Re-ID model with a staff reference gallery would be more accurate.

### 3. Re-entry Detection
The LLM suggested using appearance embeddings from a Re-ID model for re-entry detection. Given time constraints, I implemented a simpler approach: same `visitor_id` (assigned by ByteTrack) returning within a 5-minute window. This works for short clips but would degrade over longer periods. I documented this limitation in CHOICES.md.