from fastapi import APIRouter
from app.api.v1.endpoints import documents, query, sources, analytics, resume

router = APIRouter(prefix="/api/v1")
router.include_router(documents.router)
router.include_router(query.router)
router.include_router(sources.router)
router.include_router(analytics.router)
router.include_router(resume.router)
