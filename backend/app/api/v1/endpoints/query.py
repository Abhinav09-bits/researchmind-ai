import logging
from fastapi import APIRouter, HTTPException, Depends

from app.models.schemas import QueryRequest, QueryResponse
from app.services.rag_service import RAGService
from app.core.dependencies import get_rag_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/query", tags=["Query"])


@router.post("", response_model=QueryResponse)
async def query_knowledge_base(
    request: QueryRequest,
    rag_service: RAGService = Depends(get_rag_service),
):
    """
    Ask a question and get a grounded answer with citations.

    Phase 2 features:
    - query is auto-cleaned before embedding (preprocess_query=true)
    - optional filters: document_id, source_file, min_score
    - response includes preprocessed_question so you can see what was actually searched
    """
    logger.info(f"Query: '{request.question[:80]}'")
    try:
        return await rag_service.query(request)
    except Exception as e:
        logger.exception(f"Query failed: '{request.question[:80]}'")
        raise HTTPException(status_code=500, detail=f"Query failed: {str(e)}")
