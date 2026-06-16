import uuid
import logging

import fitz  # PyMuPDF
from langchain.text_splitter import RecursiveCharacterTextSplitter

from app.core.config import get_settings

logger = logging.getLogger(__name__)


class ProcessedChunk:
    __slots__ = ("chunk_id", "content", "metadata")

    def __init__(self, chunk_id: str, content: str, metadata: dict):
        self.chunk_id = chunk_id
        self.content = content
        self.metadata = metadata


class DocumentProcessor:

    def __init__(self):
        settings = get_settings()
        self._splitter = RecursiveCharacterTextSplitter(
            chunk_size=settings.chunk_size,
            chunk_overlap=settings.chunk_overlap,
            separators=["\n\n", "\n", ". ", " ", ""],
            length_function=len,
            is_separator_regex=False,
        )

    def extract_text_from_pdf(self, file_content: bytes, filename: str) -> list[dict]:
        pages = []
        try:
            with fitz.open(stream=file_content, filetype="pdf") as pdf:
                logger.info(f"Extracting text from '{filename}' — {len(pdf)} pages")
                for page_num, page in enumerate(pdf, start=1):
                    text = page.get_text("text")

                    # If page has no text, try extracting text from any embedded blocks
                    if not text.strip():
                        blocks = page.get_text("blocks")
                        text = " ".join(b[4] for b in blocks if isinstance(b[4], str))

                    if text.strip():
                        pages.append({
                            "page_number": page_num,
                            "text": text,
                        })

        except Exception as e:
            logger.error(f"Failed to extract text from {filename}: {e}")
            raise ValueError(f"Could not read PDF '{filename}': {e}") from e

        if not pages:
            raise ValueError(
                f"No text could be extracted from '{filename}'. "
                "This appears to be a scanned/image-only PDF. "
                "Please use a PDF with selectable text (e.g. from Word, Google Docs, or arxiv.org)."
            )

        logger.info(f"Extracted {len(pages)} pages from '{filename}'")
        return pages

    def chunk_pages(self, pages: list[dict], document_id: str, filename: str) -> list[ProcessedChunk]:
        all_chunks: list[ProcessedChunk] = []
        chunk_index = 0

        for page in pages:
            page_chunks = self._splitter.split_text(page["text"])
            for chunk_text in page_chunks:
                if len(chunk_text.strip()) < 50:
                    continue
                chunk = ProcessedChunk(
                    chunk_id=str(uuid.uuid4()),
                    content=chunk_text.strip(),
                    metadata={
                        "document_id": document_id,
                        "source_file": filename,
                        "page_number": page["page_number"],
                        "chunk_index": chunk_index,
                        "char_count": len(chunk_text),
                    },
                )
                all_chunks.append(chunk)
                chunk_index += 1

        logger.info(f"Chunked '{filename}' into {len(all_chunks)} chunks")
        return all_chunks

    def process_pdf(self, file_content: bytes, filename: str, document_id: str) -> list[ProcessedChunk]:
        pages = self.extract_text_from_pdf(file_content, filename)
        return self.chunk_pages(pages, document_id, filename)
