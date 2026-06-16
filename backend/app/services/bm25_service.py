import logging
import re
from dataclasses import dataclass

from rank_bm25 import BM25Okapi

logger = logging.getLogger(__name__)


@dataclass
class BM25Result:
    chunk_id: str
    content: str
    metadata: dict
    bm25_score: float


def tokenize(text: str) -> list[str]:
    """
    Simple whitespace + punctuation tokenizer.
    Lowercases and splits on non-alphanumeric characters.
    BM25 quality is highly dependent on tokenization.
    """
    return re.findall(r'\b\w+\b', text.lower())


class BM25Index:
    """
    In-memory BM25 index over all indexed chunks.

    Why in-memory?
    - BM25 needs the full corpus to compute IDF (Inverse Document Frequency)
    - Qdrant doesn't natively return BM25 scores
    - For production at scale, use Elasticsearch or Qdrant sparse vectors
    - For our use case (<100k chunks), in-memory is fast and simple

    The index is rebuilt whenever a new document is added.
    At startup, it loads existing chunks from Qdrant.
    """

    def __init__(self):
        self._chunk_ids: list[str] = []
        self._contents: list[str] = []
        self._metadatas: list[dict] = []
        self._bm25: BM25Okapi | None = None
        logger.info("BM25Index initialized (empty)")

    def build(self, chunk_ids: list[str], contents: list[str], metadatas: list[dict]) -> None:
        """
        Build the BM25 index from scratch.
        Called after loading existing chunks from Qdrant at startup,
        and after each new document is indexed.
        """
        if not contents:
            logger.warning("BM25: build called with empty corpus")
            return

        self._chunk_ids = chunk_ids
        self._contents = contents
        self._metadatas = metadatas

        tokenized_corpus = [tokenize(text) for text in contents]
        self._bm25 = BM25Okapi(tokenized_corpus)
        logger.info(f"BM25Index built with {len(contents)} chunks")

    def add_chunks(self, chunk_ids: list[str], contents: list[str], metadatas: list[dict]) -> None:
        """
        Add new chunks to the existing index without full rebuild.
        Used when a new document is uploaded.
        """
        self._chunk_ids.extend(chunk_ids)
        self._contents.extend(contents)
        self._metadatas.extend(metadatas)

        # Rebuild is required — BM25 IDF scores change when corpus changes
        if self._contents:
            tokenized_corpus = [tokenize(text) for text in self._contents]
            self._bm25 = BM25Okapi(tokenized_corpus)
            logger.info(f"BM25Index rebuilt with {len(self._contents)} total chunks")

    def search(self, query: str, top_k: int) -> list[BM25Result]:
        """
        Search the BM25 index and return top-k results with scores.

        BM25Okapi.get_scores() returns a score for every document in the corpus.
        We sort and take the top-k with score > 0 (score=0 means no keyword overlap).
        """
        if self._bm25 is None or not self._contents:
            logger.warning("BM25 search called on empty index")
            return []

        query_tokens = tokenize(query)
        if not query_tokens:
            return []

        scores = self._bm25.get_scores(query_tokens)

        # Pair scores with chunk data, filter zero-score results
        scored = [
            (score, i)
            for i, score in enumerate(scores)
            if score > 0
        ]
        scored.sort(key=lambda x: x[0], reverse=True)
        top = scored[:top_k]

        results = [
            BM25Result(
                chunk_id=self._chunk_ids[i],
                content=self._contents[i],
                metadata=self._metadatas[i],
                bm25_score=float(score),
            )
            for score, i in top
        ]

        logger.debug(f"BM25 found {len(results)} results for '{query[:50]}'")
        return results

    @property
    def size(self) -> int:
        return len(self._contents)
