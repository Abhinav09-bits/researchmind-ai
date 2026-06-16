import logging
from google import genai
from google.genai import types
from app.core.config import get_settings

logger = logging.getLogger(__name__)

# Prompt that instructs Gemini to clean and expand the user's query
# The output feeds directly into the embedding model — cleaner input = better vectors
PREPROCESS_PROMPT = """You are a search query optimizer for a document retrieval system.

Given a raw user question, rewrite it into a clean, precise search query.

Rules:
- Remove filler words ("umm", "like", "you know", "can you tell me")
- Make it specific and information-dense
- Expand abbreviations if obvious
- Keep it as a question or short phrase (max 2 sentences)
- Do NOT answer the question — only rewrite it
- If the query is already clean, return it as-is

Raw query: {query}

Return ONLY the rewritten query, nothing else."""


class QueryPreprocessor:
    """
    Cleans and expands raw user queries before embedding.

    Why this matters:
    - Users type casually: "umm what did he work on"
    - Embeddings of casual text are imprecise
    - Clean query: "projects and work experience of the candidate"
    - This produces a much better embedding → better retrieval
    """

    def __init__(self):
        settings = get_settings()
        self._client = genai.Client(api_key=settings.google_api_key)
        logger.info("QueryPreprocessor initialized")

    def preprocess(self, raw_query: str) -> str:
        """
        Clean and expand a raw user query.
        Falls back to the original query if preprocessing fails.
        """
        # Skip preprocessing for very short or already clean queries
        if len(raw_query.strip()) < 10:
            return raw_query.strip()

        try:
            prompt = PREPROCESS_PROMPT.format(query=raw_query)
            response = self._client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0,
                    max_output_tokens=256,
                ),
            )
            cleaned = response.text.strip().strip('"').strip("'")
            logger.info(f"Query: '{raw_query[:60]}' → '{cleaned[:60]}'")
            return cleaned

        except Exception as e:
            # Never let preprocessing break the query pipeline
            logger.warning(f"Query preprocessing failed, using raw query: {e}")
            return raw_query
