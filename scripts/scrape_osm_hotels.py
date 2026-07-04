"""
Travel Africa RAG Project - Step 1: Automated hotel data collection via OpenStreetMap
=======================================================================================
Uses the Overpass API (OSM's public query service) to pull hotel/lodging POIs for
every required location. This is a legitimate, ethical data source:
  - OSM data is open (ODbL license), explicitly meant for programmatic use
  - No robots.txt conflict, no anti-bot measures to fight
  - We still rate-limit ourselves out of courtesy to the free public endpoint

Output: data/raw_hotels_osm.json
Each record maps to our schema's structural fields (name, location, coords,
category, contact, website, source_url). Free-text fields (description,
review_summary, price_range, nearby_attractions) will mostly be EMPTY here -
that's expected. Step 2 enriches those manually/semi-manually.
"""

import requests
import json
import time
import os
from datetime import date

# overpass-api.de has recently started rejecting requests that lack browser-like
# headers with a blanket 406 (to fend off AI scraper load). We send a proper
# User-Agent, and fall back to a mirror instance if the primary one still blocks us.
OVERPASS_ENDPOINTS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass.private.coffee/api/interpreter",
]

HEADERS = {
    "User-Agent": "TravelAfricaRAGProject/1.0 (student class project; contact: your-email@example.com)",
    "Accept": "application/json",
}

# Center coordinates + search radius (meters) for each required location.
# Radius chosen to roughly cover the town/area without pulling in a whole region.
LOCATIONS = {
    "Nairobi":      {"lat": -1.2921,  "lon": 36.8219,  "radius": 12000, "county": "Nairobi County",  "country": "Kenya"},
    "Mombasa":      {"lat": -4.0435,  "lon": 39.6682,  "radius": 10000, "county": "Mombasa County",  "country": "Kenya"},
    "Diani":        {"lat": -4.3167,  "lon": 39.5667,  "radius": 8000,  "county": "Kwale County",    "country": "Kenya"},
    "Naivasha":     {"lat": -0.7167,  "lon": 36.4333,  "radius": 10000, "county": "Nakuru County",   "country": "Kenya"},
    "Nakuru":       {"lat": -0.3031,  "lon": 36.0800,  "radius": 10000, "county": "Nakuru County",   "country": "Kenya"},
    "Maasai Mara":  {"lat": -1.4833,  "lon": 35.1500,  "radius": 25000, "county": "Narok County",    "country": "Kenya"},
    "Amboseli":     {"lat": -2.6500,  "lon": 37.2500,  "radius": 20000, "county": "Kajiado County",  "country": "Kenya"},
    "Watamu":       {"lat": -3.3500,  "lon": 40.0167,  "radius": 6000,  "county": "Kilifi County",   "country": "Kenya"},
    "Malindi":      {"lat": -3.2175,  "lon": 40.1191,  "radius": 8000,  "county": "Kilifi County",   "country": "Kenya"},
    "Kisumu":       {"lat": -0.0917,  "lon": 34.7680,  "radius": 8000,  "county": "Kisumu County",   "country": "Kenya"},
    "Nanyuki":      {"lat": 0.0167,   "lon": 37.0667,  "radius": 8000,  "county": "Laikipia County", "country": "Kenya"},
    "Lamu":         {"lat": -2.2717,  "lon": 40.9020,  "radius": 6000,  "county": "Lamu County",     "country": "Kenya"},
    "Zanzibar":     {"lat": -6.1659,  "lon": 39.2026,  "radius": 20000, "county": "Zanzibar Urban",  "country": "Tanzania"},
    "Arusha":       {"lat": -3.3869,  "lon": 36.6830,  "radius": 10000, "county": "Arusha Region",   "country": "Tanzania"},
    "Kampala":      {"lat": 0.3476,   "lon": 32.5825,  "radius": 12000, "county": "Central Region",  "country": "Uganda"},
    "Dar es Salaam":{"lat": -6.7924,  "lon": 39.2083,  "radius": 12000, "county": "Dar es Salaam Region", "country": "Tanzania"},
}

# OSM tourism values that represent lodging (hotel is the main one, others catch more records)
LODGING_TAGS = ["hotel", "guest_house", "motel", "resort", "hostel"]


