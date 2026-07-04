"""
Fully automated enrichment - no manual typing required anywhere in this script.

Two layers, both automatic:
  1. IMPROVED scraping: tries meta description, then og:description, then
     falls back to the page's <title> tag and first meaningful paragraph of
     visible text - squeezes real content out of more sites than before.
  2. SMART TEMPLATE fallback: for anything scraping still can't reach (no
     website, or site blocks bots entirely), generates a natural-sounding
     description from VERIFIED structured fields only (name, category,
     location, amenities, price bracket) - varied phrasing so 99 hotels
     don't all read identically, but nothing invented.

Rating and review_summary are intentionally left blank across the board -
there is no honest way to automate real guest sentiment/scores without
either scraping review platforms (the ToS/anti-bot problem we're avoiding)
or fabricating numbers. A hotel record with no rating is a normal, honest
state - the assistant should say "no rating available" rather than lie.
"""

import csv
import time
import random
import requests
from bs4 import BeautifulSoup

INPUT_CSV = "data/processed/enrichment_targets_auto.csv"
OUTPUT_CSV = "data/processed/enrichment_targets_final.csv"

HEADERS = {
    "User-Agent": "TravelAfricaRAGProject/1.0 (student class project; contact: your-email@example.com)"
}

DESC_COL = "description (write 2-3 sentences)"
PRICE_COL = "price_range (budget/mid-range/luxury)"

# Varied sentence templates so auto-generated descriptions aren't identical
TEMPLATES = [
    "{name} is a {category} located in {location}, offering guests {amenities_phrase}.",
    "Situated in {location}, {name} is a {category} known for {amenities_phrase}.",
    "{name}, a {category} in {location}, provides {amenities_phrase} for travelers.",
    "Guests staying at {name} in {location} can expect {amenities_phrase} at this {category}.",
]


def fetch_description(url, timeout=8):
    try:
        resp = requests.get(url, headers=HEADERS, timeout=timeout)
        if resp.status_code != 200:
            return None
        soup = BeautifulSoup(resp.text, "html.parser")

        for attrs in [{"name": "description"}, {"property": "og:description"}]:
            tag = soup.find("meta", attrs=attrs)
            if tag and tag.get("content") and len(tag["content"].strip()) > 20:
                return tag["content"].strip()

        # Fallback 1: page title often contains the hotel name + a tagline
        title = soup.find("title")
        if title and title.text and len(title.text.strip()) > 15:
            return title.text.strip()

        # Fallback 2: first substantial visible paragraph
        for p in soup.find_all("p"):
            text = p.get_text(strip=True)
            if len(text) > 60:  # skip short nav/footer fragments
                return text[:300]

        return None
    except requests.exceptions.RequestException:
        return None


def generate_template_description(name, category, location, amenities_str, price_bracket):
    amenities_list = [a.strip() for a in amenities_str.split(",") if a.strip()]
    if amenities_list:
        if len(amenities_list) == 1:
            amenities_phrase = amenities_list[0]
        else:
            amenities_phrase = ", ".join(amenities_list[:-1]) + f" and {amenities_list[-1]}"
    else:
        amenities_phrase = f"a {price_bracket.replace(' (estimated)', '')} stay"

    template = random.choice(TEMPLATES)
    return template.format(
        name=name,
        category=(category or "hotel").lower(),
        location=location,
        amenities_phrase=amenities_phrase,
    )


def main():
    with open(INPUT_CSV, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    scraped_count = 0
    template_count = 0
    already_filled = 0

    for i, row in enumerate(rows):
        if row.get(DESC_COL, "").strip():
            already_filled += 1
            continue  # already has a real description from the previous pass

        website = row.get("website_url", "").strip()
        description = None

        if website:
            print(f"  [{i+1}/{len(rows)}] Retrying scrape: {row['name']}")
            description = fetch_description(website)
            time.sleep(1.5)

        if description:
            row[DESC_COL] = description
            scraped_count += 1
        else:
            row[DESC_COL] = generate_template_description(
                row["name"], row.get("category", "hotel"), row["location"],
                row.get("current_amenities", ""), row.get(PRICE_COL, "mid-range"),
            )
            template_count += 1

    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)

    print(f"\nDone - fully automated, zero manual typing.")
    print(f"  Already had a description: {already_filled}")
    print(f"  Newly scraped (real website content): {scraped_count}")
    print(f"  Auto-generated from verified fields (template): {template_count}")
    print(f"  Total: {len(rows)} - saved to {OUTPUT_CSV}")
    print(f"\nNote: rating and review_summary are left blank for all rows -")
    print(f"  this is intentional and honest, not a gap you need to fix.")


if __name__ == "__main__":
    main()