from functools import lru_cache

from app.services.embedding_service import EmbeddingService
from app.services.vector_store import VectorStoreService
from app.services.query_preprocessor import QueryPreprocessor
from app.services.bm25_service import BM25Index
from app.services.hybrid_search_service import HybridSearchService
from app.services.reranker_service import RerankerService
from app.services.confidence_service import ConfidenceService
from app.services.faithfulness_service import FaithfulnessService
from app.services.analytics_service import AnalyticsService
from app.services.rag_service import RAGService


@lru_cache
def get_embedding_service() -> EmbeddingService:
    return EmbeddingService()


@lru_cache
def get_vector_store() -> VectorStoreService:
    return VectorStoreService()


@lru_cache
def get_query_preprocessor() -> QueryPreprocessor:
    return QueryPreprocessor()


@lru_cache
def get_bm25_index() -> BM25Index:
    return BM25Index()


@lru_cache
def get_hybrid_search() -> HybridSearchService:
    return HybridSearchService(
        vector_store=get_vector_store(),
        bm25_index=get_bm25_index(),
    )


@lru_cache
def get_reranker() -> RerankerService:
    return RerankerService()


@lru_cache
def get_confidence_service() -> ConfidenceService:
    return ConfidenceService()


@lru_cache
def get_faithfulness_service() -> FaithfulnessService:
    return FaithfulnessService()


@lru_cache
def get_analytics_service() -> AnalyticsService:
    return AnalyticsService()


@lru_cache
def get_rag_service() -> RAGService:
    return RAGService(
        embedding_service=get_embedding_service(),
        hybrid_search=get_hybrid_search(),
        query_preprocessor=get_query_preprocessor(),
        reranker=get_reranker(),
        confidence_service=get_confidence_service(),
        faithfulness_service=get_faithfulness_service(),
        analytics_service=get_analytics_service(),
    )
