import uuid
import re
import logging

from langchain.text_splitter import RecursiveCharacterTextSplitter

from app.core.config import get_settings
from app.services.document_processor import ProcessedChunk

logger = logging.getLogger(__name__)


def _extract_video_id(url: str) -> str:
    """Extract YouTube video ID from any common URL format."""
    patterns = [
        r"(?:v=)([A-Za-z0-9_-]{11})",           # ?v=xxxx
        r"(?:youtu\.be/)([A-Za-z0-9_-]{11})",   # youtu.be/xxxx
        r"(?:embed/)([A-Za-z0-9_-]{11})",        # /embed/xxxx
        r"(?:shorts/)([A-Za-z0-9_-]{11})",       # /shorts/xxxx
    ]
    for pattern in patterns:
        m = re.search(pattern, url)
        if m:
            return m.group(1)
    raise ValueError(f"Could not extract video ID from URL: {url}")


class YouTubeLoader:

    def __init__(self):
        settings = get_settings()
        self._splitter = RecursiveCharacterTextSplitter(
            chunk_size=settings.chunk_size,
            chunk_overlap=settings.chunk_overlap,
            separators=["\n\n", "\n", ". ", " ", ""],
        )

    def load(self, url: str, document_id: str) -> list[ProcessedChunk]:
        """Fetch YouTube transcript and chunk it."""
        try:
            from youtube_transcript_api import YouTubeTranscriptApi
        except ImportError:
            raise RuntimeError("youtube-transcript-api not installed. Run: pip install youtube-transcript-api")

        video_id = _extract_video_id(url)
        logger.info(f"Fetching transcript for video: {video_id}")

        try:
            transcript_list = YouTubeTranscriptApi.get_transcript(video_id)
        except Exception as e:
            raise ValueError(
                f"Could not fetch transcript for {url}. "
                "The video may have no captions, be private, or transcripts may be disabled. "
                f"Details: {e}"
            )

        # Combine transcript segments into full text with timestamps
        # Group into ~60s blocks to preserve temporal context
        blocks = []
        current_block = []
        current_start = 0.0
        block_duration = 0.0

        for segment in transcript_list:
            current_block.append(segment["text"])
            block_duration += segment.get("duration", 2.0)

            if block_duration >= 60:
                start_min = int(current_start // 60)
                start_sec = int(current_start % 60)
                blocks.append(f"[{start_min:02d}:{start_sec:02d}] {' '.join(current_block)}")
                current_start += block_duration
                current_block = []
                block_duration = 0.0

        if current_block:
            start_min = int(current_start // 60)
            start_sec = int(current_start % 60)
            blocks.append(f"[{start_min:02d}:{start_sec:02d}] {' '.join(current_block)}")

        full_text = "\n\n".join(blocks)
        logger.info(f"Transcript: {len(full_text)} chars from video {video_id}")

        raw_chunks = self._splitter.split_text(full_text)
        chunks = []
        for i, text in enumerate(raw_chunks):
            if len(text.strip()) < 40:
                continue
            chunks.append(ProcessedChunk(
                chunk_id=str(uuid.uuid4()),
                content=text.strip(),
                metadata={
                    "document_id": document_id,
                    "source_file": f"YouTube: {video_id}",
                    "source_type": "youtube",
                    "video_id": video_id,
                    "url": f"https://www.youtube.com/watch?v={video_id}",
                    "page_number": 1,
                    "chunk_index": i,
                    "char_count": len(text),
                },
            ))

        if not chunks:
            raise ValueError(f"Transcript was empty or too short for: {url}")

        logger.info(f"YouTube loader: {len(chunks)} chunks from video {video_id}")
        return chunks
