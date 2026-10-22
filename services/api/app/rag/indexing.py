from __future__ import annotations

import hashlib
import json
import uuid
from pathlib import Path
from typing import Any

import psycopg
from psycopg import sql
from qdrant_client import QdrantClient, models

from services.api.app.core import config
from services.api.app.core.clients import get_embedder, get_qdrant
from services.api.app.rag.chunking import split_text
from services.api.app.rag.errors import NoSourcesFound
from services.api.app.repositories.documents import upsert_document


def ensure_collection(client: QdrantClient) -> None:
    """Create the configured Qdrant collection if it is missing."""
    if not client.collection_exists(config.QDRANT_COLLECTION):
        vector_size = get_embedder().get_embedding_dimension()
        if vector_size is None:
            raise RuntimeError("The embedding model did not report its vector dimension")
        client.create_collection(
            collection_name=config.QDRANT_COLLECTION,
            vectors_config=models.VectorParams(
                size=vector_size,
                distance=models.Distance.COSINE,
            ),
        )


def embed_and_upsert(
    client: QdrantClient,
    entries: list[tuple[str, str, dict[str, Any]]],
) -> int:
    """Embed and upsert entries, returning the number of points written."""
    if not entries:
        return 0
    vectors = get_embedder().encode(
        [text for _, text, _ in entries],
        batch_size=max(1, config.EMBED_BATCH_SIZE),
        normalize_embeddings=True,
        show_progress_bar=False,
    ).tolist()
    client.upsert(
        collection_name=config.QDRANT_COLLECTION,
        points=[
            models.PointStruct(
                id=str(uuid.uuid5(uuid.NAMESPACE_URL, point_key)),
                vector=vector,
                payload={"text": text, **payload},
            )
            for (point_key, text, payload), vector in zip(entries, vectors)
        ],
        wait=True,
    )
    return len(entries)


def index_document(path: Path, client: QdrantClient) -> int:
    """Persist a source document and replace its Qdrant chunks."""
    content = path.read_text(encoding="utf-8", errors="replace")
    chunks = split_text(content)
    if not chunks:
        return 0
    source_uri = path.resolve().relative_to(config.DOCS_PATH.resolve()).as_posix()
    document_id = str(uuid.uuid5(uuid.NAMESPACE_URL, source_uri))
    content_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
    upsert_document(
        document_id=document_id,
        title=path.stem,
        document_type=path.suffix.lstrip(".").lower(),
        version=content_hash[:12],
        source_uri=source_uri,
        content=content,
        content_hash=content_hash,
    )
    client.delete(
        collection_name=config.QDRANT_COLLECTION,
        points_selector=models.FilterSelector(
            filter=models.Filter(
                must=[models.FieldCondition(key="document_id", match=models.MatchValue(value=document_id))]
            )
        ),
        wait=True,
    )
    return embed_and_upsert(
        client,
        [
            (
                f"document:{document_id}:{index}",
                chunk,
                {
                    "document_id": document_id,
                    "source_type": "document",
                    "title": path.stem,
                    "source_uri": source_uri,
                    "chunk_index": index,
                },
            )
            for index, chunk in enumerate(chunks)
        ],
    )


def index_postgres_records(client: QdrantClient) -> int:
    """Re-index read-only records from the configured table allowlist."""
    deleted = models.FilterSelector(
        filter=models.Filter(
            must=[models.FieldCondition(key="source_type", match=models.MatchValue(value="database"))]
        )
    )
    client.delete(collection_name=config.QDRANT_COLLECTION, points_selector=deleted, wait=True)
    indexed = 0
    with psycopg.connect(config.DATABASE_URL) as connection:
        for table_name, primary_key in config.DATABASE_TABLES.items():
            query = sql.SQL("SELECT to_jsonb(record) FROM (SELECT * FROM {} ORDER BY {}) AS record").format(
                sql.Identifier("public", table_name),
                sql.Identifier(primary_key),
            )
            with connection.cursor(name=f"rag_{table_name}") as cursor:
                cursor.execute(query)
                while rows := cursor.fetchmany(max(1, config.EMBED_BATCH_SIZE)):
                    entries = []
                    for (record,) in rows:
                        record_text = json.dumps(record, sort_keys=True, default=str)
                        record_id = record.get(primary_key, "unknown")
                        entries.append(
                            (
                                f"database:{table_name}:{record_id}",
                                record_text,
                                {
                                    "source_type": "database",
                                    "title": f"{table_name}: {record_id}",
                                    "source_uri": f"postgres:{table_name}/{record_id}",
                                    "table_name": table_name,
                                    "record_id": str(record_id),
                                    "chunk_index": 0,
                                },
                            )
                        )
                    indexed += embed_and_upsert(client, entries)
    return indexed


def ingest_sources() -> dict[str, int]:
    """Index supported local documents and allowlisted database records."""
    paths = sorted(
        path
        for path in config.DOCS_PATH.rglob("*")
        if path.is_file() and path.suffix.lower() in {".txt", ".csv", ".json"}
    )
    client = get_qdrant()
    ensure_collection(client)
    document_chunks = sum(index_document(path, client) for path in paths)
    database_records = index_postgres_records(client)
    if not paths and database_records == 0:
        raise NoSourcesFound("No supported documents or PostgreSQL records found")
    return {
        "documents": len(paths),
        "chunks": document_chunks,
        "database_records": database_records,
    }