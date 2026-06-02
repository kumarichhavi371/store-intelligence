"""
Event schema + emission.
Handles generating event_ids and writing events to .jsonl files.
"""

import uuid
import json
import numpy as np
from datetime import datetime, timezone
from pathlib import Path


class EventEmitter:
    def __init__(self, output_path: str):
        self.output_path = output_path
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)

        # Open in append mode so multiple cameras can write to same file
        self.file = open(output_path, "a", encoding="utf-8")
        self.count = 0

    def _json_default(self, obj):
        if isinstance(obj, np.bool_):
            return bool(obj)

        if isinstance(obj, np.integer):
            return int(obj)

        if isinstance(obj, np.floating):
            return float(obj)

        if hasattr(obj, "item"):
            return obj.item()

        return str(obj)

    def emit(self, partial_event: dict) -> dict:
        """
        Takes a partial event dict (no event_id),
        adds event_id, validates required fields, writes to file.
        """
        event = {
            "event_id": str(uuid.uuid4()),
            "store_id": partial_event.get("store_id", "UNKNOWN"),
            "camera_id": partial_event.get("camera_id", "UNKNOWN"),
            "visitor_id": partial_event.get(
                "visitor_id",
                f"VIS_{uuid.uuid4().hex[:6]}"
            ),
            "event_type": partial_event.get("event_type", "ZONE_ENTER"),
            "timestamp": partial_event.get(
                "timestamp",
                datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            ),
            "zone_id": partial_event.get("zone_id"),
            "dwell_ms": int(partial_event.get("dwell_ms", 0)),
            "is_staff": bool(partial_event.get("is_staff", False)),
            "confidence": float(
                round(partial_event.get("confidence", 0.9), 4)
            ),
            "metadata": {
                "queue_depth": partial_event.get("metadata", {}).get("queue_depth"),
                "sku_zone": partial_event.get("metadata", {}).get("sku_zone"),
                "session_seq": int(
                    partial_event.get("metadata", {}).get("session_seq", 0)
                ),
            }
        }

        self.file.write(
            json.dumps(
                event,
                default=self._json_default
            ) + "\n"
        )

        self.count += 1
        return event

    def flush(self):
        self.file.flush()
        self.file.close()
        print(f"Emitter: wrote {self.count} events to {self.output_path}")