"""
Retry script - fetches ONLY the locations missing from your existing dataset,
and merges results into data/raw_hotels_osm.json instead of overwriting it.

Run this after waiting a bit (ideally 30-60 min) since repeated heavy runs
today have likely gotten your IP rate-limited by the free Overpass mirrors.
"""

import json
import os
import time
from scrape_osm_hotels import (
    LOCATIONS, fetch_location, normalize_record
)

OUT_PATH = "data/raw_hotels_osm.json"

# Edit this list if you want to retry a different set of locations
MISSING_LOCATIONS = ["Nairobi", "Nakuru", "Watamu", "Kisumu", "Lamu", "Arusha", "Kampala"]


def main():
    # Load what we already have
    if os.path.exists(OUT_PATH):
        with open(OUT_PATH) as f:
            all_records = json.load(f)
    else:
        all_records = []

    seen_names = {(r["name"].strip().lower(), r["location"]) for r in all_records}
    print(f"Loaded {len(all_records)} existing records.")

    for location_name in MISSING_LOCATIONS:
        if location_name not in LOCATIONS:
            print(f"  Skipping unknown location: {location_name}")
            continue
        meta = LOCATIONS[location_name]

        try:
            elements = fetch_location(location_name, meta)
        except Exception as e:
            print(f"    !! Still failing for {location_name}: {e}")
            print(f"    -> Skipping. Consider manual data entry for this one.")
            continue

        idx = 1
        added = 0
        for el in elements:
            record = normalize_record(el, location_name, meta, idx)
            if record is None:
                continue
            dedupe_key = (record["name"].strip().lower(), location_name)
            if dedupe_key in seen_names:
                continue
            seen_names.add(dedupe_key)
            all_records.append(record)
            added += 1
            idx += 1

        print(f"    -> Added {added} new records for {location_name}")

        # Save after every location
        with open(OUT_PATH, "w") as f:
            json.dump(all_records, f, indent=2)

        time.sleep(8)  # longer pause than the main script - be extra gentle on retry

    print(f"\nDone. {len(all_records)} total unique records saved to {OUT_PATH}")
    from collections import Counter
    counts = Counter(r["location"] for r in all_records)
    for loc, count in counts.items():
        print(f"  {loc}: {count}")


if __name__ == "__main__":
    main()