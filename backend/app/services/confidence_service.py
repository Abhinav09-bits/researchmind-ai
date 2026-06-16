import logging

logger = logging.getLogger(__name__)


class ConfidenceService:
    """
    Derives a confidence level from retrieval/rerank scores.
    No extra API calls — uses scores we already have.

    Thresholds:
      high   > 0.70  — strong semantic match, trust the answer
      medium  0.35–0.70 — partial match, answer likely useful
      low    < 0.35  — weak retrieval, verify manually
    """

    HIGH_THRESHOLD   = 0.70
    MEDIUM_THRESHOLD = 0.35

    def score(self, retrieval_scores: list[float], reranking_applied: bool) -> dict:
        if not retrieval_scores:
            return {"level": "low", "score": 0.0, "label": "🔴 Low — no sources found"}

        # Rerank scores are already cross-encoder relevance (0–1)
        # Vector/RRF scores are also 0–1, so treatment is the same
        top_scores = sorted(retrieval_scores, reverse=True)[:3]
        avg = sum(top_scores) / len(top_scores)
        avg = round(avg, 4)

        if avg >= self.HIGH_THRESHOLD:
            level = "high"
            label = "🟢 High confidence"
        elif avg >= self.MEDIUM_THRESHOLD:
            level = "medium"
            label = "🟡 Medium confidence"
        else:
            level = "low"
            label = "🔴 Low — verify manually"

        logger.debug(f"Confidence: {avg:.3f} → {level} (reranked={reranking_applied})")
        return {"level": level, "score": avg, "label": label}
