"""
Generation - takes retrieved chunks + a user question, produces an answer.

Same pluggable pattern as embeddings.py:
    GENERATION_PROVIDER=template   (default - free, no API key, no LLM call at all)
    GENERATION_PROVIDER=openai     (requires OPENAI_API_KEY - real natural-language answers)

The "template" provider doesn't call any LLM - it formats the retrieved
chunks into a readable answer directly. This means your ENTIRE RAG pipeline
(scrape -> clean -> embed -> retrieve -> answer) works end-to-end with ZERO
API costs and ZERO API keys. The moment OpenAI credits are available, switch
one env var and answers become natural-language LLM responses instead.
"""

import os

PROVIDER = os.environ.get("GENERATION_PROVIDER", "template")


def _generate_template(question, retrieved_chunks):
    """No LLM - directly format retrieved chunks into a readable answer."""
    if not retrieved_chunks:
        return "I couldn't find any matching results for that question. Try rephrasing or asking about a specific location."

    lines = [f"Here's what I found for: \"{question}\"\n"]
    for chunk in retrieved_chunks:
        meta = chunk["metadata"]
        if chunk["type"] == "hotel":
            price = meta.get("price_range", "unknown")
            rating = f", rated {meta['rating']}/5" if meta.get("rating") else ""
            lines.append(f"- **{meta['name']}** ({meta['location']}) - {price}{rating}")
        elif chunk["type"] == "attraction":
            lines.append(f"- **{meta['name']}** ({meta['location']}) - {meta.get('attraction_type', 'attraction')}")
        elif chunk["type"] == "destination":
            snippet = chunk["text"][:200].rsplit(" ", 1)[0] + "..."
            lines.append(f"- About {meta['location']}: {snippet}")

    return "\n".join(lines)


def _generate_openai(question, retrieved_chunks):
    from openai import OpenAI
    client = OpenAI()

    context = "\n\n".join(
        f"[{c['type'].upper()}] {c['text']}" for c in retrieved_chunks
    )

    prompt = f"""You are a helpful East Africa travel assistant. Answer the user's
question using ONLY the context below. If the context doesn't fully answer
the question, say what's missing rather than inventing details. Mention
specific hotel/place names from the context where relevant.

Context:
{context}

Question: {question}

Answer:"""

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=500,
    )
    return response.choices[0].message.content


def generate_answer(question, retrieved_chunks):
    if PROVIDER == "openai":
        return _generate_openai(question, retrieved_chunks)
    else:
        return _generate_template(question, retrieved_chunks)


def format_sources(retrieved_chunks):
    """Build the sources list for the API response, per the brief's example format."""
    sources = []
    for chunk in retrieved_chunks:
        meta = chunk["metadata"]
        sources.append({
            "name": meta.get("name") or meta.get("location"),
            "type": chunk["type"],
            "location": meta.get("location"),
            "source_url": meta.get("source_url"),
        })
    return sources