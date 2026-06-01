# CHOICES.md — Key Design Decisions

## Decision 1: Detection Model — YOLOv8n

**Options considered:**
- YOLOv8n (nano) — fast, ~6MB, 37.3 mAP on COCO
- YOLOv8m (medium) — more accurate, ~25MB, slower
- RT-DETR — transformer-based, higher accuracy, GPU required
- MediaPipe — very fast, lower accuracy for crowds

**What AI suggested:** Claude suggested YOLOv8m as a better balance of accuracy vs speed for retail CCTV. It also suggested RT-DETR for better performance on crowded scenes.

**What I chose and why:** YOLOv8n. This challenge prioritises getting a working system over maximum accuracy. YOLOv8n runs at real-time speeds on CPU (the minimum viable deployment), handles the 1080p@15fps source well when processing every 3rd frame (effective 5fps), and the `supervision` library has excellent native integration. If I had GPU access, I would upgrade to YOLOv8m or RT-DETR for the billing queue scenes where occlusion is heaviest.

**Trade-off acknowledged:** Lower recall on partially occluded people (the billing queue edge case). Mitigated by not suppressing low-confidence detections — they're emitted with their actual confidence score.

---

## Decision 2: Event Schema Design

**Options considered:**
- Minimal schema (just entry/exit + timestamp)
- Full schema as specified (8 event types + metadata)
- Extended schema with raw bounding box coordinates

**What AI suggested:** The LLM recommended including raw bounding box coordinates in metadata for future analytics (heatmap overlaid on actual store image). It also suggested a `session_id` field separate from `visitor_id` to handle re-entries more cleanly.

**What I chose and why:** I followed the required schema exactly and added `session_seq` to metadata as a lightweight session tracker. I did not add bounding boxes because they would triple the event size and the downstream API doesn't need them. The `visitor_id` doubles as session identifier — re-entries generate a `REENTRY` event type rather than needing a separate field.

---

## Decision 3: API Architecture — SQLite + FastAPI (no message queue)

**Options considered:**
- FastAPI + SQLite (simple, zero-ops)
- FastAPI + PostgreSQL + Redis (production-grade, complex)
- FastAPI + Kafka + TimescaleDB (streaming-native, very complex)

**What AI suggested:** The LLM recommended PostgreSQL for production readiness and noted that SQLite has write-lock contention under concurrent ingest. It specifically flagged that 40 stores × 3 cameras × 15fps would overwhelm SQLite in production.

**What I chose and why:** SQLite for the challenge scope. The acceptance gate requires `docker compose up` with no manual steps — PostgreSQL requires a separate service with proper initialisation. SQLite satisfies all test assertions and runs reliably in a single container. I documented the PostgreSQL upgrade path: swap `DATABASE_URL` env var, remove `check_same_thread`, and the rest of the code is identical because SQLAlchemy abstracts the engine.