#!/bin/bash
# Run detection pipeline on all clips
set -e

STORE_ID=${1:-STORE_BLR_002}
DATA_DIR=${2:-./data}

python pipeline/detect.py \
  --video "$DATA_DIR/clips/entry.mp4" \
  --store-id "$STORE_ID" \
  --camera-id "CAM_ENTRY_01" \
  --start-time "2026-03-03T14:00:00Z" \
  --layout "$DATA_DIR/store_layout.json" \
  --output "$DATA_DIR/events_output.jsonl"
  