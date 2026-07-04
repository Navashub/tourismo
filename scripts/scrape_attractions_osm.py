"""
Attractions scraper - same pattern as scrape_osm_hotels.py, different tags.

OSM tags a wide range of attraction types. We pull the ones relevant to
tourism planning: attractions, museums, viewpoints, national parks, wildlife
reserves, beaches, zoos.

Output: data/raw_attractions_osm.json
"""

import requests
import json
import time
import os
from datetime import date

from scrape_osm_hotels import LOCATIONS, OVERPASS_ENDPOINTS, HEADERS

# OSM tag:value pairs worth pulling for a tourism/trip-planning use case
ATTRACTION_TAGS = [
    ('tourism', 'attraction'),
    ('tourism', 'museum'),
    ('tourism', 'viewpoint'),
    ('tourism', 'zoo'),
    ('tourism', 'theme_park'),
    ('leisure', 'nature_reserve'),
    ('leisure', 'park'),
    ('boundary', 'national_park'),
    ('natural', 'beach'),
]


def build_query(lat, lon, radius):
    clauses = []
    for key, value in ATTRACTION_TAGS:
        clauses.append(f'node["{key}"="{value}"](around:{radius},{lat},{lon});')
        clauses.append(f'way["{key}"="{value}"](around:{radius},{lat},{lon});')
    body = "\n      ".join(clauses)
    return f"""
    [out:json][timeout:60];
    (
      {body}
    );
    out center tags;
    """


def fetch_location(location_name, meta):
    print(f"  Querying attractions near {location_name} ...")
    query = build_query(meta["lat"], meta["lon"], meta["radius"])
    last_error = None
    for endpoint in OVERPASS_ENDPOINTS:
        try:
            resp = requests.post(endpoint, data={"data": query}, headers=HEADERS, timeout=90)
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
    lat = element.get("lat") or element.get("center", {}).get("lat")
    lon = element.get("lon") or element.get("center", {}).get("lon")

    name = tags.get("name")
    if not name:
        return None

    # Figure out attraction "type" from whichever tag matched
    attraction_type = (
        tags.get("tourism") or tags.get("leisure") or
        tags.get("boundary") or tags.get("natural") or "attraction"
    )

    loc_code = location_name.upper().replace(" ", "")[:6]
    country_code = {"Kenya": "KE", "Tanzania": "TZ", "Uganda": "UG"}.get(meta["country"], "XX")

    return {
        "attraction_id": f"ATT-{country_code}-{loc_code}-{idx:03d}",
        "name": name,
        "location": location_name,
        "county_region": meta["county"],
        "country": meta["country"],
        "type": attraction_type.replace("_", " ").title(),
        "description": tags.get("description"),  # often missing, enrich later
        "website_url": tags.get("website") or tags.get("contact:website"),
        "latitude": lat,
        "longitude": lon,
        "source_url": f"https://www.openstreetmap.org/{element['type']}/{element['id']}",
        "last_updated": str(date.today()),
    }


def main():
    all_records = []
    seen = set()
    os.makedirs("data", exist_ok=True)
    out_path = "data/raw_attractions_osm.json"

    for location_name, meta in LOCATIONS.items():
        try:
            elements = fetch_location(location_name, meta)
        except requests.exceptions.RequestException as e:
            print(f"    !! Failed to fetch attractions for {location_name}: {e}")
            continue

        idx = 1
        for el in elements:
            record = normalize_record(el, location_name, meta, idx)
            if record is None:
                continue
            key = (record["name"].strip().lower(), location_name)
            if key in seen:
                continue
            seen.add(key)
            all_records.append(record)
            idx += 1

        with open(out_path, "w") as f:
            json.dump(all_records, f, indent=2)
        time.sleep(2)

    print(f"\nDone. {len(all_records)} attraction records saved to {out_path}")
    from collections import Counter
    counts = Counter(r["location"] for r in all_records)
    for loc, count in counts.items():
        print(f"  {loc}: {count}")


if __name__ == "__main__":
    main()