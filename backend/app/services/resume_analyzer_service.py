import logging

import fitz
from google import genai
from google.genai import types

from app.core.config import get_settings

logger = logging.getLogger(__name__)

ANALYZE_PROMPT = """You are an expert recruiter and career coach. Analyze the resume against the job description below.

RESUME:
{resume_text}

JOB DESCRIPTION:
{job_description}

Respond with valid JSON only — no markdown, no explanation outside the JSON:
{{
  "match_score": <integer 0-100>,
  "summary": "<2-3 sentence overall assessment>",
  "matched_keywords": ["<keyword1>", "<keyword2>", ...],
  "missing_keywords": ["<keyword1>", "<keyword2>", ...],
  "strengths": ["<strength1>", "<strength2>", "<strength3>"],
  "gaps": ["<gap1>", "<gap2>", "<gap3>"],
  "recommendations": ["<action1>", "<action2>", "<action3>"]
}}"""

COVER_LETTER_PROMPT = """Write a professional, personalized cover letter for this job application.

RESUME:
{resume_text}

JOB DESCRIPTION:
{job_description}

CANDIDATE NAME (extract from resume): infer from resume

Rules:
- 3-4 short paragraphs
- Reference specific skills from resume that match job requirements
- Confident and enthusiastic tone
- End with a clear call to action
- Do NOT include [brackets] or placeholder text — use real content from the resume
- Start directly with "Dear Hiring Manager," — no subject line"""

HR_EMAIL_PROMPT = """Write a concise, professional email to an HR recruiter for this job application.

RESUME:
{resume_text}

JOB DESCRIPTION:
{job_description}

Rules:
- Subject line first (format: "Subject: <subject>")
- Then a blank line
- Then the email body (3-4 short paragraphs)
- Mention 2-3 specific matching skills
- Professional but warm tone
- End with contact details placeholder: [Your Phone] | [Your Email]
- Start directly with the subject line"""


class ResumeAnalyzerService:

    def __init__(self):
        settings = get_settings()
        self._client = genai.Client(api_key=settings.google_api_key)
        self._model = "gemini-2.5-flash"

    def extract_text(self, pdf_bytes: bytes, filename: str) -> str:
        try:
            with fitz.open(stream=pdf_bytes, filetype="pdf") as pdf:
                pages = []
                for page in pdf:
                    text = page.get_text("text")
                    if text.strip():
                        pages.append(text)
            full = "\n\n".join(pages)
            if not full.strip():
                raise ValueError("No text found in resume. Please use a text-based PDF (not scanned).")
            return full[:8000]  # cap to avoid token overflow
        except Exception as e:
            raise ValueError(f"Could not read resume '{filename}': {e}") from e

    def _generate(self, prompt: str, max_tokens: int = 2048) -> str:
        response = self._client.models.generate_content(
            model=self._model,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.3,
                max_output_tokens=max_tokens,
                thinking_config=types.ThinkingConfig(thinking_budget=0),
            ),
        )
        return response.text.strip()

    def analyze(self, resume_text: str, job_description: str) -> dict:
        import json, re

        prompt = ANALYZE_PROMPT.format(
            resume_text=resume_text[:4000],
            job_description=job_description[:3000],
        )
        raw = self._generate(prompt, max_tokens=1024)

        # Strip markdown code fences if Gemini wraps in ```json
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)

        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            logger.warning(f"JSON parse failed, raw: {raw[:200]}")
            raise ValueError("AI returned malformed analysis. Please try again.")

    def generate_cover_letter(self, resume_text: str, job_description: str) -> str:
        prompt = COVER_LETTER_PROMPT.format(
            resume_text=resume_text[:4000],
            job_description=job_description[:3000],
        )
        return self._generate(prompt, max_tokens=1024)

    def generate_hr_email(self, resume_text: str, job_description: str) -> str:
        prompt = HR_EMAIL_PROMPT.format(
            resume_text=resume_text[:4000],
            job_description=job_description[:3000],
        )
        return self._generate(prompt, max_tokens=800)
