from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    pydantic-settings automatically reads from .env file and validates types.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Gemini
    google_api_key: str

    # Qdrant — supports both local (host:port) and Qdrant Cloud (https URL + api_key)
    qdrant_host: str = "localhost"
    qdrant_port: int = 6333
    qdrant_api_key: str | None = None
    qdrant_collection_name: str = "researchmind_docs"

    # PostgreSQL
    postgres_url: str = "postgresql+asyncpg://researchmind:researchmind_secret@localhost:5432/researchmind"

    # GitHub — optional token for authenticated API calls (5000 req/hr vs 60)
    github_token: str | None = None

    # App
    app_env: str = "development"
    log_level: str = "INFO"

    # CORS — comma-separated list of allowed origins for production
    allowed_origins: str = "*"

    # RAG tuning parameters — these are the levers you'll tune per use case
    chunk_size: int = 1000        # characters per chunk
    chunk_overlap: int = 200      # overlap between consecutive chunks
    retrieval_top_k: int = 5      # how many chunks to retrieve
    similarity_score_threshold: float = 0.6  # minimum similarity to include a chunk

    # Embedding model dimensions for Gemini text-embedding-004
    embedding_dimensions: int = 768


@lru_cache
def get_settings() -> Settings:
    """
    Cached singleton — settings are read once and reused.
    lru_cache ensures we don't re-parse .env on every request.
    """
    return Settings()
