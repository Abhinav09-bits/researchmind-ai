import logging
from dataclasses import dataclass

from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    VectorParams,
    PointStruct,
    Filter,
    FieldCondition,
    MatchValue,
    ScoredPoint,
)

from app.core.config import get_settings
from app.services.document_processor import ProcessedChunk

logger = logging.getLogger(__name__)


@dataclass
class RetrievedChunk:
    chunk_id: str
    content: str
    metadata: dict
    score: float


class VectorStoreService:

    def __init__(self):
        settings = get_settings()
        is_cloud = settings.qdrant_host.startswith("http")

        if is_cloud:
            self._client = QdrantClient(
                url=settings.qdrant_host,
                api_key=settings.qdrant_api_key,
                timeout=30,
            )
            logger.info(f"VectorStoreService connected to Qdrant Cloud at {settings.qdrant_host}")
        else:
            self._client = QdrantClient(
                host=settings.qdrant_host,
                port=settings.qdrant_port,
                timeout=30,
            )
            logger.info(f"VectorStoreService connected to local Qdrant at {settings.qdrant_host}:{settings.qdrant_port}")

        self._default_collection = settings.qdrant_collection_name
        self._embedding_dim = settings.embedding_dimensions

    def ensure_collection_exists(self, collection_name: str | None = None) -> None:
        name = collection_name or self._default_collection
        existing = {c.name for c in self._client.get_collections().collections}

        if name not in existing:
            self._client.create_collection(
                collection_name=name,
                vectors_config=VectorParams(
                    size=self._embedding_dim,
                    distance=Distance.COSINE,
                ),
            )
            logger.info(f"Created collection '{name}' ({self._embedding_dim}D cosine)")
        else:
            logger.debug(f"Collection '{name}' already exists")

    def upsert_chunks(
        self,
        chunks: list[ProcessedChunk],
        embeddings: list[list[float]],
        collection_name: str | None = None,
    ) -> int:
        name = collection_name or self._default_collection
        self.ensure_collection_exists(name)

        if len(chunks) != len(embeddings):
            raise ValueError(f"Mismatch: {len(chunks)} chunks but {len(embeddings)} embeddings")

        points = [
            PointStruct(
                id=chunk.chunk_id,
                vector=embedding,
                payload={"content": chunk.content, **chunk.metadata},
            )
            for chunk, embedding in zip(chunks, embeddings)
        ]

        batch_size = 100
        total = 0
        for i in range(0, len(points), batch_size):
            self._client.upsert(collection_name=name, points=points[i: i + batch_size])
            total += len(points[i: i + batch_size])

        logger.info(f"Upserted {total} chunks into '{name}'")
        return total

    def similarity_search(
        self,
        query_vector: list[float],
        top_k: int,
        score_threshold: float,
        collection_name: str | None = None,
        filter_document_id: str | None = None,
        filter_source_file: str | None = None,
    ) -> list[RetrievedChunk]:
        name = collection_name or self._default_collection

        # Build metadata filter — supports document_id OR source_file
        conditions = []
        if filter_document_id:
            conditions.append(
                FieldCondition(key="document_id", match=MatchValue(value=filter_document_id))
            )
        if filter_source_file:
            conditions.append(
                FieldCondition(key="source_file", match=MatchValue(value=filter_source_file))
            )

        query_filter = Filter(must=conditions) if conditions else None

        results: list[ScoredPoint] = self._client.search(
            collection_name=name,
            query_vector=query_vector,
            limit=top_k,
            score_threshold=score_threshold,
            query_filter=query_filter,
            with_payload=True,
        )

        retrieved = [
            RetrievedChunk(
                chunk_id=str(r.id),
                content=r.payload.get("content", ""),
                metadata={k: v for k, v in r.payload.items() if k != "content"},
                score=r.score,
            )
            for r in results
        ]

        logger.info(f"Retrieved {len(retrieved)} chunks from '{name}' (threshold={score_threshold})")
        return retrieved

    def delete_document(self, document_id: str, collection_name: str | None = None) -> None:
        name = collection_name or self._default_collection
        self._client.delete(
            collection_name=name,
            points_selector=Filter(
                must=[FieldCondition(key="document_id", match=MatchValue(value=document_id))]
            ),
        )
        logger.info(f"Deleted chunks for document_id='{document_id}' from '{name}'")

    def get_collection_info(self, collection_name: str | None = None) -> dict:
        name = collection_name or self._default_collection
        info = self._client.get_collection(name)
        return {
            "name": name,
            "total_points": info.points_count,
            "vector_size": info.config.params.vectors.size,
            "distance": info.config.params.vectors.distance.name,
        }

    def load_all_chunks(self, collection_name: str | None = None) -> dict:
        """
        Scroll through all points and return chunk data for BM25 index building.
        Called once at startup to populate the BM25 index.
        """
        name = collection_name or self._default_collection
        chunk_ids, contents, metadatas = [], [], []
        offset = None

        try:
            while True:
                records, next_offset = self._client.scroll(
                    collection_name=name,
                    limit=100,
                    offset=offset,
                    with_payload=True,
                    with_vectors=False,
                )
                for r in records:
                    chunk_ids.append(str(r.id))
                    contents.append(r.payload.get("content", ""))
                    metadatas.append({k: v for k, v in r.payload.items() if k != "content"})

                if next_offset is None:
                    break
                offset = next_offset
        except Exception as e:
            logger.warning(f"Could not load chunks for BM25 (collection may be empty): {e}")

        logger.info(f"Loaded {len(chunk_ids)} chunks from '{name}' for BM25 index")
        return {"chunk_ids": chunk_ids, "contents": contents, "metadatas": metadatas}

    def list_documents(self, collection_name: str | None = None) -> list[dict]:
        """
        Return distinct documents stored in a collection.
        Scrolls through all points and extracts unique document metadata.
        """
        name = collection_name or self._default_collection
        docs = {}
        offset = None

        while True:
            records, next_offset = self._client.scroll(
                collection_name=name,
                limit=100,
                offset=offset,
                with_payload=True,
                with_vectors=False,
            )
            for r in records:
                doc_id = r.payload.get("document_id")
                if doc_id and doc_id not in docs:
                    docs[doc_id] = {
                        "document_id": doc_id,
                        "source_file": r.payload.get("source_file", "Unknown"),
                    }
            if next_offset is None:
                break
            offset = next_offset

        return list(docs.values())
