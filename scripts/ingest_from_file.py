"""
Helper script: reads a .jsonl events file and POSTs them to the API in batches.
Use this after running the detection pipeline.
"""

import json
import requests
import argparse
import time

API_URL = "http://localhost:8000"
BATCH_SIZE = 100


def ingest_file(jsonl_path: str):
    events = []
    with open(jsonl_path) as f:
        for line in f:
            line = line.strip()
            if line:
                events.append(json.loads(line))

    print(f"Loaded {len(events)} events from {jsonl_path}")

    total_accepted  = 0
    total_duplicate = 0
    total_rejected  = 0

    for i in range(0, len(events), BATCH_SIZE):
        batch = events[i:i+BATCH_SIZE]
        r = requests.post(f"{API_URL}/events/ingest", json={"events": batch}, timeout=30)

        if r.status_code == 200:
            d = r.json()
            total_accepted  += d["accepted"]
            total_duplicate += d["duplicate"]
            total_rejected  += d["rejected"]
            print(f"Batch {i//BATCH_SIZE+1}: accepted={d['accepted']} "
                  f"dup={d['duplicate']} rejected={d['rejected']}")
        else:
            print(f"Batch {i//BATCH_SIZE+1} FAILED: {r.status_code} {r.text[:200]}")

        time.sleep(0.1)  # gentle throttle

    print(f"\nDone. Total: accepted={total_accepted} duplicate={total_duplicate} rejected={total_rejected}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", required=True, help="Path to .jsonl events file")
    args = parser.parse_args()
    ingest_file(args.file)