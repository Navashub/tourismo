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