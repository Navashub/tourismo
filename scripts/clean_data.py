"""
Day 2 - Data Cleaning
=====================
Takes data/raw_hotels_osm.json (messy, raw OSM output) and produces
data/cleaned_hotels.json (deduped, validated, normalized to our schema).

Addresses every point in the brief's "Data Cleaning Requirements":
  - Missing hotel names       -> already filtered at scrape time, re-checked here
  - Duplicate hotel records   -> fuzzy name+location dedup (catches near-duplicates
                                   the scraper's exact-match dedup missed)
  - Invalid or missing prices -> bucketed as "unknown", never guessed
  - Inconsistent location names -> whitespace/case normalization
  - Missing descriptions      -> auto-generated placeholder from known fields,
                                   flagged for manual enrichment
  - Empty amenities           -> normalized vocabulary, left as [] if truly empty
  - Incorrect ratings         -> validated to 0-5 float range, else discarded
  - Unstructured text         -> amenity/category text normalized to controlled tags

Also writes data/needs_enrichment.csv - a worklist of every record still
missing a description/price/rating, ordered by priority location, so Day 2
Part 2 (manual enrichment) has a clear checklist instead of guesswork.
"""

import json
import csv
import re
from difflib import SequenceMatcher

RAW_PATH = "data/raw_hotels_osm.json"
CLEAN_PATH = "data/cleaned_hotels.json"
ENRICHMENT_CSV = "data/needs_enrichment.csv"

# Locations that map directly to your example queries - enrich these first
PRIORITY_LOCATIONS = ["Nairobi", "Mombasa", "Diani", "Maasai Mara", "Zanzibar"]

# Canonical amenity vocabulary - maps messy/varied input to one clean tag
AMENITY_NORMALIZATION = {
    "wifi": "wifi", "wi-fi": "wifi", "internet": "wifi", "free wifi": "wifi",
    "pool": "pool", "swimming pool": "pool", "swimming_pool": "pool",
    "restaurant": "restaurant", "dining": "restaurant",
    "bar": "bar", "cocktail bar": "bar",
    "parking": "parking", "car park": "parking",
    "air conditioning": "air conditioning", "ac": "air conditioning",
    "spa": "spa", "gym": "gym", "fitness center": "gym",
    "airport shuttle": "airport shuttle", "shuttle": "airport shuttle",
    "beach access": "beach access",
}


def normalize_amenity_list(raw_list):
    """Collapse messy amenity strings into the canonical vocabulary, drop unknowns."""
    cleaned = []
    for item in raw_list or []:
        key = item.strip().lower()
        canonical = AMENITY_NORMALIZATION.get(key)
        if canonical and canonical not in cleaned:
            cleaned.append(canonical)
    return cleaned


def normalize_location(location):
    """Trim/standardize whitespace and casing so 'diani ', 'Diani', 'DIANI' all match."""
    if not location:
        return None
    return location.strip().title()


def validate_rating(rating):
    """Only accept ratings that are real numbers in a sane 0-5 range."""
    if rating is None:
        return None
    try:
        r = float(rating)
    except (ValueError, TypeError):
        return None
    if 0 <= r <= 5:
        return round(r, 1)
    return None  # out-of-range or garbage value -> discard rather than trust it


def validate_coordinates(lat, lon):
    """Basic sanity check - East Africa roughly falls in this lat/lon box."""
    if lat is None or lon is None:
        return False
    try:
        lat, lon = float(lat), float(lon)
    except (ValueError, TypeError):
        return False
    return -12 <= lat <= 5 and 28 <= lon <= 42


def name_similarity(a, b):
    """0-1 similarity score between two hotel names, for fuzzy dedup."""
    return SequenceMatcher(None, a.lower().strip(), b.lower().strip()).ratio()


