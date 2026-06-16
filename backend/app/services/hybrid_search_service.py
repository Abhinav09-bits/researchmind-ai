import logging
from dataclasses import dataclass

from app.services.bm25_service import BM25Index, BM25Result
from app.services.vector_store import VectorStoreService, RetrievedChunk

logger = logging.getLogger(__name__)

# RRF constant — 60 is the standard value from the original paper
# Higher k = reduces the impact of very high-ranked documents
RRF_K = 60


@dataclass
class HybridResult:
    """A chunk that has been ranked by hybrid search."""
    chunk_id: str
    content: str
    metadata: dict
    vector_score: float      # cosine similarity (0–1)
    bm25_score: float        # BM25 raw score
    rrf_score: float         # final combined score (higher = better)
    rank_vector: int         # rank in vector results (1 = best)
    rank_bm25: int           # rank in BM25 results (1 = best)


def reciprocal_rank_fusion(
    vector_results: list[RetrievedChunk],
    bm25_results: list[BM25Result],
    top_k: int,
    vector_weight: float = 0.5,
) -> list[HybridResult]:
    """
    Reciprocal Rank Fusion (RRF) — combines two ranked lists into one.

    Formula: RRF(doc) = Σ weight_i / (k + rank_i)

    Why RRF instead of just averaging scores?
    - BM25 and vector scores are on different scales (not directly comparable)
    - RRF only uses RANK position, not raw scores — scale-invariant
    - Works well even when one method finds the document and the other doesn't
    - Used in production by: Microsoft, Elasticsearch, Qdrant, Cohere

    Example:
      Document A: vector rank 1, bm25 rank 3
      Document B: vector rank 5, bm25 rank 1

      RRF(A) = 0.5/(60+1) + 0.5/(60+3) = 0.0082 + 0.0079 = 0.0161
      RRF(B) = 0.5/(60+5) + 0.5/(60+1) = 0.0077 + 0.0082 = 0.0159
      → Document A wins (slightly better overall rank)
    """
    bm25_weight = 1.0 - vector_weight

    # Build lookup maps: chunk_id → rank (1-indexed)
    vector_rank_map = {r.chunk_id: (i + 1) for i, r in enumerate(vector_results)}
    bm25_rank_map   = {r.chunk_id: (i + 1) for i, r in enumerate(bm25_results)}
    vector_score_map = {r.chunk_id: r.score for r in vector_results}
    bm25_score_map   = {r.chunk_id: r.bm25_score for r in bm25_results}
    content_map      = {r.chunk_id: r.content for r in [*vector_results, *bm25_results]}
    metadata_map     = {r.chunk_id: r.metadata for r in [*vector_results, *bm25_results]}

    # Union of all chunk IDs from both result sets
    all_ids = set(vector_rank_map) | set(bm25_rank_map)

    scored: list[HybridResult] = []
    for chunk_id in all_ids:
        v_rank = vector_rank_map.get(chunk_id)
        b_rank = bm25_rank_map.get(chunk_id)

        v_rrf = vector_weight / (RRF_K + v_rank) if v_rank else 0.0
        b_rrf = bm25_weight   / (RRF_K + b_rank) if b_rank else 0.0
        rrf_score = v_rrf + b_rrf

        scored.append(HybridResult(
            chunk_id=chunk_id,
            content=content_map.get(chunk_id, ""),
            metadata=metadata_map.get(chunk_id, {}),
            vector_score=vector_score_map.get(chunk_id, 0.0),
            bm25_score=bm25_score_map.get(chunk_id, 0.0),
            rrf_score=rrf_score,
            rank_vector=v_rank or 999,
            rank_bm25=b_rank or 999,
        ))

    scored.sort(key=lambda x: x.rrf_score, reverse=True)
    return scored[:top_k]


class HybridSearchService:
    """
    Orchestrates hybrid search:
      1. Run vector search (semantic)
      2. Run BM25 search (keyword)
      3. Fuse results with RRF
      4. Return top-k hybrid ranked chunks
    """

    def __init__(self, vector_store: VectorStoreService, bm25_index: BM25Index):
        self._vector_store = vector_store
        self._bm25_index = bm25_index
        logger.info("HybridSearchService initialized")

    def search(
        self,
        query_vector: list[float],
        query_text: str,
        top_k: int,
        score_threshold: float,
        collection_name: str | None = None,
        filter_document_id: str | None = None,
        filter_source_file: str | None = None,
        search_mode: str = "hybrid",    # "semantic" | "keyword" | "hybrid"
        vector_weight: float = 0.5,
    ) -> list[HybridResult]:
        """
        Run hybrid search and return RRF-fused results.

        search_mode:
          "semantic" → vector search only (Phase 1/2 behavior)
          "keyword"  → BM25 only
          "hybrid"   → both combined via RRF (best quality)
        """
        # ── Semantic (vector) retrieval ────────────────────────────
        vector_results: list[RetrievedChunk] = []
        if search_mode in ("semantic", "hybrid"):
            # Fetch more candidates for fusion (2× top_k)
            fetch_k = top_k * 2 if search_mode == "hybrid" else top_k
            vector_results = self._vector_store.similarity_search(
                query_vector=query_vector,
                top_k=fetch_k,
                score_threshold=score_threshold,
                collection_name=collection_name,
                filter_document_id=filter_document_id,
                filter_source_file=filter_source_file,
            )

        # ── Keyword (BM25) retrieval ───────────────────────────────
        bm25_results: list[BM25Result] = []
        if search_mode in ("keyword", "hybrid"):
            fetch_k = top_k * 2 if search_mode == "hybrid" else top_k
            all_bm25 = self._bm25_index.search(query=query_text, top_k=fetch_k)

            # Apply document/source filters manually (BM25 has no Qdrant filter)
            if filter_document_id:
                all_bm25 = [r for r in all_bm25 if r.metadata.get("document_id") == filter_document_id]
            if filter_source_file:
                all_bm25 = [r for r in all_bm25 if r.metadata.get("source_file") == filter_source_file]

            bm25_results = all_bm25

        # ── Fusion ─────────────────────────────────────────────────
        if search_mode == "semantic":
            return [
                HybridResult(
                    chunk_id=r.chunk_id,
                    content=r.content,
                    metadata=r.metadata,
                    vector_score=r.score,
                    bm25_score=0.0,
                    rrf_score=r.score,
                    rank_vector=i + 1,
                    rank_bm25=999,
                )
                for i, r in enumerate(vector_results[:top_k])
            ]

        if search_mode == "keyword":
            return [
                HybridResult(
                    chunk_id=r.chunk_id,
                    content=r.content,
                    metadata=r.metadata,
                    vector_score=0.0,
                    bm25_score=r.bm25_score,
                    rrf_score=r.bm25_score,
                    rank_vector=999,
                    rank_bm25=i + 1,
                )
                for i, r in enumerate(bm25_results[:top_k])
            ]

        # Hybrid: fuse both
        fused = reciprocal_rank_fusion(
            vector_results=vector_results,
            bm25_results=bm25_results,
            top_k=top_k,
            vector_weight=vector_weight,
        )

        logger.info(
            f"Hybrid search: {len(vector_results)} vector + {len(bm25_results)} BM25 "
            f"→ {len(fused)} fused results (mode={search_mode})"
        )
        return fused
