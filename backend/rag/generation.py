"""
Generation - takes retrieved chunks + a user question, produces an answer.

Same pluggable pattern as embeddings.py:
    GENERATION_PROVIDER=template   (default - free, no API key, no LLM call at all)
    GENERATION_PROVIDER=groq       (free tier available, needs GROQ_API_KEY - fast Llama/GPT-OSS models)
    GENERATION_PROVIDER=openai     (requires OPENAI_API_KEY - if credits get sponsored)

The "template" provider doesn't call any LLM - it formats the retrieved
chunks into a readable answer directly. This means your ENTIRE RAG pipeline
(scrape -> clean -> embed -> retrieve -> answer) works end-to-end with ZERO
API costs and ZERO API keys. Groq is the easiest real-LLM upgrade in the
meantime - genuinely free tier, no credit card required, just an API key
from console.groq.com.
"""

import os

PROVIDER = os.environ.get("GENERATION_PROVIDER", "template")
# openai/gpt-oss-20b is Groq's current recommended fast/free-tier model as of
# mid-2026 (their older llama-3.3-70b-versatile and llama-3.1-8b-instant
# model IDs were deprecated in June 2026). Override via GROQ_MODEL if needed.
GROQ_MODEL = os.environ.get("GROQ_MODEL", "openai/gpt-oss-20b")


def _generate_template(question, retrieved_chunks):
    """No LLM - directly format retrieved chunks into a readable answer.
    No markdown syntax here (no **bold**) since the frontend renders this
    as plain text, not HTML - literal asterisks would just show up as-is."""
    if not retrieved_chunks:
        return "I couldn't find any matches for that. Try rephrasing, or ask about a specific location like Nairobi, Diani, or Maasai Mara."

    hotel_lines, attraction_lines, destination_lines = [], [], []
    for chunk in retrieved_chunks:
        meta = chunk["metadata"]
        if chunk["type"] == "hotel":
            price = meta.get("price_range", "unknown")
            price_str = "price not listed" if price == "unknown" else price
            rating = f" · {meta['rating']}/5" if meta.get("rating") else ""
            hotel_lines.append(f"{meta['name']} in {meta['location']} ({price_str}{rating})")
        elif chunk["type"] == "attraction":
            attraction_lines.append(f"{meta['name']} in {meta['location']}")
        elif chunk["type"] == "destination":
            destination_lines.append(meta["location"])

    parts = []
    if hotel_lines:
        parts.append("A few hotels worth considering: " + "; ".join(hotel_lines) + ".")
    if attraction_lines:
        parts.append("Nearby attractions include " + ", ".join(attraction_lines) + ".")
    if destination_lines:
        parts.append(f"See the {destination_lines[0]} card below for more on what the area is like.")

    return " ".join(parts) if parts else "I found some results, but couldn't summarize them - check the cards below."


def _build_prompt(question, retrieved_chunks):
    context = "\n\n".join(
        f"[{c['type'].upper()}] {c['text']}" for c in retrieved_chunks
    )
    return f"""You are a helpful East Africa travel assistant. Answer the user's
question using ONLY the context below. If the context doesn't fully answer
the question, say what's missing rather than inventing details. Mention
specific hotel/place names from the context where relevant.

Context:
{context}

Question: {question}

Answer:"""


def _generate_groq(question, retrieved_chunks):
    from openai import OpenAI
    client = OpenAI(
        base_url="https://api.groq.com/openai/v1",
        api_key=os.environ.get("GROQ_API_KEY"),
    )
    response = client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[{"role": "user", "content": _build_prompt(question, retrieved_chunks)}],
        max_tokens=500,
    )
    return response.choices[0].message.content


def _generate_openai(question, retrieved_chunks):
    from openai import OpenAI
    client = OpenAI()
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": _build_prompt(question, retrieved_chunks)}],
        max_tokens=500,
    )
    return response.choices[0].message.content


def generate_answer(question, retrieved_chunks):
    if PROVIDER == "groq":
        return _generate_groq(question, retrieved_chunks)
    elif PROVIDER == "openai":
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
            "price_range": meta.get("price_range"),
            "rating": meta.get("rating"),
        })
    return sources