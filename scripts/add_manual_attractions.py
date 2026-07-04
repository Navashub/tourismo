"""
Manual fallback records for locations where OSM/Overpass consistently failed
(Maasai Mara, Watamu) after multiple retry attempts across mirrors.

These are real, well-documented, notable sites - manually entered because an
automated source failed, not because we skipped due diligence. This is
explicitly allowed by the project brief ("where scraping is difficult, you
may manually collect data from public sources").

Run this after retry_missing_attractions.py to merge these in.
"""

import json
from datetime import date

OUT_PATH = "data/raw_attractions_osm.json"

MANUAL_RECORDS = [
    {
        "attraction_id": "ATT-KE-MAASAI-M01",
        "name": "Maasai Mara National Reserve",
        "location": "Maasai Mara",
        "county_region": "Narok County",
        "country": "Kenya",
        "type": "National Park",
        "description": "Kenya's most famous game reserve, known for the Great Wildebeest Migration and dense populations of lions, leopards, cheetahs, and elephants.",
        "website_url": None,
        "latitude": -1.4833,
        "longitude": 35.1500,
        "source_url": "https://en.wikivoyage.org/wiki/Maasai_Mara_National_Reserve",
        "last_updated": str(date.today()),
    },
    {
        "attraction_id": "ATT-KE-MAASAI-M02",
        "name": "Mara River",
        "location": "Maasai Mara",
        "county_region": "Narok County",
        "country": "Kenya",
        "type": "Natural Landmark",
        "description": "The river famous for the dramatic wildebeest and zebra crossings during the annual Great Migration, typically between July and October.",
        "website_url": None,
        "latitude": -1.5833,
        "longitude": 35.2333,
        "source_url": "https://en.wikipedia.org/wiki/Mara_River",
        "last_updated": str(date.today()),
    },
    {
        "attraction_id": "ATT-KE-MAASAI-M03",
        "name": "Mara Triangle",
        "location": "Maasai Mara",
        "county_region": "Narok County",
        "country": "Kenya",
        "type": "Conservancy",
        "description": "A less-crowded western section of the Maasai Mara ecosystem managed by the Mara Conservancy, known for excellent game viewing with fewer vehicles.",
        "website_url": None,
        "latitude": -1.4000,
        "longitude": 35.0500,
        "source_url": "https://en.wikivoyage.org/wiki/Maasai_Mara_National_Reserve",
        "last_updated": str(date.today()),
    },
    {
        "attraction_id": "ATT-KE-WATAMU-M01",
        "name": "Watamu Marine National Park",
        "location": "Watamu",
        "county_region": "Kilifi County",
        "country": "Kenya",
        "type": "Marine Park",
        "description": "A protected marine park known for coral reefs, snorkeling, and diving, home to sea turtles and diverse tropical fish species.",
        "website_url": None,
        "latitude": -3.3667,
        "longitude": 40.0167,
        "source_url": "https://en.wikipedia.org/wiki/Watamu_Marine_National_Park",
        "last_updated": str(date.today()),
    },
    {
        "attraction_id": "ATT-KE-WATAMU-M02",
        "name": "Arabuko Sokoke Forest",
        "location": "Watamu",
        "county_region": "Kilifi County",
        "country": "Kenya",
        "type": "Nature Reserve",
        "description": "The largest remaining coastal forest in East Africa, home to rare bird species and the endangered Sokoke scops owl.",
        "website_url": None,
        "latitude": -3.3167,
        "longitude": 39.8833,
        "source_url": "https://en.wikipedia.org/wiki/Arabuko-Sokoke_Forest",
        "last_updated": str(date.today()),
    },
    {
        "attraction_id": "ATT-KE-WATAMU-M03",
        "name": "Gede Ruins",
        "location": "Watamu",
        "county_region": "Kilifi County",
        "country": "Kenya",
        "type": "Historical Site",
        "description": "The ruins of a 12th-century Swahili trading town, now a national monument set within coastal forest.",
        "website_url": None,
        "latitude": -3.3103,
        "longitude": 40.0136,
        "source_url": "https://en.wikipedia.org/wiki/Gede_Ruins",
        "last_updated": str(date.today()),
    },
]


def main():
    with open(OUT_PATH, encoding="utf-8") as f:
        records = json.load(f)

    existing_keys = {(r["name"].strip().lower(), r["location"]) for r in records}
    added = 0
    for record in MANUAL_RECORDS:
        key = (record["name"].strip().lower(), record["location"])
        if key not in existing_keys:
            records.append(record)
            added += 1

    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(records, f, indent=2)

    print(f"Added {added} manual records. Total attractions: {len(records)}")


if __name__ == "__main__":
    main()