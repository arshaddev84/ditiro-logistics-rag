from __future__ import annotations

from typing import Any

import psycopg
from psycopg.types.json import Jsonb

from services.api.app.core.config import DATABASE_URL


def ensure_documents_table(connection: psycopg.Connection[Any]) -> None:
    """Create the document metadata table when it does not exist."""
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS knowledge_documents (
            document_id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            document_type TEXT NOT NULL,
            version TEXT NOT NULL,
            effective_from DATE,
            effective_to DATE,
            source_uri TEXT,
            content_text TEXT NOT NULL,
            metadata JSONB NOT NULL DEFAULT '{}'::JSONB,
            content_sha256 TEXT NOT NULL,
            active BOOLEAN NOT NULL DEFAULT TRUE,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
        """
    )


def upsert_document(
    document_id: str,
    title: str,
    document_type: str,
    version: str,
    source_uri: str,
    content: str,
    content_hash: str,
) -> None:
    """Insert or update a document's searchable source metadata."""
    with psycopg.connect(DATABASE_URL) as connection:
        ensure_documents_table(connection)
        connection.execute(
            """
            INSERT INTO knowledge_documents (
                document_id, title, document_type, version, source_uri,
                content_text, metadata, content_sha256, active
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, TRUE)
            ON CONFLICT (document_id) DO UPDATE SET
                title = EXCLUDED.title,
                document_type = EXCLUDED.document_type,
                version = EXCLUDED.version,
                source_uri = EXCLUDED.source_uri,
                content_text = EXCLUDED.content_text,
                metadata = EXCLUDED.metadata,
                content_sha256 = EXCLUDED.content_sha256,
                active = TRUE
            """,
            (
                document_id,
                title,
                document_type,
                version,
                source_uri,
                content,
                Jsonb({"synthetic": True}),
                content_hash,
            ),
        )


def list_active_documents() -> tuple[int, list[tuple[Any, ...]]]:
    """Return the active document count and a bounded source preview."""
    with psycopg.connect(DATABASE_URL) as connection:
        ensure_documents_table(connection)
        count_row = connection.execute(
            "SELECT COUNT(*) FROM knowledge_documents WHERE active = TRUE"
        ).fetchone()
        rows = connection.execute(
            """
            SELECT document_id, title, document_type, source_uri, content_sha256, created_at
            FROM knowledge_documents
            WHERE active = TRUE
            ORDER BY title
            LIMIT 8
            """
        ).fetchall()
    return (count_row[0] if count_row else 0), rows


def delete_all_documents() -> None:
    """Delete indexed document metadata without touching source files."""
    with psycopg.connect(DATABASE_URL) as connection:
        ensure_documents_table(connection)
        connection.execute("DELETE FROM knowledge_documents")