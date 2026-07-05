"""
Day 3 - Build the vector store.

Loads cleaned hotels + raw attractions + raw destinations, converts them all
to chunks, embeds them, and saves a searchable vector store to disk.

Run from the project root (tourismo/):
    python backend/build_index.py

Switch embedding provider before running:
    export EMBEDDING_PROVIDER=local     (default, free, offline)
    export EMBEDDING_PROVIDER=openai    (needs OPENAI_API_KEY set)
On Windows/git-bash use: EMBEDDING_PROVIDER=openai python backend/build_index.py
"""

import json
import sys
import os

from dotenv import load_dotenv
load_dotenv()

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.rag.chunking import build_all_chunks
from backend.rag.vector_store import VectorStore

HOTELS_PATH = "data/processed/final_hotels.json"
ATTRACTIONS_PATH = "data/raw/raw_attractions_osm.json"
DESTINATIONS_PATH = "data/raw/raw_destinations_wikivoyage.json"
INDEX_OUTPUT_PATH = "data/processed/vector_index"


def load_json(path):
    if not os.path.exists(path):
        print(f"  !! Warning: {path} not found, skipping this data type.")
        return []
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def main():
    print("Loading data...")
    hotels = load_json(HOTELS_PATH)
    attractions = load_json(ATTRACTIONS_PATH)
    destinations = load_json(DESTINATIONS_PATH)
    print(f"  {len(hotels)} hotels, {len(attractions)} attractions, {len(destinations)} destinations")

    print("Building chunks...")
    chunks = build_all_chunks(hotels, attractions, destinations)
    print(f"  {len(chunks)} total chunks to embed")

    provider = os.environ.get("EMBEDDING_PROVIDER", "local")
    print(f"Embedding using provider: {provider} ...")

    store = VectorStore()
    store.add_chunks(chunks)

    print(f"Saving vector store to {INDEX_OUTPUT_PATH}...")
    store.save(INDEX_OUTPUT_PATH)

    print(f"\nDone. Indexed {len(chunks)} chunks ({provider} embeddings, "
          f"{store.dimension}-dim vectors).")


if __name__ == "__main__":
    main()