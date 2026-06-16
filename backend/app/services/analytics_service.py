import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

LOG_PATH = Path(__file__).parent.parent.parent / "analytics.jsonl"


class AnalyticsService:
    """
    Appends one JSON record per query to analytics.jsonl.
    Provides aggregated stats for the dashboard endpoint.
    """

    def log(
        self,
        query: str,
        answer: str,
        search_mode: str,
        reranking_applied: bool,
        confidence_level: str,
        confidence_score: float,
        faithfulness_verdict: str,
        sources_found: int,
        processing_time_ms: float,
    ) -> None:
        record = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "query": query[:200],
            "answer_length": len(answer),
            "search_mode": search_mode,
            "reranking_applied": reranking_applied,
            "confidence_level": confidence_level,
            "confidence_score": confidence_score,
            "faithfulness": faithfulness_verdict,
            "sources_found": sources_found,
            "processing_time_ms": processing_time_ms,
        }
        try:
            with open(LOG_PATH, "a", encoding="utf-8") as f:
                f.write(json.dumps(record) + "\n")
        except Exception as e:
            logger.warning(f"Failed to write analytics record: {e}")

    def get_stats(self) -> dict:
        """Read all log records and return aggregated statistics."""
        if not LOG_PATH.exists():
            return self._empty_stats()

        records = []
        try:
            with open(LOG_PATH, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            records.append(json.loads(line))
                        except json.JSONDecodeError:
                            continue
        except Exception as e:
            logger.warning(f"Failed to read analytics log: {e}")
            return self._empty_stats()

        if not records:
            return self._empty_stats()

        total = len(records)
        avg_time = sum(r.get("processing_time_ms", 0) for r in records) / total
        avg_sources = sum(r.get("sources_found", 0) for r in records) / total

        confidence_counts = {"high": 0, "medium": 0, "low": 0}
        faithfulness_counts = {"FAITHFUL": 0, "PARTIALLY_FAITHFUL": 0, "NOT_FAITHFUL": 0, "UNKNOWN": 0}
        mode_counts = {"hybrid": 0, "semantic": 0, "keyword": 0}

        for r in records:
            lvl = r.get("confidence_level", "low")
            confidence_counts[lvl] = confidence_counts.get(lvl, 0) + 1

            verdict = r.get("faithfulness", "UNKNOWN")
            faithfulness_counts[verdict] = faithfulness_counts.get(verdict, 0) + 1

            mode = r.get("search_mode", "hybrid")
            mode_counts[mode] = mode_counts.get(mode, 0) + 1

        slowest = sorted(records, key=lambda r: r.get("processing_time_ms", 0), reverse=True)[:5]
        recent = records[-10:]

        return {
            "total_queries": total,
            "avg_processing_time_ms": round(avg_time, 1),
            "avg_sources_found": round(avg_sources, 1),
            "confidence_distribution": confidence_counts,
            "faithfulness_distribution": faithfulness_counts,
            "search_mode_distribution": mode_counts,
            "slowest_queries": [{"query": r["query"], "time_ms": r["processing_time_ms"]} for r in slowest],
            "recent_queries": [
                {
                    "ts": r["ts"],
                    "query": r["query"],
                    "confidence": r.get("confidence_level", "?"),
                    "faithfulness": r.get("faithfulness", "?"),
                    "mode": r.get("search_mode", "?"),
                    "time_ms": r.get("processing_time_ms", 0),
                }
                for r in reversed(recent)
            ],
        }

    def _empty_stats(self) -> dict:
        return {
            "total_queries": 0,
            "avg_processing_time_ms": 0,
            "avg_sources_found": 0,
            "confidence_distribution": {"high": 0, "medium": 0, "low": 0},
            "faithfulness_distribution": {"FAITHFUL": 0, "PARTIALLY_FAITHFUL": 0, "NOT_FAITHFUL": 0, "UNKNOWN": 0},
            "search_mode_distribution": {"hybrid": 0, "semantic": 0, "keyword": 0},
            "slowest_queries": [],
            "recent_queries": [],
        }
