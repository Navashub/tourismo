"""
Day 2 final step - merge enrichment_targets_auto.csv back into cleaned_hotels.json.

Matches rows by hotel_id, overwrites the placeholder description/price/rating/
review_summary/nearby_attractions fields with your enriched values - but only
where the CSV cell is actually filled in. Blank cells are left as-is (still
"unknown"/placeholder), never overwritten with emptiness.
"""

import json
import csv

CLEANED_PATH = "data/processed/cleaned_hotels.json"
ENRICHED_CSV = "data/processed/enrichment_targets_final.csv"
OUTPUT_PATH = "data/processed/final_hotels.json"


def main():
    with open(CLEANED_PATH, encoding="utf-8") as f:
        hotels = json.load(f)
    hotels_by_id = {h["hotel_id"]: h for h in hotels}

    with open(ENRICHED_CSV, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    updated_count = 0
    for row in rows:
        hotel_id = row["hotel_id"]
        hotel = hotels_by_id.get(hotel_id)
        if not hotel:
            print(f"  !! Warning: {hotel_id} from CSV not found in cleaned_hotels.json, skipping")
            continue

        description = row.get("description (write 2-3 sentences)", "").strip()
        if description:
            hotel["description"] = description
            hotel["_description_is_placeholder"] = False

        price_range = row.get("price_range (budget/mid-range/luxury)", "").strip()
        if price_range:
            # strip the "(estimated)" tag we added for transparency, keep the label itself
            hotel["price_range"] = price_range.replace(" (estimated)", "")
            hotel["_price_is_estimated"] = "(estimated)" in price_range

        price_min = row.get("price_min_usd", "").strip()
        price_max = row.get("price_max_usd", "").strip()
        if price_min and price_max:
            try:
                hotel["price_range_usd"] = {"min": float(price_min), "max": float(price_max)}
            except ValueError:
                pass

        rating = row.get("rating (0-5, only if you can verify one)", "").strip()
        if rating:
            try:
                r = float(rating)
                if 0 <= r <= 5:
                    hotel["rating"] = r
            except ValueError:
                pass

        review_summary = row.get("review_summary (1-2 sentences)", "").strip()
        if review_summary:
            hotel["review_summary"] = review_summary

        attractions = row.get("nearby_attractions (comma-separated)", "").strip()
        if attractions:
            hotel["nearby_attractions"] = [a.strip() for a in attractions.split(",") if a.strip()]

        updated_count += 1

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(hotels, f, indent=2, ensure_ascii=False)

    enriched_with_desc = sum(1 for h in hotels if not h.get("_description_is_placeholder", True))
    enriched_with_rating = sum(1 for h in hotels if h.get("rating") is not None)

    print(f"Processed {updated_count} rows from enrichment CSV.")
    print(f"Saved final dataset ({len(hotels)} hotels total) to {OUTPUT_PATH}")
    print(f"  {enriched_with_desc} hotels have a real (non-placeholder) description")
    print(f"  {enriched_with_rating} hotels have a verified rating")


if __name__ == "__main__":
    main()