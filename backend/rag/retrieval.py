"""
Retrieval - loads the saved vector store once at startup, exposes a simple
search function the API endpoints call.
"""

from .vector_store import VectorStore

_store = None


def get_store(index_path="data/processed/vector_index"):
    global _store
    if _store is None:
        print(f"Loading vector store from {index_path}...")
        _store = VectorStore.load(index_path)
        print(f"Loaded {len(_store.chunks)} chunks.")
    return _store


def retrieve(question, top_k=5, filter_type=None, filter_location=None):
    store = get_store()
    return store.search(question, top_k=top_k, filter_type=filter_type, filter_location=filter_location)


def retrieve_diverse(question, filter_location=None, per_type=3):
    """
    Instead of one global top-k search (where hotels can crowd out
    attractions/destinations just because there are more of them in the
    dataset), search each type separately and merge results. This
    guarantees the LLM sees a genuine MIX of hotels, attractions, and
    destination context - important for exploratory questions like
    "places to visit in X" where attraction diversity matters more than
    raw similarity score.
    """
    store = get_store()
    results = []
    for chunk_type in ["hotel", "attraction", "destination"]:
        results.extend(
            store.search(question, top_k=per_type, filter_type=chunk_type, filter_location=filter_location)
        )
    # Re-sort the merged set by score so the most relevant overall still lead
    results.sort(key=lambda r: r["score"], reverse=True)
    return results