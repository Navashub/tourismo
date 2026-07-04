"""
Vector store - a thin, custom wrapper directly around FAISS (not LangChain's
FAISS wrapper). We control exactly what's stored and how search works, which
matters for the code-through: every line here is explainable.

Stores:
  - a FAISS index (the vectors themselves, for fast similarity search)
  - a parallel list of chunk dicts (id, type, text, metadata) - FAISS only
    knows about numbers, so we keep the actual content/metadata ourselves,
    indexed by the same position as its vector.
"""

import json
import os
import numpy as np
import faiss

from .embeddings import embed_texts, get_embedding_dimension


class VectorStore:
    def __init__(self, dimension=None):
        self.dimension = dimension or get_embedding_dimension()
        # IndexFlatIP = exact search using inner product (cosine similarity,
        # since we normalize vectors below). "Flat" means brute-force - no
        # approximation - which is completely fine at our data scale
        # (hundreds to low thousands of chunks). Approximate indexes (IVF,
        # HNSW) only start mattering at hundreds of thousands+ of vectors.
        self.index = faiss.IndexFlatIP(self.dimension)
        self.chunks = []  # parallel list: chunks[i] corresponds to vector i

    def _normalize(self, vectors):
        """L2-normalize so inner product == cosine similarity."""
        vectors = np.array(vectors, dtype="float32")
        norms = np.linalg.norm(vectors, axis=1, keepdims=True)
        norms[norms == 0] = 1e-10  # avoid division by zero on a zero vector
        return vectors / norms

    def add_chunks(self, chunks, batch_size=64):
        """Embed and add a list of chunk dicts (from chunking.py) to the store."""
        texts = [c["text"] for c in chunks]

        all_vectors = []
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            print(f"  Embedding batch {i}-{i+len(batch)} of {len(texts)}...")
            vectors = embed_texts(batch)
            all_vectors.extend(vectors)

        normalized = self._normalize(all_vectors)
        self.index.add(normalized)
        self.chunks.extend(chunks)

    def search(self, query, top_k=5, filter_type=None, filter_location=None):
        """
        Embed the query, search for top_k most similar chunks.
        Optional metadata filters (type/location) are applied AFTER vector
        search over a wider candidate pool - simple and effective at our
        data scale without needing FAISS's more complex filtered-search APIs.
        """
        query_vector = self._normalize(embed_texts([query]))
        # search wider than top_k so filtering still leaves enough results
        search_k = top_k * 5 if (filter_type or filter_location) else top_k
        search_k = min(search_k, self.index.ntotal) or 1

        scores, indices = self.index.search(query_vector, search_k)

        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx == -1:
                continue
            chunk = self.chunks[idx]
            if filter_type and chunk["type"] != filter_type:
                continue
            if filter_location and chunk["metadata"].get("location") != filter_location:
                continue
            results.append({**chunk, "score": float(score)})
            if len(results) >= top_k:
                break

        return results

    def save(self, path_prefix):
        """Save index + chunk metadata to disk (two files: .faiss and .json)."""
        os.makedirs(os.path.dirname(path_prefix) or ".", exist_ok=True)
        faiss.write_index(self.index, f"{path_prefix}.faiss")
        with open(f"{path_prefix}_chunks.json", "w", encoding="utf-8") as f:
            json.dump(self.chunks, f, ensure_ascii=False)

    @classmethod
    def load(cls, path_prefix, dimension=None):
        store = cls(dimension=dimension)
        store.index = faiss.read_index(f"{path_prefix}.faiss")
        with open(f"{path_prefix}_chunks.json", encoding="utf-8") as f:
            store.chunks = json.load(f)
        return store