def build_query(lat, lon, radius):
    """Build an Overpass QL query for lodging nodes/ways around a point."""
    tag_filter = "|".join(LODGING_TAGS)
    query = f"""
    [out:json][timeout:60];
    (
      node["tourism"~"^({tag_filter})$"](around:{radius},{lat},{lon});
      way["tourism"~"^({tag_filter})$"](around:{radius},{lat},{lon});
    );
    out center tags;
    """
    return query


def fetch_location(location_name, meta):
    print(f"  Querying {location_name} ...")
    query = build_query(meta["lat"], meta["lon"], meta["radius"])

    last_error = None
    for endpoint in OVERPASS_ENDPOINTS:
        try:
            resp = requests.post(
                endpoint, data={"data": query}, headers=HEADERS, timeout=90
            )
            resp.raise_for_status()
            elements = resp.json().get("elements", [])
            print(f"    -> {len(elements)} raw results (via {endpoint})")
            return elements
        except requests.exceptions.RequestException as e:
            last_error = e
            print(f"    .. {endpoint} failed ({e}), trying next mirror")
            time.sleep(1)

    raise last_error


def normalize_record(element, location_name, meta, idx):
    tags = element.get("tags", {})
    # ways return a "center" object for coordinates; nodes have lat/lon directly
    lat = element.get("lat") or element.get("center", {}).get("lat")
    lon = element.get("lon") or element.get("center", {}).get("lon")

    name = tags.get("name")
    if not name:
        return None  # skip unnamed POIs, not usable in a RAG assistant

    loc_code = location_name.upper().replace(" ", "")[:6]
    country_code = {"Kenya": "KE", "Tanzania": "TZ", "Uganda": "UG"}.get(meta["country"], "XX")

    record = {
        "hotel_id": f"{country_code}-{loc_code}-{idx:03d}",
        "name": name,
        "location": location_name,
        "county_region": meta["county"],
        "country": meta["country"],
        "category": tags.get("tourism", "hotel").replace("_", " ").title(),
        "price_range": None,          # to enrich
        "price_range_usd": None,      # to enrich
        "rating": None,               # to enrich
        "description": None,          # to enrich
        "amenities": [t for t in [
            "wifi" if tags.get("internet_access") in ("wlan", "yes") else None,
            "restaurant" if tags.get("restaurant") == "yes" else None,
            "pool" if tags.get("swimming_pool") == "yes" else None,
            "parking" if tags.get("parking") else None,
            "air conditioning" if tags.get("air_conditioning") == "yes" else None,
        ] if t],
        "room_types": [],             # to enrich
        "review_summary": None,       # to enrich
        "nearby_attractions": [],     # to enrich
        "contact": {
            "phone": tags.get("phone") or tags.get("contact:phone"),
            "email": tags.get("email") or tags.get("contact:email"),
        },
        "website_url": tags.get("website") or tags.get("contact:website"),
        "image_url": tags.get("image"),
        "latitude": lat,
        "longitude": lon,
        "address": tags.get("addr:full") or tags.get("addr:street"),
        "stars": tags.get("stars"),
        "source_url": f"https://www.openstreetmap.org/{element['type']}/{element['id']}",
        "last_updated": str(date.today()),
    }
    return record


def main():
    all_records = []
    seen_names = set()
    os.makedirs("data", exist_ok=True)
    out_path = "data/raw_hotels_osm.json"

    for location_name, meta in LOCATIONS.items():
        try:
            elements = fetch_location(location_name, meta)
        except requests.exceptions.RequestException as e:
            print(f"    !! Failed to fetch {location_name}: {e}")
            continue

        idx = 1
        for el in elements:
            record = normalize_record(el, location_name, meta, idx)
            if record is None:
                continue
            # simple dedupe: same name + same location
            dedupe_key = (record["name"].strip().lower(), location_name)
            if dedupe_key in seen_names:
                continue
            seen_names.add(dedupe_key)
            all_records.append(record)
            idx += 1

        # Save after every location so a crash/timeout later never loses
        # everything collected so far.
        with open(out_path, "w") as f:
            json.dump(all_records, f, indent=2)

        time.sleep(2)  # be polite to the free public Overpass instance

    print(f"\nDone. {len(all_records)} unique hotel records saved to {out_path}")
    print("Breakdown by location:")
    from collections import Counter
    counts = Counter(r["location"] for r in all_records)
    for loc, count in counts.items():
        print(f"  {loc}: {count}")


if __name__ == "__main__":
    main()