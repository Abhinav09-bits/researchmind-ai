import uuid
import logging
from datetime import datetime, timezone
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends

from app.models.schemas import DocumentUploadResponse, DocumentInfo
from app.services.document_processor import DocumentProcessor
from app.services.embedding_service import EmbeddingService
from app.services.vector_store import VectorStoreService
from app.services.bm25_service import BM25Index
from app.core.dependencies import get_embedding_service, get_vector_store, get_bm25_index
from app.core.config import get_settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/documents", tags=["Documents"])

MAX_FILE_SIZE_BYTES = 50 * 1024 * 1024


@router.post("/upload", response_model=DocumentUploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    embedding_service: EmbeddingService = Depends(get_embedding_service),
    vector_store: VectorStoreService = Depends(get_vector_store),
    bm25_index: BM25Index = Depends(get_bm25_index),
):
    """Upload and index a PDF into the vector store."""
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")

    file_content = await file.read()

    if not file_content:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    if len(file_content) > MAX_FILE_SIZE_BYTES:
        raise HTTPException(status_code=413, detail="File too large. Maximum size is 50MB.")

    settings = get_settings()
    document_id = str(uuid.uuid4())
    collection_name = settings.qdrant_collection_name

    logger.info(f"Ingesting '{file.filename}' — document_id={document_id}")

    try:
        processor = DocumentProcessor()
        chunks = processor.process_pdf(
            file_content=file_content,
            filename=file.filename,
            document_id=document_id,
        )

        if not chunks:
            raise HTTPException(status_code=422, detail="No text could be extracted from the PDF.")

        texts = [chunk.content for chunk in chunks]
        embeddings = await embedding_service.embed_documents(texts)

        vector_store.ensure_collection_exists(collection_name)
        total_stored = vector_store.upsert_chunks(chunks, embeddings, collection_name)

        # Update BM25 index with new chunks so keyword search includes them immediately
        bm25_index.add_chunks(
            chunk_ids=[c.chunk_id for c in chunks],
            contents=[c.content for c in chunks],
            metadatas=[c.metadata for c in chunks],
        )

        logger.info(f"Indexed '{file.filename}' — {total_stored} chunks in '{collection_name}'")

        return DocumentUploadResponse(
            document_id=document_id,
            filename=file.filename,
            total_chunks=total_stored,
            collection_name=collection_name,
            message=f"Successfully indexed '{file.filename}' into {total_stored} searchable chunks.",
        )

    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Ingestion failed for '{file.filename}'")
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {str(e)}")


@router.get("/list", response_model=list[DocumentInfo])
async def list_documents(
    vector_store: VectorStoreService = Depends(get_vector_store),
):
    """List all documents currently indexed in the knowledge base."""
    try:
        docs = vector_store.list_documents()
        return [
            DocumentInfo(
                document_id=d["document_id"],
                filename=d["source_file"],
                total_chunks=0,
                collection_name=get_settings().qdrant_collection_name,
                uploaded_at="",
            )
            for d in docs
        ]
    except Exception as e:
        logger.exception("Failed to list documents")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{document_id}")
async def delete_document(
    document_id: str,
    vector_store: VectorStoreService = Depends(get_vector_store),
):
    """Delete a document and all its chunks from the knowledge base."""
    try:
        vector_store.delete_document(document_id)
        return {"message": f"Document '{document_id}' deleted successfully."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
