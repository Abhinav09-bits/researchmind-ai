import logging

from google import genai
from google.genai import types

from app.core.config import get_settings

logger = logging.getLogger(__name__)

FAITHFULNESS_PROMPT = """You are a factual auditor. Determine if the Answer below is fully supported by the Context.

Respond with EXACTLY one of these three labels on the first line, then one sentence explaining why:
FAITHFUL
PARTIALLY_FAITHFUL
NOT_FAITHFUL

Context:
{context}

Answer:
{answer}"""


class FaithfulnessService:
    """
    Uses Gemini to check whether a generated answer is grounded in the retrieved context.
    This catches hallucinations — cases where the model adds facts not in the sources.

    Returns a verdict: FAITHFUL / PARTIALLY_FAITHFUL / NOT_FAITHFUL
    """

    def __init__(self):
        settings = get_settings()
        self._client = genai.Client(api_key=settings.google_api_key)
        self._model = "gemini-2.5-flash"

    def check(self, answer: str, context_chunks: list[str], skip_if_short: bool = True) -> dict:
        """
        answer: the generated answer text
        context_chunks: list of raw chunk content strings used to build the answer
        Returns: { verdict, explanation, checked }
        """
        if not answer or not context_chunks:
            return {"verdict": "UNKNOWN", "explanation": "No answer or context to check.", "checked": False}

        if skip_if_short and len(answer.strip()) < 30:
            return {"verdict": "FAITHFUL", "explanation": "Answer too short to require check.", "checked": False}

        context_text = "\n\n---\n\n".join(context_chunks[:5])  # cap at 5 chunks for speed
        prompt = FAITHFULNESS_PROMPT.format(context=context_text, answer=answer)

        try:
            response = self._client.models.generate_content(
                model=self._model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0,
                    max_output_tokens=150,
                    thinking_config=types.ThinkingConfig(thinking_budget=0),
                ),
            )
            raw = response.text.strip()
            lines = raw.split("\n", 1)
            verdict = lines[0].strip().upper()
            explanation = lines[1].strip() if len(lines) > 1 else ""

            if verdict not in {"FAITHFUL", "PARTIALLY_FAITHFUL", "NOT_FAITHFUL"}:
                verdict = "UNKNOWN"

            logger.info(f"Faithfulness: {verdict}")
            return {"verdict": verdict, "explanation": explanation, "checked": True}

        except Exception as e:
            logger.warning(f"Faithfulness check failed: {e}")
            return {"verdict": "UNKNOWN", "explanation": str(e), "checked": False}
