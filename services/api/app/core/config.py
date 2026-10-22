from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

DOCS_PATH = Path(os.getenv("DOCS_PATH", "docs"))
EMBED_MODEL = os.getenv("EMBED_MODEL", "all-MiniLM-L6-v2")
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "512"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "64"))
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://ditiro:ditiro_local@localhost:5432/ditiro")
QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY") or None
QDRANT_COLLECTION = os.getenv("QDRANT_COLLECTION", "ditiro_logistics")
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2:1b")
EMBED_BATCH_SIZE = int(os.getenv("EMBED_BATCH_SIZE", "8"))
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")

DATABASE_TABLES = {
    "vehicles": "vehicle_id",
    "drivers": "driver_id",
    "trips": "trip_id",
    "telemetry_events": "telemetry_id",
    "security_incidents": "incident_id",
    "fuel_events": "fuel_event_id",
    "port_observations": "observation_id",
}