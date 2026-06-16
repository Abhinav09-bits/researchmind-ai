from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class DocumentUploadResponse(BaseModel):
    """Returned after a PDF is successfully ingested."""
    document_id: str
    filename: str
    total_chunks: int
    collection_name: str
    message: str


class DocumentInfo(BaseModel):
    """Metadata about an indexed document — used for the knowledge base list."""
    document_id: str
    filename: str
    total_chunks: int
    collection_name: str
    uploaded_at: str


class QueryFilters(BaseModel):
    """Optional filters to narrow retrieval scope."""
    document_id: Optional[str] = Field(
        default=None,
        description="Restrict search to a specific document by ID",
    )
    source_file: Optional[str] = Field(
        default=None,
        description="Restrict search to a specific filename",
    )
    min_score: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Override the minimum similarity score threshold",
    )


class QueryRequest(BaseModel):
    """Incoming query from the user."""
    question: str = Field(
        ...,
        min_length=3,
        max_length=2000,
        description="The user's question",
    )
    collection_name: Optional[str] = Field(
        default=None,
        description="Query a specific collection; defaults to global collection",
    )
    top_k: Optional[int] = Field(
        default=None,
        ge=1,
        le=20,
        description="Number of chunks to retrieve",
    )
    filters: Optional[QueryFilters] = Field(
        default=None,
        description="Optional metadata filters to narrow the search",
    )
    preprocess_query: bool = Field(
        default=True,
        description="Whether to auto-clean the query before embedding",
    )
    search_mode: str = Field(
        default="hybrid",
        description="Search mode: 'semantic' (vector only), 'keyword' (BM25 only), 'hybrid' (both)",
    )
    vector_weight: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Weight for vector search in hybrid mode (0=keyword only, 1=vector only)",
    )
    enable_reranking: bool = Field(
        default=True,
        description="Whether to apply cross-encoder reranking after hybrid retrieval",
    )
    rerank_top_k: int = Field(
        default=5,
        ge=1,
        le=20,
        description="Number of final results after reranking (candidates = top_k * 4)",
    )


class SourceChunk(BaseModel):
    """A single retrieved chunk shown as a citation."""
    chunk_id: str
    content: str
    source_file: str
    page_number: Optional[int]
    similarity_score: float
    chunk_index: int


class WebSourceRequest(BaseModel):
    url: str = Field(..., description="Full URL to scrape (must start with http/https)")


class GitHubSourceRequest(BaseModel):
    repo: str  = Field(..., description="owner/repo-name e.g. 'tiangolo/fastapi'")
    branch: str = Field(default="main", description="Branch to index")
    github_token: Optional[str] = Field(default=None, description="Optional PAT for private repos")


class YouTubeSourceRequest(BaseModel):
    url: str = Field(..., description="YouTube video URL")


class SourceIngestionResponse(BaseModel):
    document_id: str
    source_label: str
    source_type: str
    total_chunks: int
    collection_name: str
    message: str


class ConfidenceInfo(BaseModel):
    level: str        # high / medium / low
    score: float      # 0.0 – 1.0
    label: str        # human-readable badge text


class FaithfulnessInfo(BaseModel):
    verdict: str      # FAITHFUL / PARTIALLY_FAITHFUL / NOT_FAITHFUL / UNKNOWN
    explanation: str
    checked: bool


class QueryResponse(BaseModel):
    """Full RAG response returned to the frontend."""
    answer: str
    sources: list[SourceChunk]
    question: str
    preprocessed_question: str
    total_sources_found: int
    processing_time_ms: float
    collection_searched: str
    search_mode: str
    reranking_applied: bool = False
    confidence: Optional[ConfidenceInfo] = None
    faithfulness: Optional[FaithfulnessInfo] = None
