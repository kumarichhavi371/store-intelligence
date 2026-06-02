"""
Main detection + tracking script.
Reads CCTV clips → detects people → tracks them → emits structured events.
"""

import cv2
import json
import uuid
import os
import sys
import argparse
import numpy as np
from datetime import datetime, timezone, timedelta
from pathlib import Path
from collections import defaultdict

# YOLOv8 for detection
from ultralytics import YOLO
import supervision as sv

# Import our event emitter
sys.path.insert(0, str(Path(__file__).parent))
from emit import EventEmitter

# ─────────────────────────────────────────────
# CONFIGURATION
# ─────────────────────────────────────────────

ENTRY_ZONE_Y_RATIO   = 0.35   # top 35% of frame = entry zone
BILLING_ZONE_Y_RATIO = 0.65   # bottom 35% = billing zone
DWELL_EMIT_INTERVAL  = 30     # emit ZONE_DWELL every 30 seconds
REENTRY_WINDOW_SEC   = 300    # 5 min — if same person returns, it's re-entry
STAFF_MIN_FRAMES     = 1200    # staff appear in >150 frames continuously
CONFIDENCE_THRESHOLD = 0.35   # minimum detection confidence to keep

# Staff detection: bounding box height ratio (staff tend to fill more of frame)
STAFF_HEIGHT_RATIO   = 0.55

# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────

def load_store_layout(layout_path: str) -> dict:
    """Load store_layout.json. Returns dict keyed by store_id."""
    with open(layout_path) as f:
        return json.load(f)


def get_zone_for_box(box, frame_h, frame_w, zones: list) -> str | None:
    """
    Given a bounding box [x1,y1,x2,y2] and frame dimensions,
    return the zone name this detection falls in.
    Uses simple Y-position heuristic.
    """

    cy = (box[1] + box[3]) / 2
    cy_ratio = cy / frame_h

    if cy_ratio < ENTRY_ZONE_Y_RATIO:
        return "ENTRY_ZONE"
    elif cy_ratio > BILLING_ZONE_Y_RATIO:
        return "BILLING_ZONE"
    else:
        return "MAIN_FLOOR"

def is_staff_heuristic(track_history: dict, track_id: int, box, frame_h) -> bool:
    """
    Heuristic staff detection:
    1. Person has been tracked for many frames (always present = staff)
    2. Bounding box is very tall relative to frame (staff closer to camera)
    """
    frames_seen = track_history.get(track_id, {}).get("frames", 0)
    box_height = (box[3] - box[1]) / frame_h

    return frames_seen > STAFF_MIN_FRAMES or box_height > STAFF_HEIGHT_RATIO


def direction_of_movement(track_history: dict, track_id: int) -> str:
    """
    Returns 'ENTRY' or 'EXIT' based on Y movement direction.
    Moving down (increasing Y) = entering store.
    Moving up (decreasing Y) = exiting.
    """
    positions = track_history.get(track_id, {}).get("positions", [])
    if len(positions) < 5:
        return "ENTRY"  # default

    first_y = np.mean([p[1] for p in positions[:3]])
    last_y  = np.mean([p[1] for p in positions[-3:]])

    return "ENTRY" if last_y > first_y else "EXIT"


# ─────────────────────────────────────────────
# MAIN PROCESSOR
# ─────────────────────────────────────────────

