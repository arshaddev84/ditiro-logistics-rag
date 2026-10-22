from __future__ import annotations

import csv
import logging
import os
import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from qdrant_client import QdrantClient, models
from sentence_transformers import SentenceTransformer

load_dotenv()

logger = logging.getLogger("ditiro_logistics.pipeline")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")


@dataclass(frozen=True)
class Document:
    page_content: str
    metadata: dict[str, Any]


@dataclass(frozen=True)
class PipelineConfig:
    docs_path: str = os.getenv("DOCS_PATH", "docs")
    collection_name: str = os.getenv("QDRANT_COLLECTION", "ditiro_logistics")
    model_name: str = os.getenv("EMBED_MODEL", "all-MiniLM-L6-v2")
    qdrant_url: str = os.getenv("QDRANT_URL", "http://localhost:6333")
    qdrant_api_key: str | None = os.getenv("QDRANT_API_KEY") or None
    chunk_size: int = int(os.getenv("CHUNK_SIZE", "512"))
    chunk_overlap: int = int(os.getenv("CHUNK_OVERLAP", "0"))
    max_workers: int = int(os.getenv("MAX_WORKERS", "2"))
    batch_size: int = int(os.getenv("EMBED_BATCH_SIZE", "8"))


class DocumentIngestionEngine:
    def __init__(self, config: PipelineConfig | None = None) -> None:
        self.config = config or PipelineConfig()
        logger.info("Loading local embedding model: %s", self.config.model_name)
        self.model = SentenceTransformer(self.config.model_name, local_files_only=True)
        self.vector_dimension = int(self.model.get_embedding_dimension() or 384)
        self.client = QdrantClient(
            url=self.config.qdrant_url,
            api_key=self.config.qdrant_api_key,
        )

    def load_file(self, path: Path) -> list[Document]:
        source = path.relative_to(Path(self.config.docs_path)).as_posix()
        if path.suffix.lower() == ".csv":
            with path.open("r", encoding="utf-8", newline="") as csv_file:
                rows = csv.DictReader(csv_file)
                return [
                    Document(
                        page_content="\n".join(f"{key}: {value}" for key, value in row.items() if value),
                        metadata={"source": source, "row": row_number},
                    )
                    for row_number, row in enumerate(rows, start=1)
                ]
        return [
            Document(
                page_content=path.read_text(encoding="utf-8", errors="replace"),
                metadata={"source": source},
            )
        ]

    def extract_all_documents(self) -> list[Document]:
        docs_root = Path(self.config.docs_path)
        if not docs_root.is_dir():
            raise FileNotFoundError(f"Documents directory not found: {docs_root}")
        paths = sorted(
            path for path in docs_root.rglob("*")
            if path.is_file() and path.suffix.lower() in {".txt", ".csv"}
        )
        if not paths:
            raise ValueError(f"No supported documents found under {docs_root}")
        with ThreadPoolExecutor(max_workers=max(1, self.config.max_workers)) as executor:
            documents = [doc for group in executor.map(self.load_file, paths) for doc in group]
        logger.info("Loaded %d document passages from %d files", len(documents), len(paths))
        return documents

    def partition_documents(self, documents: list[Document]) -> list[Document]:
        chunks: list[Document] = []
        for document in documents:
            text = document.page_content
            start = 0
            while start < len(text):
                end = min(start + self.config.chunk_size, len(text))
                if end < len(text):
                    boundary = max(text.rfind("\n", start, end), text.rfind(" ", start, end))
                    if boundary > start + self.config.chunk_size // 2:
                        end = boundary
                content = text[start:end].strip()
                if content:
                    chunks.append(Document(content, document.metadata))
                if end == len(text):
                    break
                start = max(end - self.config.chunk_overlap, start + 1)
        return chunks

    def _ensure_collection(self) -> None:
        if not self.client.collection_exists(collection_name=self.config.collection_name):
            self.client.create_collection(
                collection_name=self.config.collection_name,
                vectors_config=models.VectorParams(
                    size=self.vector_dimension,
                    distance=models.Distance.COSINE,
                ),
            )

    def embed_and_populate_store(self, chunks: list[Document]) -> None:
        if not chunks:
            logger.warning("No document chunks to index")
            return
        self._ensure_collection()
        vectors = self.model.encode(
            [chunk.page_content for chunk in chunks],
            batch_size=max(1, self.config.batch_size),
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        points = [
            models.PointStruct(
                id=str(uuid.uuid5(uuid.NAMESPACE_URL, f"{chunk.metadata}:{chunk.page_content}")),
                vector=vectors[index].tolist(),
                payload={"text": chunk.page_content, **chunk.metadata},
            )
            for index, chunk in enumerate(chunks)
        ]
        self.client.upsert(
            collection_name=self.config.collection_name,
            points=points,
            wait=True,
        )
        logger.info("Indexed %d document chunks", len(points))


def main() -> None:
    engine = DocumentIngestionEngine()
    documents = engine.extract_all_documents()
    chunks = engine.partition_documents(documents)
    engine.embed_and_populate_store(chunks)
    logger.info("Document ingestion completed")


if __name__ == "__main__":
    main()
