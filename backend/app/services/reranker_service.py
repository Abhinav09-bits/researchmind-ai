import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class RerankResult:
    chunk_id: str
    content: str
    metadata: dict
    rerank_score: float
    original_score: float


class RerankerService:
    """
    Cross-encoder reranker using FlashRank (ms-marco-MiniLM-L-12-v2).

    Two-stage pipeline:
      Stage 1 — Hybrid search retrieves top-N candidates (fast, bi-encoder)
      Stage 2 — Cross-encoder scores each (query, doc) pair together (accurate)

    The cross-encoder sees query + document simultaneously, enabling full
    attention-based interaction that bi-encoders miss (negation, exact phrasing, context).
    """

    def __init__(self):
        try:
            from flashrank import Ranker
            # MiniLM-L-12 — 25MB, CPU-only, fine-tuned on MS-MARCO relevance pairs
            self._ranker = Ranker(model_name="ms-marco-MiniLM-L-12-v2", cache_dir="/tmp/flashrank")
            logger.info("RerankerService initialized with ms-marco-MiniLM-L-12-v2")
        except ImportError:
            self._ranker = None
            logger.warning("flashrank not installed — reranking disabled. Run: pip install flashrank")

    @property
    def available(self) -> bool:
        return self._ranker is not None

    def rerank(self, query: str, candidates: list, top_k: int = 5) -> list[RerankResult]:
        """
        Rerank candidates using the cross-encoder.

        candidates: list of objects with .chunk_id, .content, .metadata, and a score attribute
        Returns top_k results sorted by cross-encoder relevance score.
        """
        if not self._ranker or not candidates:
            # Fallback: return candidates as-is, converting to RerankResult
            return [
                RerankResult(
                    chunk_id=c.chunk_id,
                    content=c.content,
                    metadata=c.metadata,
                    rerank_score=getattr(c, "rrf_score", getattr(c, "score", 0.0)),
                    original_score=getattr(c, "rrf_score", getattr(c, "score", 0.0)),
                )
                for c in candidates[:top_k]
            ]

        from flashrank import RerankRequest

        passages = [
            {"id": i, "text": c.content, "meta": {"chunk_id": c.chunk_id, "metadata": c.metadata}}
            for i, c in enumerate(candidates)
        ]

        rerank_request = RerankRequest(query=query, passages=passages)
        results = self._ranker.rerank(rerank_request)

        reranked = []
        for r in results[:top_k]:
            original_idx = r["id"]
            original = candidates[original_idx]
            reranked.append(
                RerankResult(
                    chunk_id=original.chunk_id,
                    content=original.content,
                    metadata=original.metadata,
                    rerank_score=round(float(r["score"]), 4),
                    original_score=round(getattr(original, "rrf_score", getattr(original, "score", 0.0)), 4),
                )
            )

        logger.info(f"Reranked {len(candidates)} → {len(reranked)} results for query: '{query[:50]}'")
        return reranked
