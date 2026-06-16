import uuid
import logging

from fastapi import APIRouter, HTTPException, Depends

from app.models.schemas import (
    WebSourceRequest, GitHubSourceRequest, YouTubeSourceRequest, SourceIngestionResponse,
)
from app.services.web_loader import WebLoader
from app.services.github_loader import GitHubLoader
from app.services.youtube_loader import YouTubeLoader
from app.services.source_ingestion_service import SourceIngestionService
from app.core.dependencies import get_embedding_service, get_vector_store, get_bm25_index

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/sources", tags=["Sources"])


def _make_ingestion_service(
    embedding_service=Depends(get_embedding_service),
    vector_store=Depends(get_vector_store),
    bm25_index=Depends(get_bm25_index),
) -> SourceIngestionService:
    return SourceIngestionService(embedding_service, vector_store, bm25_index)


@router.post("/web", response_model=SourceIngestionResponse)
async def ingest_web_url(
    request: WebSourceRequest,
    ingestion: SourceIngestionService = Depends(_make_ingestion_service),
):
    """Scrape a web page and index its content."""
    if not request.url.startswith(("http://", "https://")):
        raise HTTPException(status_code=400, detail="URL must start with http:// or https://")

    try:
        document_id = str(uuid.uuid4())
        loader = WebLoader()
        chunks = loader.load(url=request.url, document_id=document_id)
        result = await ingestion.ingest(chunks, source_label=request.url)

        return SourceIngestionResponse(
            document_id=result["document_id"],
            source_label=result["source_label"],
            source_type="web",
            total_chunks=result["total_chunks"],
            collection_name=result["collection_name"],
            message=f"Successfully indexed {result['total_chunks']} chunks from {request.url}",
        )
    except (ValueError, RuntimeError) as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logger.exception(f"Web ingestion failed for {request.url}")
        raise HTTPException(status_code=500, detail=f"Web ingestion failed: {e}")


@router.post("/github", response_model=SourceIngestionResponse)
async def ingest_github_repo(
    request: GitHubSourceRequest,
    ingestion: SourceIngestionService = Depends(_make_ingestion_service),
):
    """Index all text/code files from a public GitHub repository."""
    if "/" not in request.repo or len(request.repo.split("/")) != 2:
        raise HTTPException(status_code=400, detail="repo must be in 'owner/repo-name' format")

    try:
        document_id = str(uuid.uuid4())
        loader = GitHubLoader()
        chunks = loader.load(
            repo=request.repo,
            branch=request.branch,
            document_id=document_id,
            github_token=request.github_token,
        )
        result = await ingestion.ingest(chunks, source_label=f"github:{request.repo}")

        return SourceIngestionResponse(
            document_id=result["document_id"],
            source_label=result["source_label"],
            source_type="github",
            total_chunks=result["total_chunks"],
            collection_name=result["collection_name"],
            message=f"Successfully indexed {result['total_chunks']} chunks from {request.repo}@{request.branch}",
        )
    except (ValueError, RuntimeError) as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logger.exception(f"GitHub ingestion failed for {request.repo}")
        raise HTTPException(status_code=500, detail=f"GitHub ingestion failed: {e}")


@router.post("/youtube", response_model=SourceIngestionResponse)
async def ingest_youtube_video(
    request: YouTubeSourceRequest,
    ingestion: SourceIngestionService = Depends(_make_ingestion_service),
):
    """Fetch a YouTube transcript and index it."""
    if "youtube.com" not in request.url and "youtu.be" not in request.url:
        raise HTTPException(status_code=400, detail="URL must be a YouTube link")

    try:
        document_id = str(uuid.uuid4())
        loader = YouTubeLoader()
        chunks = loader.load(url=request.url, document_id=document_id)
        result = await ingestion.ingest(chunks, source_label=request.url)

        return SourceIngestionResponse(
            document_id=result["document_id"],
            source_label=result["source_label"],
            source_type="youtube",
            total_chunks=result["total_chunks"],
            collection_name=result["collection_name"],
            message=f"Successfully indexed {result['total_chunks']} chunks from YouTube video",
        )
    except (ValueError, RuntimeError) as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logger.exception(f"YouTube ingestion failed for {request.url}")
        raise HTTPException(status_code=500, detail=f"YouTube ingestion failed: {e}")
