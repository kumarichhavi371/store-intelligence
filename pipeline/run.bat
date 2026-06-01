@echo off
set STORE_ID=STORE_BLR_002
set DATA_DIR=.\data

python pipeline\detect.py ^
  --video "%DATA_DIR%\clips\entry.mp4" ^
  --store-id "%STORE_ID%" ^
  --camera-id "CAM_ENTRY_01" ^
  --start-time "2026-03-03T14:00:00Z" ^
  --layout "%DATA_DIR%\store_layout.json" ^
  --output "%DATA_DIR%\events_output.jsonl"

echo Done! Events written to %DATA_DIR%\events_output.jsonlni