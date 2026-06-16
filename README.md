# ResearchMind AI

An advanced, production-deployed Retrieval-Augmented Generation (RAG) system that lets you chat with your documents. Upload PDFs, GitHub repositories, web pages, or YouTube videos — then ask questions and get grounded, hallucination-checked answers powered by Gemini 2.5 Flash.

**Live Demo:** [researchmind-ai-neon.vercel.app](https://researchmind-ai-neon.vercel.app)  
**Backend API:** [researchmind-ai-anvp.onrender.com](https://researchmind-ai-anvp.onrender.com/docs)

---

## Features

- **Hybrid Search** — BM25 keyword search + vector semantic search, fused with Reciprocal Rank Fusion (RRF)
- **Cross-Encoder Reranking** — FlashRank MiniLM-L-12 reranks top-20 candidates to return the most relevant top-5
- **Multi-Source Ingestion** — PDF, Web (BeautifulSoup), GitHub (REST API + CDN), YouTube (transcript API)
- **Confidence Scoring** — averages top-3 retrieval scores into HIGH / MEDIUM / LOW signal
- **Hallucination Detection** — secondary Gemini call verifies every answer is grounded in retrieved context
- **Analytics Dashboard** — tracks queries, response times, confidence distribution, faithfulness stats
- **Resume Analyzer** — upload a PDF resume + paste a job description → get match score, missing keywords, cover letter, and HR email

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.11, FastAPI, Uvicorn |
| Frontend | Next.js 15, TypeScript, Tailwind CSS |
| LLM | Gemini 2.5 Flash (`gemini-2.5-flash`) |
| Embeddings | Gemini `text-embedding-004` |
| Vector Database | Qdrant Cloud |
| Keyword Search | BM25 (`rank-bm25`) |
| Reranker | FlashRank (`ms-marco-MiniLM-L-12-v2`) |
| PDF Processing | PyMuPDF |
| Web Scraping | httpx + BeautifulSoup4 |
| YouTube | `youtube-transcript-api` |
| Deployment | Render (backend) · Vercel (frontend) |

---

## Architecture

```
User Query
    │
    ▼
Query Preprocessor (clean + expand)
    │
    ├──► Vector Search (Qdrant)  ──┐
    │                              ├──► RRF Fusion ──► Top 20 Candidates
    └──► BM25 Keyword Search    ──┘
                                          │
                                          ▼
                              FlashRank Cross-Encoder Reranker
                                          │
                                          ▼
                                      Top 5 Chunks
                                          │
                                          ▼
                              Gemini 2.5 Flash (Answer Generation)
                                          │
                              ┌───────────┴───────────┐
                              ▼                       ▼
                     Confidence Score         Faithfulness Check
                    (retrieval quality)    (hallucination detection)
                              │
                              ▼
                       Analytics Logger
```

---

## Project Structure

```
researchmind-ai/
├── backend/
│   ├── app/
│   │   ├── api/v1/endpoints/     # documents, query, sources, analytics, resume
│   │   ├── core/                 # config, dependencies
│   │   ├── models/               # Pydantic schemas
│   │   └── services/
│   │       ├── rag_service.py            # main pipeline orchestrator
│   │       ├── hybrid_search_service.py  # BM25 + vector + RRF
│   │       ├── reranker_service.py       # FlashRank cross-encoder
│   │       ├── confidence_service.py     # retrieval quality scoring
│   │       ├── faithfulness_service.py   # hallucination detection
│   │       ├── analytics_service.py      # JSONL query logging
│   │       ├── web_loader.py             # BeautifulSoup web scraper
│   │       ├── github_loader.py          # GitHub REST API loader
│   │       ├── youtube_loader.py         # YouTube transcript loader
│   │       └── resume_analyzer_service.py
│   ├── requirements.txt
│   └── render.yaml
└── frontend-next/
    ├── app/
    │   ├── page.tsx              # main chat interface
    │   ├── analytics/page.tsx    # analytics dashboard
    │   └── resume/page.tsx       # resume analyzer
    ├── components/
    │   ├── Sidebar.tsx           # source ingestion panel
    │   ├── ChatArea.tsx          # query input + mode toggle
    │   └── MessageBubble.tsx     # answer with badges + sources
    └── lib/
        ├── api.ts                # typed API client
        └── types.ts              # TypeScript interfaces
```

---

## RAG Pipeline — 6 Phases

| Phase | Feature | Key Technologies |
|---|---|---|
| 1 | Document ingestion + vector storage | PyMuPDF, Gemini Embeddings, Qdrant |
| 2 | Semantic retrieval + LLM generation | Qdrant ANN, Gemini 2.5 Flash |
| 3 | Hybrid search | BM25, RRF fusion |
| 4 | Cross-encoder reranking | FlashRank MiniLM-L-12 |
| 5 | Multi-source ingestion | Web, GitHub, YouTube loaders |
| 6 | Production features | Confidence, faithfulness, analytics, resume analyzer |

---

## Getting Started

### Prerequisites

- Python 3.11+
- Node.js 18+
- [Qdrant Cloud](https://cloud.qdrant.io) account
- [Google AI Studio](https://aistudio.google.com) API key

### Backend Setup

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env
# Fill in GOOGLE_API_KEY, QDRANT_HOST, QDRANT_API_KEY

uvicorn app.main:app --reload --port 8001
```

### Frontend Setup

```bash
cd frontend-next
npm install

# Create .env.local
echo "NEXT_PUBLIC_API_URL=http://localhost:8001/api/v1" > .env.local

npm run dev
```

Open [http://localhost:3000](http://localhost:3000)

### Environment Variables

**Backend (`backend/.env`)**

```env
GOOGLE_API_KEY=your_gemini_api_key
QDRANT_HOST=https://your-cluster.cloud.qdrant.io
QDRANT_API_KEY=your_qdrant_api_key
GITHUB_TOKEN=github_pat_...        # optional, for GitHub ingestion
ALLOWED_ORIGINS=http://localhost:3000
APP_ENV=development
```

**Frontend (`frontend-next/.env.local`)**

```env
NEXT_PUBLIC_API_URL=http://localhost:8001/api/v1
```

---

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/v1/documents/upload` | Upload PDF |
| `POST` | `/api/v1/query` | Ask a question |
| `POST` | `/api/v1/sources/web` | Ingest a web URL |
| `POST` | `/api/v1/sources/github` | Ingest a GitHub repository |
| `POST` | `/api/v1/sources/youtube` | Ingest a YouTube video |
| `POST` | `/api/v1/resume/analyze` | Analyze resume vs job description |
| `GET` | `/api/v1/analytics/stats` | Get usage analytics |
| `GET` | `/health` | Health check |

Full Swagger docs available at `/docs` when running locally.

---

## Deployment

### Backend → Render

1. New Web Service → connect GitHub repo
2. Root Directory: `backend`
3. Build Command: `pip install -r requirements.txt`
4. Start Command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
5. Add environment variables: `GOOGLE_API_KEY`, `QDRANT_HOST`, `QDRANT_API_KEY`, `PYTHON_VERSION=3.11.0`

### Frontend → Vercel

1. New Project → import GitHub repo
2. Root Directory: `frontend-next`
3. Add environment variable: `NEXT_PUBLIC_API_URL=https://your-render-url.onrender.com/api/v1`

---

## Key Design Decisions

**Why two-stage retrieval?**  
Bi-encoders (vector search) are fast enough to run over millions of documents but less accurate. Cross-encoders are highly accurate but too slow for full-corpus search. The two-stage approach retrieves 20 candidates fast, then reranks them accurately.

**Why hybrid search over pure vector search?**  
Vector search misses exact keyword matches (e.g. specific model names, error codes). BM25 handles exact terms well but misses semantic similarity. RRF fusion captures both signals without needing to normalise scores across different units.

**Why a second LLM call for faithfulness?**  
Confidence score measures retrieval quality — it cannot tell you if the LLM fabricated information not present in the retrieved chunks. The faithfulness check directly verifies whether the generated answer is grounded in the provided context.

---

## License

MIT
