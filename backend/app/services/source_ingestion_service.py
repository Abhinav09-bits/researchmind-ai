import uuid
import logging

from app.services.document_processor import ProcessedChunk
from app.services.embedding_service import EmbeddingService
from app.services.vector_store import VectorStoreService
from app.services.bm25_service import BM25Index
from app.core.config import get_settings

logger = logging.getLogger(__name__)


class SourceIngestionService:
    """
    Shared ingestion pipeline used by all loaders (web, GitHub, YouTube, PDF).
    Takes a list of ProcessedChunks → embeds → stores in Qdrant + BM25.
    """

    def __init__(
        self,
        embedding_service: EmbeddingService,
        vector_store: VectorStoreService,
        bm25_index: BM25Index,
    ):
        self._embedding = embedding_service
        self._vector_store = vector_store
        self._bm25 = bm25_index
        self._settings = get_settings()

    async def ingest(self, chunks: list[ProcessedChunk], source_label: str) -> dict:
        """
        Embed and store chunks. Returns ingestion summary dict.
        source_label: human-readable name for logging (URL, repo name, etc.)
        """
        if not chunks:
            raise ValueError("No chunks to ingest")

        collection = self._settings.qdrant_collection_name
        texts = [c.content for c in chunks]

        logger.info(f"Embedding {len(chunks)} chunks from '{source_label}'")
        embeddings = await self._embedding.embed_documents(texts)

        self._vector_store.ensure_collection_exists(collection)
        total_stored = self._vector_store.upsert_chunks(chunks, embeddings, collection)

        self._bm25.add_chunks(
            chunk_ids=[c.chunk_id for c in chunks],
            contents=[c.content for c in chunks],
            metadatas=[c.metadata for c in chunks],
        )

        logger.info(f"Ingested '{source_label}': {total_stored} chunks stored")
        return {
            "document_id": chunks[0].metadata["document_id"],
            "source_label": source_label,
            "total_chunks": total_stored,
            "collection_name": collection,
        }
