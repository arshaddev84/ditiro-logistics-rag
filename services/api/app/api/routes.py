from __future__ import annotations

import logging
from typing import Any

import ollama
import psycopg
from fastapi import APIRouter, HTTPException
from qdrant_client import models

from services.api.app.api.schemas import AskRequest
from services.api.app.core import config
from services.api.app.core.clients import get_qdrant
from services.api.app.rag.answering import answer_question
from services.api.app.rag.errors import (
    AnswerGenerationUnavailable,
    NoSourcesFound,
    RetrievalUnavailable,
)
from services.api.app.rag.indexing import ingest_sources
from services.api.app.repositories.documents import delete_all_documents, list_active_documents

router = APIRouter()
logger = logging.getLogger("ditiro.api")


@router.get("/health")
def health() -> dict[str, Any]:
    """Report the availability of configured backend dependencies."""
    checks: dict[str, str] = {}
    try:
        with psycopg.connect(config.DATABASE_URL) as connection:
            connection.execute("SELECT 1")
        checks["postgres"] = "ok"
    except Exception:
        logger.exception("PostgreSQL health check failed")
        checks["postgres"] = "unavailable"
    try:
        get_qdrant().get_collections()
        checks["qdrant"] = "ok"
    except Exception:
        logger.exception("Qdrant health check failed")
        checks["qdrant"] = "unavailable"
    try:
        ollama.Client(host=config.OLLAMA_URL).list()
        checks["ollama"] = "ok"
    except Exception:
        logger.exception("Ollama health check failed")
        checks["ollama"] = "unavailable"
    return {
        "status": "ok" if all(value == "ok" for value in checks.values()) else "degraded",
        "services": checks,
        "model": config.OLLAMA_MODEL,
        "embedding_model": config.EMBED_MODEL,
        "collection": config.QDRANT_COLLECTION,
    }


@router.get("/documents")
def documents() -> dict[str, Any]:
    """Return indexed document metadata and the indexed record count."""
    try:
        total, rows = list_active_documents()
        database_records = 0
        client = get_qdrant()
        if client.collection_exists(config.QDRANT_COLLECTION):
            database_records = client.count(
                collection_name=config.QDRANT_COLLECTION,
                count_filter=models.Filter(
                    must=[models.FieldCondition(key="source_type", match=models.MatchValue(value="database"))]
                ),
                exact=True,
            ).count
    except Exception as error:
        logger.exception("Indexed data listing failed")
        raise HTTPException(status_code=503, detail="Could not load indexed data status") from error
    return {
        "total": total,
        "database_records": database_records,
        "documents": [
            {
                "document_id": row[0],
                "title": row[1],
                "document_type": row[2],
                "source_uri": row[3],
                "content_sha256": row[4],
                "indexed_at": row[5].isoformat(),
            }
            for row in rows
        ],
    }


@router.delete("/documents")
def forget_index() -> dict[str, int]:
    """Remove indexed copies while retaining source files and source records."""
    try:
        client = get_qdrant()
        forgotten = 0
        if client.collection_exists(config.QDRANT_COLLECTION):
            forgotten = client.count(collection_name=config.QDRANT_COLLECTION, exact=True).count
            client.delete_collection(config.QDRANT_COLLECTION)
        delete_all_documents()
    except Exception as error:
        logger.exception("Forgetting indexed data failed")
        raise HTTPException(
            status_code=503,
            detail="Could not forget indexed documents and database records",
        ) from error
    return {"items_forgotten": forgotten}


@router.post("/ingest")
def ingest() -> dict[str, int]:
    """Index supported documents and allowlisted PostgreSQL records."""
    try:
        return ingest_sources()
    except NoSourcesFound as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except Exception as error:
        logger.exception("Document and PostgreSQL indexing failed")
        raise HTTPException(status_code=503, detail="Indexing failed; check API logs") from error


@router.post("/ask")
def ask(request: AskRequest) -> dict[str, Any]:
    """Delegate a validated question to the evidence-grounded answer service."""
    try:
        return answer_question(request.question, request.limit)
    except RetrievalUnavailable as error:
        logger.exception("Evidence retrieval failed")
        raise HTTPException(status_code=503, detail="Retrieval unavailable; check API logs") from error
    except AnswerGenerationUnavailable as error:
        logger.exception("Answer generation failed")
        raise HTTPException(status_code=503, detail="Answer generation unavailable; check API logs") from error