def fuzzy_dedupe(records, threshold=0.88):
    """
    Catches near-duplicate hotels the scraper's exact-match dedup missed -
    e.g. 'Sarova Stanley Hotel' vs 'Sarova Stanley' returned as separate OSM
    entries (a node AND a way for the same physical building is common).
    Keeps the record with more filled-in fields when a duplicate is found.
    """
    kept = []
    for record in records:
        duplicate_of = None
        for i, existing in enumerate(kept):
            if existing["location"] != record["location"]:
                continue
            if name_similarity(existing["name"], record["name"]) >= threshold:
                duplicate_of = i
                break
        if duplicate_of is None:
            kept.append(record)
        else:
            # keep whichever record has more non-empty fields
            existing = kept[duplicate_of]
            existing_filled = sum(1 for v in existing.values() if v not in (None, "", [], {}))
            new_filled = sum(1 for v in record.values() if v not in (None, "", [], {}))
            if new_filled > existing_filled:
                kept[duplicate_of] = record
    return kept


def clean_record(record):
    """Apply all field-level cleaning rules to a single record."""
    record["name"] = record["name"].strip() if record.get("name") else None
    record["location"] = normalize_location(record.get("location"))
    record["amenities"] = normalize_amenity_list(record.get("amenities"))
    record["rating"] = validate_rating(record.get("rating"))

    price = record.get("price_range")
    if price not in ("budget", "mid-range", "luxury"):
        record["price_range"] = "unknown"

    if not record.get("description"):
        # Placeholder built from confirmed fields only - never fabricated details.
        # Flagged in needs_enrichment.csv for a human-written replacement.
        parts = [record["name"], "is a", record.get("category", "hotel").lower(),
                  "in", record["location"] + "."]
        if record["amenities"]:
            parts.append("Amenities include " + ", ".join(record["amenities"]) + ".")
        record["description"] = " ".join(parts)
        record["_description_is_placeholder"] = True
    else:
        record["_description_is_placeholder"] = False

    return record


def main():
    with open(RAW_PATH, encoding="utf-8") as f:
        raw_records = json.load(f)
    print(f"Loaded {len(raw_records)} raw records.")

    # 1. Drop unusable records: no name, or invalid coordinates
    valid = []
    dropped_no_name = 0
    dropped_bad_coords = 0
    for r in raw_records:
        if not r.get("name") or not r["name"].strip():
            dropped_no_name += 1
            continue
        if not validate_coordinates(r.get("latitude"), r.get("longitude")):
            dropped_bad_coords += 1
            continue
        valid.append(r)
    print(f"Dropped {dropped_no_name} no-name records, {dropped_bad_coords} bad-coordinate records.")

    # 2. Field-level cleaning
    cleaned = [clean_record(r) for r in valid]

    # 3. Fuzzy dedup (catches near-duplicates exact-match missed)
    before = len(cleaned)
    cleaned = fuzzy_dedupe(cleaned)
    print(f"Fuzzy dedup removed {before - len(cleaned)} near-duplicate records.")

    # 4. Save cleaned dataset
    with open(CLEAN_PATH, "w", encoding="utf-8") as f:
        json.dump(cleaned, f, indent=2)
    print(f"Saved {len(cleaned)} cleaned records to {CLEAN_PATH}")

    # 5. Build enrichment worklist, priority locations first
    def priority_key(r):
        return (0 if r["location"] in PRIORITY_LOCATIONS else 1, r["location"], r["name"])

    needs_enrichment = sorted(
        [r for r in cleaned if r["_description_is_placeholder"] or r["price_range"] == "unknown" or r["rating"] is None],
        key=priority_key,
    )

    with open(ENRICHMENT_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["hotel_id", "name", "location", "priority", "website_url",
                          "needs_description", "needs_price", "needs_rating",
                          "description", "price_range", "rating", "review_summary",
                          "nearby_attractions"])
        for r in needs_enrichment:
            writer.writerow([
                r["hotel_id"], r["name"], r["location"],
                "HIGH" if r["location"] in PRIORITY_LOCATIONS else "low",
                r.get("website_url") or "",
                "YES" if r["_description_is_placeholder"] else "",
                "YES" if r["price_range"] == "unknown" else "",
                "YES" if r["rating"] is None else "",
                "", "", "", "", "",  # blank columns for you to fill in by hand
            ])
    print(f"Wrote {len(needs_enrichment)} records needing enrichment to {ENRICHMENT_CSV}")
    print(f"  ({sum(1 for r in needs_enrichment if r['location'] in PRIORITY_LOCATIONS)} are in priority locations)")


if __name__ == "__main__":
    main()