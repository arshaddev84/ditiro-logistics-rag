# Features

This file describes the active local proof of concept.

## Chat

- Search indexed document chunks and allowlisted PostgreSQL logistics records with vector retrieval.
- Generate answers locally with Ollama using only retrieved evidence, with source labels and an explicit insufficient-evidence instruction.
- Show each top-k source, its path or PostgreSQL table/record reference, text, and normalized cosine-similarity percentage.
- Display an explicit no-evidence state when no points are returned.

The percentage is a retrieval ranking signal, not a model-accuracy score or probability that a response is correct. Accuracy measurement needs a labeled evaluation set.

## Settings

- View PostgreSQL, Qdrant, and Ollama health.
- View the indexed document count, a limited source preview, and count of indexed PostgreSQL records.
- Re-index supported files from `DOCS_PATH` and records from the fixed database table allowlist.
- Forget the Qdrant collection and indexed document metadata without deleting source files or operational PostgreSQL records.

Settings opens as a modal from the bottom of the chat page.

## Local Models and Dependencies

The active application uses `all-MiniLM-L6-v2` for embeddings and `llama3.2:1b` through Ollama for generation. Models must be available locally for offline use. Embedding loads with local-only mode. There is no second scoring/classification model or autonomous task workflow in the active app.

## Limits

- No file upload; document ingestion reads the configured local folder.
- Database indexing is read-only and limited to the tables listed in `services/api/app/main.py`.
- No generated SQL, operational writes, notifications, external network integration, authentication, or tenant isolation.
- Similarity is not accuracy; evaluate with representative questions and expected evidence before making accuracy claims.
