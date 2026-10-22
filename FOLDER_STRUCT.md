# Folder Structure

This tree shows the current application surface; it omits data files, generated files, and caches.

```text
ditiro/
├── apps/
│   └── web/
│       ├── Dockerfile                 # standalone Next.js production image
│       ├── src/
│       │   ├── app/
│       │   │   ├── globals.css       # chat and Settings modal styling
│       │   │   ├── layout.tsx        # root layout and metadata
│       │   │   └── page.tsx          # retrieval chat and Settings modal
│       │   └── lib/
│       │       └── api.ts            # typed FastAPI client
│       └── package.json
├── docs/                              # local RAG source material
├── infra/
│   ├── compose/
│   │   └── compose.yaml               # full local application stack
│   └── postgres/
│       └── schema.sql                 # operational and document schema
├── ingestion_engine.py                # standalone local document indexer
├── services/
│   └── api/
│       ├── Dockerfile                 # FastAPI image with local embedder
│       ├── app/
│       │   ├── api/
│       │   │   ├── routes.py          # HTTP endpoints and error translation
│       │   │   └── schemas.py         # request validation models
│       │   ├── core/
│       │   │   ├── clients.py         # cached model and Qdrant clients
│       │   │   └── config.py          # environment-backed settings
│       │   ├── rag/
│       │   │   ├── answering.py      # evidence-grounded answer generation
│       │   │   ├── chunking.py       # document text splitting
│       │   │   ├── errors.py         # RAG service errors
│       │   │   ├── indexing.py       # document and database indexing
│       │   │   └── retrieval.py      # Qdrant evidence retrieval
│       │   ├── repositories/
│       │   │   └── documents.py      # knowledge-document persistence
│       │   ├── main.py                # FastAPI app and router composition
│       │   └── main_updated.py        # existing separate API copy
│       └── tests/
│           └── test_main.py           # unit tests for API and RAG boundaries
├── tests/
│   └── evaluations/
│       ├── README.md                  # evaluation scope and limitations
│       └── rag_cases.json             # synthetic labeled RAG cases
├── .env.example                       # safe local config template
├── .dockerignore                      # Docker build-context exclusions
├── .gitignore                         # local secrets and generated files
├── ARCHITECTURE.md
├── DESIGN.md
├── FEATURES.md
├── FOLDER_STRUCT.md
├── README.md
└── requirements.txt
```

The API indexes local documents and an explicit PostgreSQL table allowlist. Run it through `services.api.app.main`. Agent orchestration is not part of this proof of concept; add agent modules only when a validated workflow needs them.
