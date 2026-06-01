# Store Intelligence API

Real-time retail analytics from CCTV footage. Detects people, tracks movement, emits events, computes KPIs.

## Quick Start (5 commands)

```bash
git clone <your-repo-url>
cd store-intelligence
cp data/sample_events.jsonl data/events_output.jsonl   # seed with sample data
docker compose up --build
```

API is now live at **http://localhost:8000**
Dashboard is live at **http://localhost:3000**

## Run the Detection Pipeline

1. Place your video clips in `data/clips/`
2. Run:

```bash
# Activate virtualenv (Windows)
venv\Scripts\activate

# Run detection on one clip
python pipeline/detect.py \
  --video data/clips/entry.mp4 \
  --store-id STORE_BLR_002 \
  --camera-id CAM_ENTRY_01 \
  --start-time 2026-03-03T14:00:00Z \
  --output data/events_output.jsonl
```

3. Ingest the events into the API:

```bash
python scripts/ingest_from_file.py --file data/events_output.jsonl
```

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| POST | `/events/ingest` | Ingest up to 500 events |
| GET | `/stores/{id}/metrics` | Visitors, conversion, dwell, queue |
| GET | `/stores/{id}/funnel` | Entry → Zone → Billing → Purchase |
| GET | `/stores/{id}/heatmap` | Zone frequency heatmap |
| GET | `/stores/{id}/anomalies` | Queue spikes, conversion drops |
| GET | `/health` | Service + feed status |

Interactive API docs: **http://localhost:8000/docs**

## Run Tests

```bash
venv\Scripts\activate
pytest tests/ -v --cov=app --cov-report=term-missing
```

## Architecture

See `docs/DESIGN.md` for full architecture overview.
See `docs/CHOICES.md` for key design decisions.