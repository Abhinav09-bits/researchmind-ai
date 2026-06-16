import logging
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from pydantic import BaseModel
from typing import Optional

from app.services.resume_analyzer_service import ResumeAnalyzerService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/resume", tags=["Resume"])


class ResumeAnalysis(BaseModel):
    match_score: int
    summary: str
    matched_keywords: list[str]
    missing_keywords: list[str]
    strengths: list[str]
    gaps: list[str]
    recommendations: list[str]
    cover_letter: str
    hr_email: str


@router.post("/analyze", response_model=ResumeAnalysis)
async def analyze_resume(
    file: UploadFile = File(...),
    job_description: str = Form(...),
):
    """Upload a resume PDF + job description → get match score, keywords, cover letter, HR email."""
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF resumes are supported.")

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")
    if len(job_description.strip()) < 50:
        raise HTTPException(status_code=400, detail="Job description is too short.")

    try:
        svc = ResumeAnalyzerService()
        resume_text = svc.extract_text(content, file.filename)

        # Run analysis + cover letter + HR email (3 Gemini calls)
        analysis = svc.analyze(resume_text, job_description)
        cover_letter = svc.generate_cover_letter(resume_text, job_description)
        hr_email = svc.generate_hr_email(resume_text, job_description)

        return ResumeAnalysis(
            match_score=analysis.get("match_score", 0),
            summary=analysis.get("summary", ""),
            matched_keywords=analysis.get("matched_keywords", []),
            missing_keywords=analysis.get("missing_keywords", []),
            strengths=analysis.get("strengths", []),
            gaps=analysis.get("gaps", []),
            recommendations=analysis.get("recommendations", []),
            cover_letter=cover_letter,
            hr_email=hr_email,
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logger.exception("Resume analysis failed")
        raise HTTPException(status_code=500, detail=f"Analysis failed: {e}")
