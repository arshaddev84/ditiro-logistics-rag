# Architecture

This describes the local, document-and-database retrieval proof of concept. It is not a production deployment and does not provide tenant isolation.

## Runtime

```text
Browser: Next.js / React / TypeScript / Tailwind
                  | HTTP + CORS
                  v
FastAPI: services/api/app/main.py
  |-- PostgreSQL: source document text and metadata; logistics source tables
  |-- Qdrant: embedded document chunks and selected PostgreSQL records
  |-- SentenceTransformers: local query/document embeddings
  `-- Ollama: local answer generation
```

The active application requires PostgreSQL, Qdrant, Ollama, a local embedding model, and installed application packages.

## Indexing

`POST /ingest` indexes `.txt`, `.csv`, and `.json` files below `DOCS_PATH`. Original content and metadata are upserted into `knowledge_documents`; chunks are embedded with `EMBED_MODEL` and stored as Qdrant points.

The same request re-indexes rows from this fixed PostgreSQL allowlist: `vehicles`, `drivers`, `trips`, `telemetry_events`, `security_incidents`, `fuel_events`, and `port_observations`. SQL identifiers come only from this allowlist. Row values are serialized as JSON and stored as Qdrant payload text. Re-indexing replaces the previous points marked as database records; it does not modify the source tables.

`DELETE /documents` deletes the configured Qdrant collection and rows from `knowledge_documents`. It does not remove source files or rows from operational PostgreSQL tables.

## Retrieval and Answers

`POST /ask` embeds the question with the same local SentenceTransformer model and requests the configured top-k points from Qdrant. Each source includes its path/table reference, passage or record text, and a percentage formed by multiplying Qdrant's cosine similarity by 100:

`score_percent = cosine_similarity * 100`

This preserves the application's cosine-similarity percentage display. It is a retrieval ranking signal, not an answer-accuracy probability. Accuracy requires labeled questions and expected evidence for evaluation.

The retrieved evidence is passed to Ollama with instructions to use only those sources, cite source labels, and abstain when evidence is insufficient. Retrieved text is treated as data, not instructions. This reduces unsupported answers but cannot guarantee a model never hallucinates; verify consequential decisions against cited sources.

## Models and Offline Use

| Setting | Default | Role |
|---|---|---|
| `EMBED_MODEL` | `all-MiniLM-L6-v2` | Local query and source embeddings; loaded with `local_files_only=True` |
| `OLLAMA_MODEL` | `llama3.2:1b` | Local grounded answer generation |
| `CHUNK_SIZE` | `512` | Maximum source chunk characters |
| `CHUNK_OVERLAP` | `64` | Overlap between source chunks |
| `EMBED_BATCH_SIZE` | `8` | Embedding batch size to limit peak memory |

For offline operation, install application dependencies and download both model artifacts before disconnecting from the internet. `OLLAMA_MODEL` must already be available in the local Ollama model store, and `EMBED_MODEL` must point to a local SentenceTransformers model directory.

## API

| Method | Path | Behavior |
|---|---|---|
| `GET` | `/health` | PostgreSQL, Qdrant, Ollama, and configured model status |
| `GET` | `/documents` | Document count, up to eight document summaries, and indexed PostgreSQL record count |
| `POST` | `/ingest` | Re-index supported local files and allowlisted PostgreSQL records |
| `DELETE` | `/documents` | Delete indexed vectors and document metadata only |
| `POST` | `/ask` | Retrieve top-k sources and generate a cited, evidence-limited response |

FastAPI documentation is available at `/docs` while the API is running.

## Limits

- Indexing and embedding run synchronously in the API request.
- PostgreSQL and Qdrant do not share a transaction; a failed indexing run may leave a partial index. Re-run indexing to recover.
- No authentication, tenant boundaries, or production authorization are implemented. Use synthetic/developer data only.
