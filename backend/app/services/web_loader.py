import uuid
import logging
import re

import httpx
from langchain.text_splitter import RecursiveCharacterTextSplitter

from app.core.config import get_settings
from app.services.document_processor import ProcessedChunk

logger = logging.getLogger(__name__)

# Tags that carry actual content vs boilerplate
CONTENT_TAGS = {"p", "h1", "h2", "h3", "h4", "h5", "h6", "li", "article", "section", "td", "pre", "blockquote"}
NOISE_TAGS   = {"script", "style", "nav", "footer", "header", "aside", "form", "button", "noscript", "iframe"}


class WebLoader:

    def __init__(self):
        settings = get_settings()
        self._splitter = RecursiveCharacterTextSplitter(
            chunk_size=settings.chunk_size,
            chunk_overlap=settings.chunk_overlap,
            separators=["\n\n", "\n", ". ", " ", ""],
        )

    def load(self, url: str, document_id: str) -> list[ProcessedChunk]:
        """Fetch a URL, strip HTML noise, chunk the clean text."""
        try:
            from bs4 import BeautifulSoup
        except ImportError:
            raise RuntimeError("beautifulsoup4 not installed. Run: pip install beautifulsoup4")

        logger.info(f"Fetching URL: {url}")
        headers = {"User-Agent": "Mozilla/5.0 (ResearchMind AI / research bot)"}

        with httpx.Client(timeout=30, follow_redirects=True) as client:
            response = client.get(url, headers=headers)

        if response.status_code != 200:
            raise ValueError(f"Failed to fetch URL (HTTP {response.status_code}): {url}")

        soup = BeautifulSoup(response.text, "html.parser")

        # Extract page title
        title = soup.title.string.strip() if soup.title and soup.title.string else url

        # Remove boilerplate tags entirely
        for tag in soup.find_all(NOISE_TAGS):
            tag.decompose()

        # Collect text from content-bearing tags
        texts = []
        for tag in soup.find_all(CONTENT_TAGS):
            text = tag.get_text(separator=" ", strip=True)
            if len(text) > 40:  # skip tiny fragments
                texts.append(text)

        # Fallback: grab all body text if no content tags found
        if not texts:
            body = soup.find("body")
            if body:
                texts = [body.get_text(separator="\n", strip=True)]

        if not texts:
            raise ValueError(f"No readable content found at: {url}")

        full_text = "\n\n".join(texts)
        # Collapse excessive whitespace
        full_text = re.sub(r"\n{3,}", "\n\n", full_text)
        full_text = re.sub(r" {2,}", " ", full_text)

        logger.info(f"Extracted {len(full_text)} chars from '{title}'")

        raw_chunks = self._splitter.split_text(full_text)
        chunks = []
        for i, text in enumerate(raw_chunks):
            if len(text.strip()) < 50:
                continue
            chunks.append(ProcessedChunk(
                chunk_id=str(uuid.uuid4()),
                content=text.strip(),
                metadata={
                    "document_id": document_id,
                    "source_file": title[:120],
                    "source_type": "web",
                    "url": url,
                    "page_number": 1,
                    "chunk_index": i,
                    "char_count": len(text),
                },
            ))

        if not chunks:
            raise ValueError(f"Could not extract enough content from: {url}")

        logger.info(f"Web loader: {len(chunks)} chunks from '{url}'")
        return chunks
