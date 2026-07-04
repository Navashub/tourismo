"""
Retry script for attractions - same pattern as retry_missing.py, but for
scrape_attractions_osm.py. Only queries the locations that failed, merges
into the existing data/raw_attractions_osm.json instead of overwriting.
"""

import json
import os
import time
from scrape_osm_hotels import LOCATIONS
from scrape_attractions_osm import fetch_location, normalize_record

OUT_PATH = "data/raw_attractions_osm.json"

# Maasai Mara and Amboseli are HIGH priority - core safari use case.
# The rest are lower priority but worth one retry attempt.
MISSING_LOCATIONS = ["Maasai Mara", "Amboseli", "Nakuru", "Watamu", "Kisumu", "Dar es Salaam"]


def main():
    if os.path.exists(OUT_PATH):
        with open(OUT_PATH, encoding="utf-8") as f:
            all_records = json.load(f)
    else:
        all_records = []

    seen = {(r["name"].strip().lower(), r["location"]) for r in all_records}
    print(f"Loaded {len(all_records)} existing attraction records.")

    for location_name in MISSING_LOCATIONS:
        if location_name not in LOCATIONS:
            continue
        meta = LOCATIONS[location_name]
        try:
            elements = fetch_location(location_name, meta)
        except Exception as e:
            print(f"    !! Still failing for {location_name}: {e}")
            print(f"    -> Skipping. Will need manual entry for key safari sites here.")
            continue

        idx = 1
        added = 0
        for el in elements:
            record = normalize_record(el, location_name, meta, idx)
            if record is None:
                continue
            key = (record["name"].strip().lower(), location_name)
            if key in seen:
                continue
            seen.add(key)
            all_records.append(record)
            added += 1
            idx += 1

        print(f"    -> Added {added} new records for {location_name}")

        with open(OUT_PATH, "w", encoding="utf-8") as f:
            json.dump(all_records, f, indent=2)

        time.sleep(10)  # extra gentle - these mirrors have been hit a lot today

    print(f"\nDone. {len(all_records)} total attraction records saved to {OUT_PATH}")
    from collections import Counter
    counts = Counter(r["location"] for r in all_records)
    for loc, count in counts.items():
        print(f"  {loc}: {count}")


if __name__ == "__main__":
    main()