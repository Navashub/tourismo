"""
Day 2 Part 2 - Select enrichment targets
=========================================
1982 records is too many to hand-enrich. This picks a realistic subset
(default 100) worth your manual time, biased toward:
  1. Priority locations (match your example queries)
  2. Records that already have SOME signal (website_url, amenities, phone)
     -> these are more likely to be real, notable hotels worth featuring,
        not a random unnamed guesthouse OSM happened to tag.

Output: data/enrichment_targets.csv - a MUCH shorter worklist to fill by hand.
Everything not selected stays in cleaned_hotels.json as-is (placeholder
description, "unknown" price) - still usable for broad coverage / /hotels
listing endpoints, just not as rich in the RAG answers.
"""

import json
import csv

CLEAN_PATH = "data/cleaned_hotels.json"
TARGETS_CSV = "data/enrichment_targets.csv"

PRIORITY_LOCATIONS = ["Nairobi", "Mombasa", "Diani", "Maasai Mara", "Zanzibar"]

# How many hotels to enrich per location. Priority locations get more.
TARGET_PER_PRIORITY_LOCATION = 15   # 5 locations x 15 = 75
TARGET_PER_OTHER_LOCATION = 3       # spreads coverage across remaining locations


def signal_score(record):
    """Rough proxy for 'is this a real, notable hotel worth featuring'."""
    score = 0
    if record.get("website_url"):
        score += 3
    if record.get("contact", {}).get("phone"):
        score += 2
    if record.get("amenities"):
        score += len(record["amenities"])
    if record.get("stars"):
        score += 2
    return score


def main():
    with open(CLEAN_PATH, encoding="utf-8") as f:
        records = json.load(f)

    by_location = {}
    for r in records:
        by_location.setdefault(r["location"], []).append(r)

    selected = []
    for location, hotels in by_location.items():
        hotels_sorted = sorted(hotels, key=signal_score, reverse=True)
        n = TARGET_PER_PRIORITY_LOCATION if location in PRIORITY_LOCATIONS else TARGET_PER_OTHER_LOCATION
        selected.extend(hotels_sorted[:n])

    print(f"Selected {len(selected)} hotels to enrich out of {len(records)} total.")

    with open(TARGETS_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "hotel_id", "name", "location", "website_url", "phone",
            "current_amenities",
            "description (write 2-3 sentences)",
            "price_range (budget/mid-range/luxury)",
            "price_min_usd", "price_max_usd",
            "rating (0-5, only if you can verify one)",
            "review_summary (1-2 sentences)",
            "nearby_attractions (comma-separated)",
        ])
        for r in selected:
            writer.writerow([
                r["hotel_id"], r["name"], r["location"],
                r.get("website_url") or "",
                r.get("contact", {}).get("phone") or "",
                ", ".join(r.get("amenities", [])),
                "", "", "", "", "", "", "",
            ])

    print(f"Wrote worklist to {TARGETS_CSV}")
    print("Breakdown:")
    from collections import Counter
    counts = Counter(r["location"] for r in selected)
    for loc, count in sorted(counts.items(), key=lambda x: -x[1]):
        print(f"  {loc}: {count}")


if __name__ == "__main__":
    main()