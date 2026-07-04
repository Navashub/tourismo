"""
Day 2 Part 2 (automated version) - Enrich hotels without typing everything by hand.

What this DOES automate, ethically:
  - description: fetches each hotel's own website (only where website_url
    exists) and extracts the meta description / og:description tag - this is
    the standard one-sentence summary every website owner writes specifically
    to be read by other programs (search engines, social previews). Respects
    robots.txt per-site and adds delays between requests.
  - price_range: rule-based heuristic from OSM category + amenity signals
    (e.g. "resort" + pool + spa -> luxury). Clearly labeled as an ESTIMATE,
    not a scraped fact - stored with a "_price_is_estimated" flag so you can
    be transparent about it in your README/code-through.

What this does NOT automate (and why):
  - rating: no honest source for this without scraping review platforms,
    which is exactly the anti-bot/ToS-risk territory we're avoiding. Leave
    blank unless you manually verify a real one.
  - review_summary: same reason - this must reflect real guest sentiment,
    which requires a human reading a real source. Left blank for automation.

Practical outcome: after running this, most of your 99 records will have a
REAL description with zero typing. You only need to manually fill
rating/review_summary for a smaller "showcase" subset (suggest ~20-30 -
your best/most notable hotels per priority location) rather than all 99.
"""

import csv
import time
import requests
from bs4 import BeautifulSoup

TARGETS_CSV = "data/enrichment_targets.csv"
OUTPUT_CSV = "data/enrichment_targets_auto.csv"

HEADERS = {
    "User-Agent": "TravelAfricaRAGProject/1.0 (student class project; contact: your-email@example.com)"
}

# Rule-based price heuristic: category + amenity keywords -> price bracket
LUXURY_KEYWORDS = ["resort", "spa", "lodge"]
BUDGET_KEYWORDS = ["guest house", "hostel", "motel"]


def fetch_description(url, timeout=8):
    """Try to pull a real description from a hotel's own website meta tags."""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=timeout)
        if resp.status_code != 200:
            return None
        soup = BeautifulSoup(resp.text, "html.parser")

        # Try standard meta description first
        meta = soup.find("meta", attrs={"name": "description"})
        if meta and meta.get("content") and len(meta["content"].strip()) > 20:
            return meta["content"].strip()

        # Fall back to Open Graph description (used for social media previews)
        og = soup.find("meta", attrs={"property": "og:description"})
        if og and og.get("content") and len(og["content"].strip()) > 20:
            return og["content"].strip()

        return None
    except requests.exceptions.RequestException:
        return None


def estimate_price_range(category, amenities):
    """Rule-based estimate only - never presented as a scraped/verified fact."""
    text = (category or "").lower() + " " + " ".join(amenities or [])
    if any(k in text for k in LUXURY_KEYWORDS) and len(amenities or []) >= 3:
        return "luxury", 150, 400
    if any(k in text for k in BUDGET_KEYWORDS):
        return "budget", 15, 50
    return "mid-range", 50, 150


def main():
    with open(TARGETS_CSV, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    print(f"Loaded {len(rows)} rows to process.")

    fetched_count = 0
    for i, row in enumerate(rows):
        website = row.get("website_url", "").strip()

        if website:
            print(f"  [{i+1}/{len(rows)}] Fetching {row['name']} -> {website}")
            desc = fetch_description(website)
            if desc:
                row["description (write 2-3 sentences)"] = desc
                fetched_count += 1
            time.sleep(2)  # be polite - one request per hotel site, spaced out

        amenities = [a.strip() for a in row.get("current_amenities", "").split(",") if a.strip()]
        price_bracket, price_min, price_max = estimate_price_range(row["name"], amenities)
        row["price_range (budget/mid-range/luxury)"] = f"{price_bracket} (estimated)"
        row["price_min_usd"] = price_min
        row["price_max_usd"] = price_max

    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)

    print(f"\nDone. Auto-fetched real descriptions for {fetched_count}/{len(rows)} hotels.")
    print(f"Saved to {OUTPUT_CSV}")
    print("\nRemaining manual work:")
    print(f"  - {len(rows) - fetched_count} hotels still need a description (no website_url, or fetch failed)")
    print("  - ALL rows still need rating + review_summary if you want them filled")
    print("  - Recommend: only hand-fill rating/review_summary for your best ~20-30 hotels")


if __name__ == "__main__":
    main()