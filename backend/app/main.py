import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1 import router as api_router
from app.core.config import get_settings
from app.core.dependencies import get_vector_store, get_bm25_index, get_reranker

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    FastAPI lifespan — runs setup before the server starts accepting requests,
    and teardown when it shuts down.

    We ensure the Qdrant collection exists at startup so the first request
    doesn't pay the cost of creating it.
    """
    settings = get_settings()
    logger.info(f"ResearchMind AI starting — env={settings.app_env}")

    # Ensure Qdrant collection is ready
    vector_store = get_vector_store()
    vector_store.ensure_collection_exists()
    logger.info(f"Qdrant collection '{settings.qdrant_collection_name}' is ready")

    # Pre-warm reranker — downloads 25MB model at startup, not on first query
    reranker = get_reranker()
    if reranker.available:
        logger.info("RerankerService ready (ms-marco-MiniLM-L-12-v2)")
    else:
        logger.warning("RerankerService unavailable — reranking will be skipped")

    # Load existing chunks into BM25 index so keyword search works immediately
    bm25_index = get_bm25_index()
    existing = vector_store.load_all_chunks()
    if existing["chunk_ids"]:
        bm25_index.build(
            chunk_ids=existing["chunk_ids"],
            contents=existing["contents"],
            metadatas=existing["metadatas"],
        )
        logger.info(f"BM25 index loaded with {bm25_index.size} existing chunks")
    else:
        logger.info("BM25 index empty — will populate on first document upload")

    yield  # server is running

    logger.info("ResearchMind AI shutting down")


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title="ResearchMind AI",
        description="Advanced RAG-powered research assistant",
        version="1.0.0",
        docs_url="/docs",       # Swagger UI
        redoc_url="/redoc",     # ReDoc UI
        lifespan=lifespan,
    )

    # CORS — "*" in dev; set ALLOWED_ORIGINS=https://your-app.vercel.app in prod
    origins = [o.strip() for o in settings.allowed_origins.split(",")]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(api_router)

    @app.get("/health", tags=["Health"])
    async def health_check():
        """Quick liveness check for load balancers and Docker health checks."""
        return {"status": "healthy", "service": "ResearchMind AI"}

    return app


app = create_app()