class StoreVideoProcessor:
    def __init__(self, store_id: str, camera_id: str, clip_start_time: str,
                 layout: dict, output_path: str):
        self.store_id        = store_id
        self.camera_id       = camera_id
        self.clip_start_dt   = datetime.fromisoformat(clip_start_time.replace("Z","")).replace(tzinfo=timezone.utc)
        self.layout          = layout
        self.emitter         = EventEmitter(output_path)

        # Load YOLO model (downloads automatically first time ~6MB)
        print("Loading YOLOv8n model...")
        self.model = YOLO("yolov8n.pt")

        # ByteTrack tracker
        self.tracker = sv.ByteTrack()

        # State tracking
        self.track_history    = defaultdict(lambda: {"frames": 0, "positions": [], "zone": None,
                                                      "zone_enter_time": None, "dwell_last_emit": None,
                                                      "visitor_id": None, "is_staff": False,
                                                      "entered": False, "exited": False})
        self.visitor_sessions = {}   # track_id → visitor_id
        self.exited_visitors  = {}   # visitor_id → exit_timestamp (for re-entry detection)
        self.zone_visitors    = defaultdict(set)   # zone → set of visitor_ids currently inside
        self.billing_entries  = {}   # visitor_id → timestamp entered billing zone

        # For queue depth
        self.current_queue_depth = 0

        print(f"Processor ready for {store_id} / {camera_id}")

    def frame_to_timestamp(self, frame_idx: int, fps: float) -> str:
        """Convert frame index to ISO-8601 UTC timestamp."""
        offset_sec = frame_idx / fps
        ts = self.clip_start_dt + timedelta(seconds=offset_sec)
        return ts.strftime("%Y-%m-%dT%H:%M:%SZ")

    def get_or_create_visitor_id(self, track_id: int) -> str:
        if track_id not in self.visitor_sessions:
            short = uuid.uuid4().hex[:6]
            self.visitor_sessions[track_id] = f"VIS_{short}"
        return self.visitor_sessions[track_id]

    def process_clip(self, video_path: str):
        """Main loop — read frames, detect, track, emit events."""
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            print(f"ERROR: Cannot open video {video_path}")
            return

        fps       = cap.get(cv2.CAP_PROP_FPS) or 15.0
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        frame_h   = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        frame_w   = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))

        print(f"Video: {total_frames} frames @ {fps:.1f}fps  ({frame_w}x{frame_h})")

        frame_idx = 0
        # Process every 3rd frame for speed (still 5fps from 15fps source)
        SKIP = 3

        while True:
            ret, frame = cap.read()
            if not ret:
                break

            frame_idx += 1
            if frame_idx % SKIP != 0:
                continue

            timestamp = self.frame_to_timestamp(frame_idx, fps)

            # ── Run YOLO detection ──
            results = self.model(frame, classes=[0], verbose=False,
                                 conf=CONFIDENCE_THRESHOLD)[0]  # class 0 = person

            # Convert to supervision format for ByteTrack
            detections = sv.Detections.from_ultralytics(results)

            if len(detections) == 0:
                frame_idx += 1
                continue

            # ── Run ByteTrack ──
            tracked = self.tracker.update_with_detections(detections)

            # Update queue depth (people in billing zone)
            billing_count = 0

            for i, track_id in enumerate(tracked.tracker_id):
                if track_id is None:
                    continue

                box        = tracked.xyxy[i]
                confidence = float(tracked.confidence[i]) if tracked.confidence is not None else 0.9

                # Update track history
                hist = self.track_history[track_id]
                hist["frames"] += 1
                cx = float((box[0] + box[2]) / 2)
                cy = float((box[1] + box[3]) / 2)
                hist["positions"].append((cx, cy))
                if len(hist["positions"]) > 30:
                    hist["positions"] = hist["positions"][-30:]

                # Determine if staff
                is_staff = is_staff_heuristic(self.track_history, track_id, box, frame_h)
                hist["is_staff"] = is_staff

                # Get zone
                zone = get_zone_for_box(box, frame_h, frame_w, [])

                visitor_id = self.get_or_create_visitor_id(track_id)
                session_seq = hist["frames"] // SKIP

                # ── ENTRY event ──
                if not hist["entered"] and zone == "ENTRY_ZONE":
                    hist["entered"] = True
                    event_type = "ENTRY"

                    # Check for RE-ENTRY
                    if visitor_id in self.exited_visitors:
                        prev_exit = self.exited_visitors[visitor_id]
                        elapsed   = (datetime.fromisoformat(timestamp.replace("Z","")) -
                                     datetime.fromisoformat(prev_exit.replace("Z",""))).total_seconds()
                        if elapsed < REENTRY_WINDOW_SEC:
                            event_type = "REENTRY"

                    self.emitter.emit({
                        "store_id":    self.store_id,
                        "camera_id":   self.camera_id,
                        "visitor_id":  visitor_id,
                        "event_type":  event_type,
                        "timestamp":   timestamp,
                        "zone_id":     None,
                        "dwell_ms":    0,
                        "is_staff":    is_staff,
                        "confidence":  confidence,
                        "metadata":    {"queue_depth": None, "sku_zone": None,
                                        "session_seq": session_seq}
                    })

                # ── ZONE transitions ──
                if zone != hist["zone"]:
                    # Zone exit
                    if hist["zone"] is not None:
                        dwell_ms = 0
                        if hist["zone_enter_time"]:
                            enter_dt = datetime.fromisoformat(hist["zone_enter_time"].replace("Z",""))
                            cur_dt   = datetime.fromisoformat(timestamp.replace("Z",""))
                            dwell_ms = int((cur_dt - enter_dt).total_seconds() * 1000)

                        self.emitter.emit({
                            "store_id":   self.store_id,
                            "camera_id":  self.camera_id,
                            "visitor_id": visitor_id,
                            "event_type": "ZONE_EXIT",
                            "timestamp":  timestamp,
                            "zone_id":    hist["zone"],
                            "dwell_ms":   dwell_ms,
                            "is_staff":   is_staff,
                            "confidence": confidence,
                            "metadata":   {"queue_depth": None, "sku_zone": hist["zone"],
                                           "session_seq": session_seq}
                        })

                    # Zone enter
                    hist["zone"]            = zone
                    hist["zone_enter_time"] = timestamp
                    hist["dwell_last_emit"] = timestamp

                    self.emitter.emit({
                        "store_id":   self.store_id,
                        "camera_id":  self.camera_id,
                        "visitor_id": visitor_id,
                        "event_type": "ZONE_ENTER",
                        "timestamp":  timestamp,
                        "zone_id":    zone,
                        "dwell_ms":   0,
                        "is_staff":   is_staff,
                        "confidence": confidence,
                        "metadata":   {"queue_depth": None, "sku_zone": zone,
                                       "session_seq": session_seq}
                    })

                    # Billing zone specific
                    if zone == "BILLING_ZONE":
                        billing_count += 1
                        self.billing_entries[visitor_id] = timestamp
                        if self.current_queue_depth > 0 and not is_staff:
                            self.emitter.emit({
                                "store_id":   self.store_id,
                                "camera_id":  self.camera_id,
                                "visitor_id": visitor_id,
                                "event_type": "BILLING_QUEUE_JOIN",
                                "timestamp":  timestamp,
                                "zone_id":    "BILLING_ZONE",
                                "dwell_ms":   0,
                                "is_staff":   is_staff,
                                "confidence": confidence,
                                "metadata":   {"queue_depth": self.current_queue_depth,
                                               "sku_zone": "BILLING", "session_seq": session_seq}
                            })

                # ── ZONE_DWELL (every 30s) ──
                if hist["zone"] and hist["dwell_last_emit"]:
                    last_dt = datetime.fromisoformat(hist["dwell_last_emit"].replace("Z",""))
                    cur_dt  = datetime.fromisoformat(timestamp.replace("Z",""))
                    if (cur_dt - last_dt).total_seconds() >= DWELL_EMIT_INTERVAL:
                        enter_dt = datetime.fromisoformat((hist["zone_enter_time"] or timestamp).replace("Z",""))
                        dwell_ms = int((cur_dt - enter_dt).total_seconds() * 1000)
                        self.emitter.emit({
                            "store_id":   self.store_id,
                            "camera_id":  self.camera_id,
                            "visitor_id": visitor_id,
                            "event_type": "ZONE_DWELL",
                            "timestamp":  timestamp,
                            "zone_id":    hist["zone"],
                            "dwell_ms":   dwell_ms,
                            "is_staff":   is_staff,
                            "confidence": confidence,
                            "metadata":   {"queue_depth": None, "sku_zone": hist["zone"],
                                           "session_seq": session_seq}
                        })
                        hist["dwell_last_emit"] = timestamp

            self.current_queue_depth = billing_count

            if frame_idx % 300 == 0:
                pct = (frame_idx / total_frames) * 100
                print(f"  Progress: {pct:.0f}%  frame={frame_idx}  active_tracks={len(tracked)}")

        cap.release()

        # ── Emit EXIT for all still-inside visitors ──
        for track_id, hist in self.track_history.items():
            if hist["entered"] and not hist["exited"]:
                visitor_id = self.get_or_create_visitor_id(track_id)
                last_ts    = self.frame_to_timestamp(frame_idx, fps)
                self.exited_visitors[visitor_id] = last_ts
                self.emitter.emit({
                    "store_id":   self.store_id,
                    "camera_id":  self.camera_id,
                    "visitor_id": visitor_id,
                    "event_type": "EXIT",
                    "timestamp":  last_ts,
                    "zone_id":    None,
                    "dwell_ms":   0,
                    "is_staff":   hist["is_staff"],
                    "confidence": 0.7,
                    "metadata":   {"queue_depth": None, "sku_zone": None, "session_seq": 0}
                })

        self.emitter.flush()
        print(f"Done. Events written to output.")


# ─────────────────────────────────────────────
# CLI ENTRY POINT
# ─────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Store CCTV Detection Pipeline")
    parser.add_argument("--video",      required=True,  help="Path to video clip")
    parser.add_argument("--store-id",   required=True,  help="Store ID e.g. STORE_BLR_002")
    parser.add_argument("--camera-id",  required=True,  help="Camera ID e.g. CAM_ENTRY_01")
    parser.add_argument("--start-time", required=True,  help="Clip start time ISO-8601 UTC")
    parser.add_argument("--layout",     default="data/store_layout.json")
    parser.add_argument("--output",     default="data/events_output.jsonl")
    args = parser.parse_args()

    layout = {}
    if os.path.exists(args.layout):
        layout = load_store_layout(args.layout)

    processor = StoreVideoProcessor(
        store_id=args.store_id,
        camera_id=args.camera_id,
        clip_start_time=args.start_time,
        layout=layout,
        output_path=args.output
    )
    processor.process_clip(args.video)


if __name__ == "__main__":
    main()