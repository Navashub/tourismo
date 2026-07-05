"""
Travel Africa RAG Assistant - FastAPI backend.

Run from project root:
    uvicorn backend.main:app --reload --port 8000
"""

# Load .env BEFORE importing anything that reads os.environ at import time
# (embeddings.py and generation.py both read provider/API-key env vars as
# soon as they're imported, so this has to come first).
from dotenv import load_dotenv
load_dotenv()

import json
import os
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional

from backend.rag.retrieval import retrieve, retrieve_diverse
from backend.rag.generation import generate_answer, format_sources

# Known locations from our data collection - used for simple keyword-based
# query understanding. Not fancy NLP, just a direct substring check, but it
# fixes real cases where pure semantic search matches the wrong place (e.g.
# a hotel literally named "Naivasha House" that's actually in Nairobi).
KNOWN_LOCATIONS = [
    "Nairobi", "Mombasa", "Diani", "Naivasha", "Nakuru", "Maasai Mara",
    "Amboseli", "Watamu", "Malindi", "Kisumu", "Nanyuki", "Lamu",
    "Zanzibar", "Arusha", "Kampala", "Dar es Salaam",
]


def detect_location(question):
    """Return the first known location name mentioned in the question, if any."""
    question_lower = question.lower()
    for location in KNOWN_LOCATIONS:
        if location.lower() in question_lower:
            return location
    return None

app = FastAPI(title="Travel Africa RAG Assistant")

import os as _os

# Serve the provided frontend template's static assets, if present
if _os.path.isdir("static"):
    app.mount("/static", StaticFiles(directory="static"), name="static")

FINAL_HOTELS_PATH = "data/processed/final_hotels.json"


# ---------- Request/response schemas ----------

class AskRequest(BaseModel):
    question: str


class PlanTripRequest(BaseModel):
    preferences: str
    days: Optional[int] = 5


# ---------- Health check ----------

@app.get("/")
def root():
    if _os.path.exists("templates/index.html"):
        return FileResponse("templates/index.html")
    return {"message": "Travel Africa RAG Assistant API is running. Frontend template not found yet - add templates/index.html and static/."}


@app.get("/health")
def health():
    return {"status": "ok"}


# ---------- Core RAG endpoint ----------

@app.post("/ask")
def ask(request: AskRequest):
    if not request.question or not request.question.strip():
        raise HTTPException(status_code=400, detail="question must not be empty")

    location = detect_location(request.question)
    chunks = retrieve_diverse(request.question, filter_location=location, per_type=3)

    # If a location was mentioned but the filtered search found nothing,
    # fall back to unfiltered diverse search rather than returning empty results.
    if location and not chunks:
        chunks = retrieve_diverse(request.question, per_type=3)

    answer = generate_answer(request.question, chunks)
    sources = format_sources(chunks)

    return {"answer": answer, "sources": sources}


# ---------- Trip planning ----------

@app.post("/plan-trip")
def plan_trip(request: PlanTripRequest):
    question = f"Plan a {request.days}-day trip: {request.preferences}"
    # Pull a wider mix of chunk types for itinerary-style questions
    chunks = retrieve(question, top_k=10)
    answer = generate_answer(question, chunks)
    sources = format_sources(chunks)

    return {"answer": answer, "sources": sources, "days_requested": request.days}


# ---------- Hotel listing endpoints ----------

def _load_hotels():
    if not os.path.exists(FINAL_HOTELS_PATH):
        raise HTTPException(status_code=500, detail="Hotel dataset not found - run the data pipeline first.")
    with open(FINAL_HOTELS_PATH, encoding="utf-8") as f:
        return json.load(f)


@app.get("/hotels")
def get_all_hotels():
    return _load_hotels()


@app.get("/hotels/{location}")
def get_hotels_by_location(location: str):
    hotels = _load_hotels()
    matches = [h for h in hotels if h["location"].lower() == location.lower()]
    if not matches:
        raise HTTPException(status_code=404, detail=f"No hotels found for location '{location}'")
    return matches


# ---------- Data pipeline endpoints (kick off the scripts you already built) ----------

@app.post("/upload-data")
def upload_data():
    """
    Note: your actual data collection happens via the scripts/ pipeline
    (scrape_osm_hotels.py, clean_data.py, etc.) run offline, not live through
    this endpoint - that's a deliberate choice given free API rate limits
    observed during development. This endpoint is a placeholder documenting
    that design decision; wire it to trigger the pipeline if time allows.
    """
    return {"message": "Data pipeline is run via scripts/ - see README for the collection workflow."}