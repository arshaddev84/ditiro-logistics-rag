from __future__ import annotations

from typing import Any

from services.api.app.core import config
from services.api.app.core.clients import get_embedder, get_qdrant


def retrieve_sources(question: str, limit: int) -> list[dict[str, Any]] | None:
    """Return cited Qdrant evidence, or None when no collection exists."""
    query_vector = get_embedder().encode(
        question,
        normalize_embeddings=True,
        show_progress_bar=False,
    ).tolist()
    client = get_qdrant()
    if not client.collection_exists(config.QDRANT_COLLECTION):
        return None
    results = client.query_points(
        collection_name=config.QDRANT_COLLECTION,
        query=query_vector,
        limit=limit,
        with_payload=True,
    ).points
    return [
        {
            "ref": f"S{index}",
            "title": point.payload["title"],
            "source_uri": point.payload["source_uri"],
            "source_type": point.payload.get("source_type", "document"),
            "chunk_index": point.payload["chunk_index"],
            "text": point.payload["text"],
            "score": float(point.score),
        }
        for index, point in enumerate(results, start=1)
        if point.payload and point.payload.get("text")
    ]