"""
Embeddings - pluggable provider so switching from local (free) to OpenAI
(paid, if the boss sponsors credits) is a ONE-LINE config change, not a
rewrite.

Set the provider via environment variable:
    EMBEDDING_PROVIDER=local    (default - sentence-transformers, free, offline)
    EMBEDDING_PROVIDER=openai   (requires OPENAI_API_KEY env var)

Both providers expose the same interface: embed_texts(list[str]) -> list[list[float]]
so the rest of the RAG pipeline (vector_store.py, retrieval.py) never needs
to know or care which one is active.
"""

import os

PROVIDER = os.environ.get("EMBEDDING_PROVIDER", "local")

# ---- Local provider (sentence-transformers) ----
_local_model = None


def _get_local_model():
    global _local_model
    if _local_model is None:
        from sentence_transformers import SentenceTransformer
        # all-MiniLM-L6-v2: small, fast, free, runs on CPU, 384-dim vectors.
        # Good enough quality for a class project; no API key, no cost.
        _local_model = SentenceTransformer("all-MiniLM-L6-v2")
    return _local_model


def _embed_local(texts):
    model = _get_local_model()
    vectors = model.encode(texts, show_progress_bar=False, convert_to_numpy=True)
    return vectors.tolist()


# ---- OpenAI provider ----
def _embed_openai(texts):
    from openai import OpenAI
    client = OpenAI()  # reads OPENAI_API_KEY from environment automatically
    # text-embedding-3-small: cheap (~$0.02 per 1M tokens), 1536-dim vectors,
    # noticeably better retrieval quality than the local MiniLM model.
    response = client.embeddings.create(
        model="text-embedding-3-small",
        input=texts,
    )
    return [item.embedding for item in response.data]


def embed_texts(texts):
    """
    Embed a list of strings. Returns a list of vectors (list of floats).
    Batches internally are handled by each provider's own API/library.
    """
    if not texts:
        return []

    if PROVIDER == "openai":
        return _embed_openai(texts)
    elif PROVIDER == "local":
        return _embed_local(texts)
    else:
        raise ValueError(f"Unknown EMBEDDING_PROVIDER: {PROVIDER}")


def get_embedding_dimension():
    """Needed when initializing the vector store's index size."""
    if PROVIDER == "openai":
        return 1536  # text-embedding-3-small
    else:
        return 384   # all-MiniLM-L6-v2