import uuid
import logging

import httpx
from langchain.text_splitter import RecursiveCharacterTextSplitter

from app.core.config import get_settings
from app.services.document_processor import ProcessedChunk

logger = logging.getLogger(__name__)

# File extensions worth indexing
INDEXABLE_EXTENSIONS = {
    ".md", ".mdx", ".txt", ".rst",          # docs
    ".py", ".js", ".ts", ".tsx", ".jsx",    # code
    ".go", ".rs", ".java", ".cpp", ".c",   # systems
    ".yaml", ".yml", ".toml", ".json",     # config
    ".html", ".css",                        # web
}

MAX_FILE_SIZE_BYTES = 200_000  # skip files over 200KB (minified/generated)
MAX_FILES_PER_REPO  = 200      # safety cap


class GitHubLoader:

    def __init__(self):
        settings = get_settings()
        self._splitter = RecursiveCharacterTextSplitter(
            chunk_size=settings.chunk_size,
            chunk_overlap=settings.chunk_overlap,
            separators=["\n\n", "\n", ". ", " ", ""],
        )

    def load(self, repo: str, branch: str, document_id: str, github_token: str | None = None) -> list[ProcessedChunk]:
        """
        Walk a public GitHub repo tree and index text files.
        repo: "owner/repo-name"
        """
        # Fall back to token from .env if none provided in the request
        token = github_token or get_settings().github_token
        headers = {"Accept": "application/vnd.github+json"}
        if token:
            headers["Authorization"] = f"Bearer {token}"

        # Step 1: get full tree (recursive)
        tree_url = f"https://api.github.com/repos/{repo}/git/trees/{branch}?recursive=1"
        logger.info(f"Fetching repo tree: {tree_url}")

        with httpx.Client(timeout=30) as client:
            resp = client.get(tree_url, headers=headers)

        if resp.status_code == 404:
            raise ValueError(f"Repo or branch not found: {repo}@{branch}. Check spelling and that the repo is public.")
        if resp.status_code != 200:
            raise ValueError(f"GitHub API error {resp.status_code}: {resp.text[:200]}")

        tree_data = resp.json()
        files = [
            item for item in tree_data.get("tree", [])
            if item["type"] == "blob"
            and any(item["path"].endswith(ext) for ext in INDEXABLE_EXTENSIONS)
            and item.get("size", 0) < MAX_FILE_SIZE_BYTES
        ]

        if not files:
            raise ValueError(f"No indexable files found in {repo}@{branch} (checked {len(tree_data.get('tree',[]))} tree entries)")

        files = files[:MAX_FILES_PER_REPO]
        logger.info(f"Found {len(files)} indexable files in {repo}")

        # Step 2: fetch each file's content via raw.githubusercontent.com
        # (avoids API rate limits — raw content CDN has no per-IP limits)
        chunks: list[ProcessedChunk] = []
        chunk_index = 0

        with httpx.Client(timeout=30, follow_redirects=True) as client:
            for file in files:
                path = file["path"]
                raw_url = f"https://raw.githubusercontent.com/{repo}/{branch}/{path}"
                try:
                    r = client.get(raw_url)
                    if r.status_code != 200:
                        logger.warning(f"Skipping {path}: HTTP {r.status_code}")
                        continue

                    raw_text = r.text

                    if not raw_text.strip():
                        continue

                    raw_chunks = self._splitter.split_text(raw_text)
                    for text in raw_chunks:
                        if len(text.strip()) < 40:
                            continue
                        chunks.append(ProcessedChunk(
                            chunk_id=str(uuid.uuid4()),
                            content=text.strip(),
                            metadata={
                                "document_id": document_id,
                                "source_file": f"{repo}/{path}",
                                "source_type": "github",
                                "repo": repo,
                                "branch": branch,
                                "file_path": path,
                                "url": f"https://github.com/{repo}/blob/{branch}/{path}",
                                "page_number": 1,
                                "chunk_index": chunk_index,
                                "char_count": len(text),
                            },
                        ))
                        chunk_index += 1

                except Exception as e:
                    logger.warning(f"Error processing {path}: {e}")
                    continue

        if not chunks:
            raise ValueError(f"No content could be extracted from {repo}@{branch}")

        logger.info(f"GitHub loader: {len(chunks)} chunks from {repo}")
        return chunks
