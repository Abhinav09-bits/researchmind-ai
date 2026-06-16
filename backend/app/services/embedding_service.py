import logging
import asyncio
import httpx

from app.core.config import get_settings

logger = logging.getLogger(__name__)

# Direct REST API — bypasses all SDK version issues
EMBEDDING_MODEL = "models/gemini-embedding-001"
GEMINI_EMBED_URL = f"https://generativelanguage.googleapis.com/v1beta/{EMBEDDING_MODEL}:embedContent"
BATCH_SIZE = 20


class EmbeddingService:
    """
    Calls the Gemini Embedding REST API directly via httpx.
    No SDK dependency — immune to version/deprecation issues.
    """

    def __init__(self):
        settings = get_settings()
        self._api_key = settings.google_api_key
        logger.info(f"EmbeddingService initialized — model: {EMBEDDING_MODEL}")

    def _embed_single(self, text: str, task_type: str) -> list[float]:
        """Embed one text synchronously via direct HTTP."""
        url = f"{GEMINI_EMBED_URL}?key={self._api_key}"
        body = {
            "model": EMBEDDING_MODEL,
            "content": {"parts": [{"text": text}]},
            "taskType": task_type,
            "outputDimensionality": 768,
        }
        with httpx.Client(timeout=30) as client:
            response = client.post(url, json=body)

        if response.status_code != 200:
            raise ValueError(f"Embedding API error {response.status_code}: {response.text}")

        return response.json()["embedding"]["values"]

    def _embed_batch_sync(self, texts: list[str], task_type: str) -> list[list[float]]:
        """Embed multiple texts one by one (Gemini REST doesn't support true batching)."""
        return [self._embed_single(text, task_type) for text in texts]

    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """Embed document chunks for indexing (task: RETRIEVAL_DOCUMENT)."""
        all_embeddings: list[list[float]] = []

        for i in range(0, len(texts), BATCH_SIZE):
            batch = texts[i: i + BATCH_SIZE]
            logger.debug(f"Embedding batch {i // BATCH_SIZE + 1} ({len(batch)} chunks)...")

            embeddings = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda b=batch: self._embed_batch_sync(b, "RETRIEVAL_DOCUMENT"),
            )
            all_embeddings.extend(embeddings)

        logger.info(f"Generated {len(all_embeddings)} embeddings")
        return all_embeddings

    async def embed_query(self, text: str) -> list[float]:
        """Embed a user query for retrieval (task: RETRIEVAL_QUERY)."""
        return await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: self._embed_single(text, "RETRIEVAL_QUERY"),
        )
