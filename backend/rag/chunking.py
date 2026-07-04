"""
Chunking - converts our three record types (hotel, attraction, destination)
into a UNIFIED format: one embeddable text string + a metadata dict per chunk.

Design decision: one chunk per record (not splitting long text further).
Hotels/attractions are short structured records - splitting them would break
apart the very details (name + amenities + location) that make a chunk
useful. Destination content (Wikivoyage) is longer prose; we cap it at
~3000 chars at scrape time, which is already a reasonable single-chunk size
for an embedding model's context window.

Every chunk dict has the same shape:
{
    "id": unique string,
    "type": "hotel" | "attraction" | "destination",
    "text": the flattened natural-language string that gets embedded,
    "metadata": {..fields useful for filtering/display, varies by type..}
}
"""


def hotel_to_chunk(record):
    amenities = record.get("amenities") or []
    amenities_str = ", ".join(amenities) if amenities else "amenities not listed"

    price = record.get("price_range", "unknown")
    rating_str = f"rated {record['rating']}/5" if record.get("rating") else "not yet rated"

    text = (
        f"{record['name']} is a {record.get('category', 'hotel').lower()} in "
        f"{record['location']}, {record.get('county_region', '')}, {record['country']}. "
        f"Price range: {price}. {rating_str}. "
        f"{record.get('description', '')} "
        f"Amenities include {amenities_str}. "
    )
    if record.get("nearby_attractions"):
        text += f"Nearby attractions: {', '.join(record['nearby_attractions'])}. "
    if record.get("review_summary"):
        text += f"Guest reviews: {record['review_summary']}"

    return {
        "id": record["hotel_id"],
        "type": "hotel",
        "text": text.strip(),
        "metadata": {
            "name": record["name"],
            "location": record["location"],
            "country": record["country"],
            "price_range": price,
            "rating": record.get("rating"),
            "category": record.get("category"),
            "amenities": amenities,
            "source_url": record.get("source_url"),
            "website_url": record.get("website_url"),
        },
    }


def attraction_to_chunk(record):
    text = (
        f"{record['name']} is a {record.get('type', 'attraction').lower()} in "
        f"{record['location']}, {record.get('county_region', '')}, {record['country']}. "
        f"{record.get('description', '')}"
    )
    return {
        "id": record["attraction_id"],
        "type": "attraction",
        "text": text.strip(),
        "metadata": {
            "name": record["name"],
            "location": record["location"],
            "country": record["country"],
            "attraction_type": record.get("type"),
            "source_url": record.get("source_url"),
        },
    }


def destination_to_chunk(record):
    text = f"About {record['location']}, {record['country']}: {record['content']}"
    return {
        "id": record["destination_id"],
        "type": "destination",
        "text": text.strip(),
        "metadata": {
            "location": record["location"],
            "country": record["country"],
            "source_url": record.get("source_url"),
        },
    }


def build_all_chunks(hotels, attractions, destinations):
    """Combine all three record types into one flat list of chunks."""
    chunks = []
    chunks.extend(hotel_to_chunk(r) for r in hotels)
    chunks.extend(attraction_to_chunk(r) for r in attractions)
    chunks.extend(destination_to_chunk(r) for r in destinations)
    return chunks