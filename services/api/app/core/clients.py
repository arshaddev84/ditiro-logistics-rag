from __future__ import annotations

from functools import lru_cache
from typing import TYPE_CHECKING

from qdrant_client import QdrantClient

from services.api.app.core import config

if TYPE_CHECKING:
    from sentence_transformers import SentenceTransformer


@lru_cache(maxsize=1)
def get_embedder() -> SentenceTransformer:
    """Return the cached local sentence embedding model."""
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(config.EMBED_MODEL, local_files_only=True)


@lru_cache(maxsize=1)
def get_qdrant() -> QdrantClient:
    """Return the cached Qdrant client."""
    return QdrantClient(url=config.QDRANT_URL, api_key=config.QDRANT_API_KEY)