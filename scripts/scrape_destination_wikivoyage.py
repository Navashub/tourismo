"""
Destination content scraper - pulls narrative "what is this place like, what
can you do here" content from Wikivoyage's public API.

Wikivoyage is a Wikimedia project - openly licensed (CC BY-SA), built with an
API specifically for programmatic access, no scraping ethics concerns at all.

This is what makes queries like "plan a 6-day Kenya trip covering safari,
coast, and culture" actually answerable - hotel listings alone can't answer
"what is Maasai Mara like" or "what's the culture scene in Nairobi."

Output: data/raw_destinations_wikivoyage.json
"""

import requests
import json
import time
import os
from datetime import date

from scrape_osm_hotels import LOCATIONS

WIKIVOYAGE_API = "https://en.wikivoyage.org/w/api.php"

HEADERS = {
    "User-Agent": "TravelAfricaRAGProject/1.0 (student class project; contact: your-email@example.com)"
}

# Wikivoyage page titles may differ slightly from our location names -
# override where needed (e.g. "Zanzibar" is a whole archipelago page)
WIKIVOYAGE_TITLE_OVERRIDES = {
    "Maasai Mara": "Maasai Mara National Reserve",  # note: double-A "Maasai", not "Masai"
    "Diani": "Diani Beach",
    "Amboseli": "Amboseli National Park",
}


def search_best_title(query):
    """
    Fallback for when the direct title guess doesn't exist on Wikivoyage.
    Asks Wikivoyage's own search API for the closest matching page title.
    This makes onboarding NEW locations later more robust - you don't need
    to know the exact page title in advance, just a reasonable search term.
    """
    params = {
        "action": "query",
        "format": "json",
        "list": "search",
        "srsearch": query,
        "srlimit": 1,
    }
    resp = requests.get(WIKIVOYAGE_API, params=params, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    results = resp.json().get("query", {}).get("search", [])
    if results:
        return results[0]["title"]
    return None


def fetch_extract(title):
    """Fetch the plain-text summary/extract of a Wikivoyage page."""
    params = {
        "action": "query",
        "format": "json",
        "prop": "extracts",
        "explaintext": 1,
        "titles": title,
    }
    resp = requests.get(WIKIVOYAGE_API, params=params, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    pages = resp.json().get("query", {}).get("pages", {})
    for page_id, page in pages.items():
        if page_id == "-1":  # Wikivoyage's code for "page not found"
            return None, None
        extract = page.get("extract", "")
        return extract, f"https://en.wikivoyage.org/wiki/{title.replace(' ', '_')}"
    return None, None


def main():
    os.makedirs("data", exist_ok=True)
    out_path = "data/raw_destinations_wikivoyage.json"
    records = []

    for location_name, meta in LOCATIONS.items():
        title = WIKIVOYAGE_TITLE_OVERRIDES.get(location_name, location_name)
        print(f"  Fetching Wikivoyage page for {location_name} (title: {title}) ...")

        try:
            extract, url = fetch_extract(title)
            if not extract:
                # Direct title didn't exist - try search fallback
                better_title = search_best_title(location_name)
                if better_title and better_title != title:
                    print(f"    -> direct title not found, trying search match: '{better_title}'")
                    extract, url = fetch_extract(better_title)
        except requests.exceptions.RequestException as e:
            print(f"    !! Failed: {e}")
            continue

        if not extract:
            print(f"    -> No Wikivoyage page found for '{title}', skipping")
            continue

        # Trim to a reasonable chunk size - Wikivoyage pages can be very long,
        # we mainly want the intro + "Understand"/"Do" sections worth of content
        trimmed = extract[:3000]

        records.append({
            "destination_id": f"DEST-{location_name.upper().replace(' ', '')[:8]}",
            "location": location_name,
            "country": meta["country"],
            "content": trimmed,
            "source_url": url,
            "last_updated": str(date.today()),
        })
        print(f"    -> {len(trimmed)} characters fetched")

        time.sleep(1.5)  # polite delay between requests

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(records, f, indent=2, ensure_ascii=False)

    print(f"\nDone. {len(records)} destination records saved to {out_path}")


if __name__ == "__main__":
    main()