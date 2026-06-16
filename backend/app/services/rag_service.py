import logging
import time

from google import genai
from google.genai import types

from app.core.config import get_settings
from app.models.schemas import QueryRequest, QueryResponse, SourceChunk, ConfidenceInfo, FaithfulnessInfo
from app.services.embedding_service import EmbeddingService
from app.services.hybrid_search_service import HybridSearchService
from app.services.reranker_service import RerankerService
from app.services.confidence_service import ConfidenceService
from app.services.faithfulness_service import FaithfulnessService
from app.services.analytics_service import AnalyticsService

logger = logging.getLogger(__name__)

CHAT_MODEL = "gemini-2.5-flash"

SYSTEM_PROMPT = """You are ResearchMind AI, an expert research assistant.

Answer the user's question using ONLY the provided context chunks.

RULES:
1. Use only the provided context. Do not use outside knowledge.
2. If context is insufficient, say: "I don't have enough information in the indexed documents to answer this."
3. Cite sources inline as [Source: <filename>, Page <page>].
4. Be precise and concise. Never fabricate facts."""


class RAGService:

    def __init__(
        self,
        embedding_service: EmbeddingService,
        hybrid_search: HybridSearchService,
        query_preprocessor,
        reranker: RerankerService,
        confidence_service: ConfidenceService,
        faithfulness_service: FaithfulnessService,
        analytics_service: AnalyticsService,
    ):
        settings = get_settings()
        self._embedding_service = embedding_service
        self._hybrid_search = hybrid_search
        self._preprocessor = query_preprocessor
        self._reranker = reranker
        self._confidence = confidence_service
        self._faithfulness = faithfulness_service
        self._analytics = analytics_service
        self._settings = settings
        self._client = genai.Client(api_key=settings.google_api_key)
        logger.info(f"RAGService initialized with {CHAT_MODEL} + hybrid + rerank + confidence + faithfulness")

    async def query(self, request: QueryRequest) -> QueryResponse:
        start_time = time.perf_counter()
        collection = request.collection_name or self._settings.qdrant_collection_name

        # Stage 1a: Preprocess query
        clean_question = (
            self._preprocessor.preprocess(request.question)
            if request.preprocess_query
            else request.question
        )

        # Stage 1b: Embed query
        query_vector = await self._embedding_service.embed_query(clean_question)

        # Stage 1c: Extract filters
        filter_doc_id = None
        filter_source = None
        score_threshold = self._settings.similarity_score_threshold

        if request.filters:
            filter_doc_id = request.filters.document_id
            filter_source = request.filters.source_file
            if request.filters.min_score is not None:
                score_threshold = request.filters.min_score

        # Stage 1d: Retrieve candidates — fetch 4× more when reranking is on
        # so the cross-encoder has a large pool to reorder
        reranking_on = request.enable_reranking and self._reranker.available
        final_k = request.rerank_top_k if reranking_on else (request.top_k or self._settings.retrieval_top_k)
        candidate_k = final_k * 4 if reranking_on else final_k

        hybrid_results = self._hybrid_search.search(
            query_vector=query_vector,
            query_text=clean_question,
            top_k=candidate_k,
            score_threshold=score_threshold,
            collection_name=collection,
            filter_document_id=filter_doc_id,
            filter_source_file=filter_source,
            search_mode=request.search_mode,
            vector_weight=request.vector_weight,
        )

        elapsed = lambda: round((time.perf_counter() - start_time) * 1000, 2)

        if not hybrid_results:
            return QueryResponse(
                answer="I don't have enough information in the indexed documents to answer this question. Please upload relevant documents first.",
                sources=[],
                question=request.question,
                preprocessed_question=clean_question,
                total_sources_found=0,
                processing_time_ms=elapsed(),
                collection_searched=collection,
                search_mode=request.search_mode,
                reranking_applied=False,
            )

        # Stage 2: Cross-encoder reranking — scores (query, doc) together
        if reranking_on:
            reranked = self._reranker.rerank(
                query=clean_question,
                candidates=hybrid_results,
                top_k=final_k,
            )
            sources = [
                SourceChunk(
                    chunk_id=r.chunk_id,
                    content=r.content,
                    source_file=r.metadata.get("source_file", "Unknown"),
                    page_number=r.metadata.get("page_number"),
                    similarity_score=r.rerank_score,
                    chunk_index=r.metadata.get("chunk_index", 0),
                )
                for r in reranked
            ]
            context_chunks = reranked
        else:
            sources = [
                SourceChunk(
                    chunk_id=c.chunk_id,
                    content=c.content,
                    source_file=c.metadata.get("source_file", "Unknown"),
                    page_number=c.metadata.get("page_number"),
                    similarity_score=round(c.rrf_score, 4),
                    chunk_index=c.metadata.get("chunk_index", 0),
                )
                for c in hybrid_results
            ]
            context_chunks = hybrid_results

        # Build context string from final ranked results
        context_parts = []
        for i, chunk in enumerate(context_chunks, start=1):
            source_file = chunk.metadata.get("source_file", "Unknown")
            page = chunk.metadata.get("page_number", "?")
            context_parts.append(
                f"[Context {i}] Source: {source_file}, Page {page}\n{chunk.content}"
            )
        context_text = "\n\n---\n\n".join(context_parts)

        # Stage 3: Generate answer (with retry on 503 overload)
        prompt = f"{SYSTEM_PROMPT}\n\nContext:\n{context_text}\n\nQuestion: {clean_question}"
        response = None
        for attempt in range(3):
            try:
                response = self._client.models.generate_content(
                    model=CHAT_MODEL,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        temperature=0,
                        max_output_tokens=2048,
                    ),
                )
                break
            except Exception as e:
                err = str(e)
                if "503" in err or "UNAVAILABLE" in err:
                    wait = 2 ** attempt
                    logger.warning(f"Gemini 503 on attempt {attempt+1}, retrying in {wait}s…")
                    time.sleep(wait)
                    if attempt == 2:
                        raise RuntimeError("Gemini API is temporarily overloaded. Please try again in a few seconds.") from e
                else:
                    raise

        answer_text = response.text
        final_elapsed = elapsed()

        # Confidence — derived from retrieval scores, zero extra API calls
        retrieval_scores = [s.similarity_score for s in sources]
        confidence_raw = self._confidence.score(retrieval_scores, reranking_on)
        confidence = ConfidenceInfo(**confidence_raw)

        # Faithfulness — second Gemini call to detect hallucinations
        context_texts = [c.content for c in context_chunks]
        faith_raw = self._faithfulness.check(answer_text, context_texts)
        faithfulness = FaithfulnessInfo(**faith_raw)

        # Analytics — fire and forget, never block the response
        try:
            self._analytics.log(
                query=request.question,
                answer=answer_text,
                search_mode=request.search_mode,
                reranking_applied=reranking_on,
                confidence_level=confidence.level,
                confidence_score=confidence.score,
                faithfulness_verdict=faithfulness.verdict,
                sources_found=len(sources),
                processing_time_ms=final_elapsed,
            )
        except Exception:
            pass

        logger.info(
            f"[{request.search_mode.upper()}{'+RERANK' if reranking_on else ''}] "
            f"'{clean_question[:50]}' → {len(sources)} src | {confidence.level} confidence "
            f"| {faithfulness.verdict} | {final_elapsed:.0f}ms"
        )

        return QueryResponse(
            answer=answer_text,
            sources=sources,
            question=request.question,
            preprocessed_question=clean_question,
            total_sources_found=len(sources),
            processing_time_ms=final_elapsed,
            collection_searched=collection,
            search_mode=request.search_mode,
            reranking_applied=reranking_on,
            confidence=confidence,
            faithfulness=faithfulness,
        )
