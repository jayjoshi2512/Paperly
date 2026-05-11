# Paperly — Full Product Development Document

> **One-line pitch:** Drop your company docs, SOPs, and PDFs — get a smart internal assistant that answers questions, detects knowledge gaps, and tells you when policies change.
>
> **Your real goal:** Land an AI Engineer role. This project is engineered to show depth, not just "I called the Gemini API."

---

## 1. The Idea (Sharp, Not Generic)

**Paperly** is an internal knowledge assistant for small teams. Upload your company handbook, SOPs, HR policies, onboarding docs — and your team can chat with them in plain English.

But here's what makes it different from ChatPDF clones:

| Feature | ChatPDF / AskYourPDF | Paperly |
|---|---|---|
| Chat with doc | ✅ | ✅ |
| Multi-doc search | ❌ | ✅ |
| Knowledge gap detection | ❌ | ✅ |
| Policy change alerts | ❌ | ✅ |
| Answer quality scoring | ❌ | ✅ (RAGAS) |
| Retrieval strategy options | ❌ | ✅ |
| Answer audit trail | ❌ | ✅ |

You are not building a business. You are building a portfolio piece that shows you understand **the full RAG engineering lifecycle**, not just "embed → query → answer."

---

## 2. What This Project Proves to an AI Engineer Interviewer

- You can build a real **RAG pipeline from scratch** in Python
- You know the difference between **naive chunking vs semantic chunking**
- You've implemented **hybrid search** (BM25 + vector)
- You've used **reranking** to improve retrieval quality
- You've **evaluated** your RAG system with RAGAS metrics
- You understand **streaming responses** via FastAPI SSE
- You've set up **observability** with Langfuse
- You can **containerize** and **deploy** a multi-service AI app on a VPS

This is the stack. Every decision is justified below.

---

## 3. Tech Stack

### Why Python / FastAPI (not Node/Express)
90% of AI tooling is Python-first. LangChain, LlamaIndex, sentence-transformers, RAGAS — none of these have mature Node equivalents. FastAPI is the Express of Python: async, fast, typed, and has excellent developer experience.

### Why Gemini Free Tier
- `gemini-1.5-flash` → Free, fast, 1M token context window
- `text-embedding-004` → Free, 768-dim embeddings, excellent quality
- No credit card needed for development

### Why Qdrant (self-hosted on VPS)
- Best-in-class free open source vector DB
- Docker-native, runs perfectly on a VPS
- Supports hybrid search (sparse + dense) natively
- Used in production by real companies

### Why MySQL (existing VPS setup)
MySQL is already running on your VPS — no extra container, no extra memory, no setup overhead. Paperly uses `aiomysql` with SQLAlchemy's async engine for non-blocking queries. All schema is designed for MySQL 8.0+ syntax (JSON columns, UUID functions, full-text indexes).

### Why React (frontend)
You already know it. Don't waste energy learning Vue or Svelte for this. The AI layer is where you grow — keep the frontend in your comfort zone.

### Full Stack

| Layer | Technology | Free? |
|---|---|---|
| LLM | Gemini 1.5 Flash (`gemini-1.5-flash`) | ✅ Free tier |
| Embeddings | Google `text-embedding-004` | ✅ Free tier |
| Orchestration | LangChain (Python) | ✅ Open source |
| Vector DB | Qdrant (self-hosted Docker) | ✅ Open source |
| Sparse search | BM25 (rank-bm25 library) | ✅ Open source |
| Reranking | Cohere Rerank API free tier | ✅ 1000 req/mo free |
| Evaluation | RAGAS | ✅ Open source |
| Observability | Langfuse (self-hosted Docker) | ✅ Open source |
| Backend | FastAPI (Python 3.11) | ✅ Open source |
| Auth | JWT (python-jose) | ✅ Open source |
| Database | MySQL 8.0 (existing VPS) | ✅ Already on VPS |
| Frontend | React + Vite + TailwindCSS | ✅ Open source |
| Reverse proxy | Nginx | ✅ Open source |
| Deployment | Docker Compose on VPS | ✅ Your VPS |

**Zero monthly cost.** Everything runs on your friend's VPS.

---

## 4. System Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                            VPS                               │
│                                                              │
│  ┌──────────┐    ┌────────────────────────────────────────┐  │
│  │  Nginx   │───▶│          React Frontend                │  │
│  │ (port 80)│    │          (Vite build, static)          │  │
│  └──────────┘    └────────────────────────────────────────┘  │
│       │                                                      │
│       ▼                                                      │
│  ┌────────────────────────────────────────────────────────┐  │
│  │            FastAPI Backend (port 8000)                 │  │
│  │                                                        │  │
│  │    /auth/*     /docs/*     /chat/*     /eval/*         │  │
│  └────────────────────────────────────────────────────────┘  │
│       │                 │                 │                  │
│       ▼                 ▼                 ▼                  │
│  ┌─────────┐     ┌──────────┐     ┌──────────┐              │
│  │  MySQL  │     │  Qdrant  │     │ Langfuse │              │
│  │  8.0    │     │(port6333)│     │(port3000)│              │
│  │(existing│     └──────────┘     └──────────┘              │
│  │  setup) │                                                 │
│  └─────────┘                                                 │
└──────────────────────────────────────────────────────────────┘
                            │
                            ▼  (external API calls)
                ┌───────────────────────┐
                │   Google Gemini API   │
                │   Cohere Rerank API   │
                └───────────────────────┘
```

---

## 5. The RAG Pipeline (Core Engineering)

This is the heart of the project. Most "RAG tutorials" stop at step 2. You will go to step 7.

### 5.1 Document Ingestion Pipeline

```
PDF Upload
    │
    ▼
Text Extraction (PyMuPDF)
    │
    ▼
Chunking Strategy (your choice — see below)
    │
    ▼
Embedding Generation (text-embedding-004)
    │
    ▼
BM25 Index Update (sparse)
    │
    ▼
Qdrant Upsert (dense vector)
    │
    ▼
Metadata stored in MySQL
```

### 5.2 Chunking Strategies (Implement ALL THREE — this is what gets you hired)

Most tutorials use fixed-size chunking and call it done. You implement three and let the evaluator tell you which is best.

**Strategy A — Fixed Size Chunking**
- Split by N tokens (e.g., 512) with M token overlap (e.g., 50)
- Simple, predictable
- Baseline to beat

**Strategy B — Recursive Character Splitting**
- LangChain's `RecursiveCharacterTextSplitter`
- Respects paragraph and sentence boundaries
- Better semantic coherence than fixed size

**Strategy C — Semantic Chunking**
- Embed every sentence, compute cosine similarity between consecutive sentences
- Split where similarity drops below a threshold (topic change detected)
- Best retrieval quality, slowest to compute
- LangChain has `SemanticChunker` — use it

Store which strategy was used per document in MySQL. Compare retrieval quality in the eval dashboard.

### 5.3 Retrieval Strategy — Hybrid Search

```python
# pseudocode — implement this in retrieval.py

def hybrid_search(query: str, top_k: int = 20):
    # 1. Dense retrieval — semantic similarity
    query_embedding = embed(query)
    dense_results = qdrant.search(query_embedding, limit=top_k)

    # 2. Sparse retrieval — keyword matching
    bm25_scores = bm25_index.get_scores(tokenize(query))
    sparse_results = top_k_by_score(bm25_scores)

    # 3. Reciprocal Rank Fusion — merge both result sets
    fused = reciprocal_rank_fusion([dense_results, sparse_results])

    return fused[:top_k]
```

**Why this matters:** Dense search finds semantically similar content even with different words. Sparse/BM25 finds exact keyword matches. Hybrid catches both. Pure vector search misses "ISO 27001" if the query says "information security standard."

### 5.4 Reranking (Cohere)

After hybrid search returns top 20 results, send them to Cohere Rerank to get the true top 5:

```python
from cohere import Client

def rerank(query: str, documents: list[str], top_n: int = 5):
    co = Client(api_key=COHERE_API_KEY)
    results = co.rerank(
        query=query,
        documents=documents,
        model="rerank-english-v3.0",
        top_n=top_n
    )
    return results
```

Reranking uses a cross-encoder model (much more accurate than bi-encoder similarity) to re-score the candidates. This step alone typically improves answer quality by 15–25%.

### 5.5 Answer Generation (Gemini 1.5 Flash)

```python
async def generate_answer(query: str, context_chunks: list, stream: bool = True):
    prompt = f"""
    You are a helpful assistant for internal company knowledge.
    Answer ONLY based on the provided context. If the answer is not in the context,
    say "I don't have information about this in the uploaded documents."

    Context:
    {format_chunks(context_chunks)}

    Question: {query}

    Provide a clear answer and cite the source document and page number for each fact.
    """

    if stream:
        # Gemini streaming API → FastAPI SSE → React EventSource
        async for chunk in gemini.stream(prompt):
            yield chunk
    else:
        return gemini.generate(prompt)
```

### 5.6 Streaming (FastAPI SSE → React)

```python
# FastAPI
@router.post("/chat/stream")
async def stream_chat(request: ChatRequest):
    async def event_generator():
        async for token in generate_answer(request.query, chunks):
            yield f"data: {json.dumps({'token': token})}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")
```

```jsx
// React
const source = new EventSource('/api/chat/stream')
source.onmessage = (e) => {
  if (e.data === '[DONE]') return source.close()
  const { token } = JSON.parse(e.data)
  setAnswer(prev => prev + token)
}
```

---

## 6. Differentiated Features (Beyond Basic RAG)

### 6.1 Knowledge Gap Detection

After every query, if the system says "I don't have information about this," log the query. After 5+ similar unanswered queries, surface a notification to the admin:

> "⚠️ 7 questions about 'parental leave policy' couldn't be answered. Consider uploading this document."

```sql
-- MySQL table for unanswered queries
CREATE TABLE unanswered_queries (
    id          CHAR(36)     NOT NULL DEFAULT (UUID()),
    workspace_id CHAR(36)    NOT NULL,
    query_text  TEXT         NOT NULL,
    cluster_label VARCHAR(255),
    created_at  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    INDEX idx_workspace (workspace_id),
    INDEX idx_created (created_at)
);
```

Use k-means on the embeddings of unanswered queries to cluster similar ones. Show the top clusters in the admin dashboard with suggested document titles.

### 6.2 Document Change Detection

When a document is re-uploaded with the same name, diff the chunks:
- New chunks → flagged as **Added**
- Deleted chunks → flagged as **Removed**
- Modified chunks → flagged as **Updated**

Notify team members who have queried that document in the last 30 days:
> "📝 Your company handbook was updated. 3 sections changed."

### 6.3 Answer Audit Trail

Every answer is logged with:
- The query text
- Retrieved chunks with their scores
- Which chunking strategy was used
- Reranking scores before and after
- Final generated answer
- The user who asked
- Timestamp and latency

Show this in a collapsible "Sources & Reasoning" panel in the UI. This gives a full trace for debugging bad answers and is what makes an evaluator trust the system.

### 6.4 RAG Evaluation Dashboard (The Differentiator)

Use **RAGAS** to score your RAG system. This is extremely rare in portfolios.

```python
from ragas import evaluate
from ragas.metrics import (
    faithfulness,        # is the answer grounded in the context?
    answer_relevancy,    # is the answer relevant to the question?
    context_precision,   # are the retrieved chunks actually useful?
    context_recall,      # did we miss any relevant chunks?
)

def evaluate_answer(query, answer, retrieved_contexts, ground_truth):
    dataset = Dataset.from_dict({
        "question":     [query],
        "answer":       [answer],
        "contexts":     [retrieved_contexts],
        "ground_truth": [ground_truth],
    })
    return evaluate(dataset, metrics=[
        faithfulness, answer_relevancy, context_precision, context_recall
    ])
```

Show these scores in a dashboard broken down by chunking strategy, document type, and time period. This lets you demonstrate that Strategy C (semantic chunking) scores 0.87 faithfulness vs Strategy A's 0.71 — with actual data, not claims.

---

## 7. Database Schema (MySQL 8.0)

> All tables use `CHAR(36)` for UUIDs populated via MySQL's built-in `UUID()` function. Engine is `InnoDB` throughout. Timestamps use `DATETIME` with `DEFAULT CURRENT_TIMESTAMP`.

```sql
-- Workspaces (multi-tenant root)
CREATE TABLE workspaces (
    id          CHAR(36)     NOT NULL DEFAULT (UUID()),
    name        VARCHAR(255) NOT NULL,
    created_at  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id)
) ENGINE=InnoDB;

-- Users & Auth
CREATE TABLE users (
    id           CHAR(36)     NOT NULL DEFAULT (UUID()),
    workspace_id CHAR(36)     NOT NULL,
    email        VARCHAR(255) NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role         ENUM('admin','member') NOT NULL DEFAULT 'member',
    created_at   DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uq_email (email),
    CONSTRAINT fk_users_workspace FOREIGN KEY (workspace_id)
        REFERENCES workspaces(id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- Documents
CREATE TABLE documents (
    id                CHAR(36)     NOT NULL DEFAULT (UUID()),
    workspace_id      CHAR(36)     NOT NULL,
    uploaded_by       CHAR(36)     NOT NULL,
    filename          VARCHAR(500) NOT NULL,
    file_size_bytes   INT          UNSIGNED,
    page_count        INT          UNSIGNED,
    chunking_strategy ENUM('fixed','recursive','semantic') NOT NULL DEFAULT 'recursive',
    chunk_count       INT          UNSIGNED,
    status            ENUM('processing','ready','failed') NOT NULL DEFAULT 'processing',
    version           TINYINT      UNSIGNED NOT NULL DEFAULT 1,
    created_at        DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    INDEX idx_workspace (workspace_id),
    CONSTRAINT fk_docs_workspace FOREIGN KEY (workspace_id)
        REFERENCES workspaces(id) ON DELETE CASCADE,
    CONSTRAINT fk_docs_user FOREIGN KEY (uploaded_by)
        REFERENCES users(id)
) ENGINE=InnoDB;

-- Chunks (metadata only — vectors live in Qdrant)
CREATE TABLE chunks (
    id              CHAR(36)     NOT NULL DEFAULT (UUID()),
    document_id     CHAR(36)     NOT NULL,
    qdrant_point_id CHAR(36)     NOT NULL,
    chunk_index     INT          UNSIGNED NOT NULL,
    page_number     INT          UNSIGNED,
    token_count     INT          UNSIGNED,
    chunk_text      TEXT         NOT NULL,
    created_at      DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    INDEX idx_document (document_id),
    FULLTEXT idx_ft_text (chunk_text),
    CONSTRAINT fk_chunks_doc FOREIGN KEY (document_id)
        REFERENCES documents(id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- Queries & Answers (audit trail)
CREATE TABLE queries (
    id                   CHAR(36)  NOT NULL DEFAULT (UUID()),
    workspace_id         CHAR(36)  NOT NULL,
    user_id              CHAR(36)  NOT NULL,
    query_text           TEXT      NOT NULL,
    answer_text          TEXT,
    retrieved_chunk_ids  JSON,
    was_answered         TINYINT(1) NOT NULL DEFAULT 1,
    faithfulness_score   FLOAT,
    relevancy_score      FLOAT,
    latency_ms           INT       UNSIGNED,
    created_at           DATETIME  NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    INDEX idx_workspace_time (workspace_id, created_at),
    INDEX idx_user (user_id),
    CONSTRAINT fk_queries_workspace FOREIGN KEY (workspace_id)
        REFERENCES workspaces(id) ON DELETE CASCADE,
    CONSTRAINT fk_queries_user FOREIGN KEY (user_id)
        REFERENCES users(id)
) ENGINE=InnoDB;

-- Unanswered query clusters (knowledge gap detection)
CREATE TABLE unanswered_queries (
    id            CHAR(36)     NOT NULL DEFAULT (UUID()),
    workspace_id  CHAR(36)     NOT NULL,
    query_text    TEXT         NOT NULL,
    cluster_label VARCHAR(255),
    created_at    DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    INDEX idx_workspace (workspace_id),
    CONSTRAINT fk_unanswered_workspace FOREIGN KEY (workspace_id)
        REFERENCES workspaces(id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- Document version diffs
CREATE TABLE document_diffs (
    id           CHAR(36)    NOT NULL DEFAULT (UUID()),
    document_id  CHAR(36)    NOT NULL,
    from_version TINYINT     UNSIGNED NOT NULL,
    to_version   TINYINT     UNSIGNED NOT NULL,
    diff_summary JSON,
    created_at   DATETIME    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    CONSTRAINT fk_diffs_doc FOREIGN KEY (document_id)
        REFERENCES documents(id) ON DELETE CASCADE
) ENGINE=InnoDB;
```

> **Note on MySQL + async Python:** Use `aiomysql` as the driver with `SQLAlchemy[asyncio]`. The connection string format is `mysql+aiomysql://user:pass@host:3306/paperly`. Since MySQL is already running on the VPS, point the backend container at the host IP (or use `host.docker.internal` on Linux with `--add-host`). Do not spin up a MySQL Docker container.

---

## 8. Connecting FastAPI to the Existing MySQL on VPS

Since MySQL is already installed on the VPS (not in Docker), the backend container needs to reach the host machine's MySQL. Here is the exact pattern:

```python
# app/database.py

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.config import settings

engine = create_async_engine(
    settings.DATABASE_URL,  # mysql+aiomysql://user:pass@HOST_IP:3306/paperly
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,     # auto-reconnect on stale connections
    echo=False,
)

AsyncSessionLocal = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
```

```yaml
# docker-compose.yml — backend service
backend:
  build: ./backend
  extra_hosts:
    - "host.docker.internal:host-gateway"   # lets the container reach VPS host MySQL
  environment:
    DATABASE_URL: mysql+aiomysql://paperly_user:${DB_PASSWORD}@host.docker.internal:3306/paperly
```

```sql
-- Run once on your VPS MySQL to create the DB and user
CREATE DATABASE paperly CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'paperly_user'@'%' IDENTIFIED BY 'your_strong_password';
GRANT ALL PRIVILEGES ON paperly.* TO 'paperly_user'@'%';
FLUSH PRIVILEGES;
```

---

## 9. API Endpoints

### Auth
```
POST  /auth/register       Register user (email + password + workspace)
POST  /auth/login          Login, returns access + refresh JWT
POST  /auth/refresh        Exchange refresh token for new access token
```

### Documents
```
POST   /docs/upload        Upload PDF (multipart/form-data)
GET    /docs/              List all docs in workspace (paginated)
GET    /docs/{id}          Get doc details, chunk count, status
DELETE /docs/{id}          Delete doc + remove vectors from Qdrant
GET    /docs/{id}/diff     Show chunk-level diff vs previous version
```

### Chat
```
POST  /chat/query          Non-streaming query (returns full answer)
POST  /chat/stream         Streaming SSE query (token-by-token)
GET   /chat/history        Paginated query history for workspace
GET   /chat/{id}/trace     Full retrieval trace for a single query
```

### Evaluation
```
POST  /eval/run            Run RAGAS evaluation on a set of recent queries
GET   /eval/scores         Scores broken down by chunking strategy + date
GET   /eval/gaps           Knowledge gap clusters (unanswered query groups)
```

### Admin
```
GET   /admin/users         List all users in workspace
POST  /admin/invite        Create a new user account
GET   /admin/stats         Usage stats (queries/day, docs uploaded, top questions)
```

---

## 10. Project Structure

```
paperly/
├── backend/
│   ├── app/
│   │   ├── main.py                    # FastAPI app entry, CORS, router registration
│   │   ├── config.py                  # Settings via pydantic-settings (.env)
│   │   ├── database.py                # MySQL async engine + session factory
│   │   ├── models.py                  # SQLAlchemy ORM models (all tables)
│   │   ├── auth/
│   │   │   ├── router.py              # /auth/* endpoints
│   │   │   ├── service.py             # register, login business logic
│   │   │   └── jwt.py                 # token creation + verification
│   │   ├── documents/
│   │   │   ├── router.py              # /docs/* endpoints
│   │   │   ├── service.py             # upload, delete, diff orchestration
│   │   │   ├── extractor.py           # PyMuPDF → raw text + page metadata
│   │   │   ├── chunkers/
│   │   │   │   ├── base.py            # abstract Chunker class
│   │   │   │   ├── fixed.py           # Strategy A
│   │   │   │   ├── recursive.py       # Strategy B
│   │   │   │   └── semantic.py        # Strategy C
│   │   │   └── diff.py                # chunk-level diff between doc versions
│   │   ├── rag/
│   │   │   ├── embedder.py            # Gemini text-embedding-004 wrapper
│   │   │   ├── retrieval.py           # hybrid search + RRF
│   │   │   ├── reranker.py            # Cohere rerank wrapper
│   │   │   ├── generator.py           # Gemini streaming answer generation
│   │   │   └── bm25_index.py          # in-memory BM25 index, rebuilt on startup
│   │   ├── chat/
│   │   │   ├── router.py              # /chat/* endpoints
│   │   │   └── service.py             # query orchestration, audit logging
│   │   ├── eval/
│   │   │   ├── router.py              # /eval/* endpoints
│   │   │   ├── ragas_eval.py          # RAGAS evaluation runner
│   │   │   └── gap_detector.py        # k-means clustering on unanswered queries
│   │   └── vector_store/
│   │       └── qdrant_client.py       # Qdrant collection setup + upsert + search
│   ├── requirements.txt
│   └── Dockerfile
│
├── frontend/
│   ├── src/
│   │   ├── pages/
│   │   │   ├── Login.jsx
│   │   │   ├── Dashboard.jsx
│   │   │   ├── Chat.jsx               # main chat interface
│   │   │   ├── Documents.jsx          # upload + doc management
│   │   │   └── EvalDashboard.jsx      # RAGAS scores + gap clusters
│   │   ├── components/
│   │   │   ├── ChatMessage.jsx        # streaming token rendering
│   │   │   ├── SourcePanel.jsx        # collapsible retrieval trace
│   │   │   ├── DocUploader.jsx        # drag-and-drop PDF upload
│   │   │   └── ScoreCard.jsx          # RAGAS metric display card
│   │   └── hooks/
│   │       ├── useStreamingChat.js    # EventSource SSE hook
│   │       └── useDocuments.js        # doc CRUD hook
│   ├── package.json
│   └── Dockerfile
│
├── .env                               # all secrets — never commit this
├── docker-compose.yml
├── nginx.conf
└── README.md                          # ← most important file
```

---

## 11. Docker Compose Setup

> MySQL is **not** in Docker Compose — it is already running on the VPS. The backend reaches it via `host.docker.internal`. Everything else is containerized.

```yaml
version: '3.9'

services:
  qdrant:
    image: qdrant/qdrant:latest
    restart: unless-stopped
    ports:
      - "6333:6333"
    volumes:
      - qdrant_data:/qdrant/storage

  langfuse:
    image: langfuse/langfuse:latest
    restart: unless-stopped
    environment:
      DATABASE_URL: mysql+pymysql://paperly_user:${DB_PASSWORD}@host.docker.internal:3306/langfuse
      NEXTAUTH_SECRET: ${LANGFUSE_SECRET}
      NEXTAUTH_URL: http://${VPS_IP}:3000
      TELEMETRY_ENABLED: "false"
    extra_hosts:
      - "host.docker.internal:host-gateway"
    ports:
      - "3000:3000"

  backend:
    build: ./backend
    restart: unless-stopped
    extra_hosts:
      - "host.docker.internal:host-gateway"
    environment:
      DATABASE_URL: mysql+aiomysql://paperly_user:${DB_PASSWORD}@host.docker.internal:3306/paperly
      QDRANT_URL: http://qdrant:6333
      LANGFUSE_HOST: http://langfuse:3000
      LANGFUSE_PUBLIC_KEY: ${LANGFUSE_PUBLIC_KEY}
      LANGFUSE_SECRET_KEY: ${LANGFUSE_SECRET_KEY}
      GEMINI_API_KEY: ${GEMINI_API_KEY}
      COHERE_API_KEY: ${COHERE_API_KEY}
      JWT_SECRET: ${JWT_SECRET}
      JWT_ALGORITHM: HS256
      ACCESS_TOKEN_EXPIRE_MINUTES: 30
    ports:
      - "8000:8000"
    depends_on:
      - qdrant
      - langfuse

  frontend:
    build: ./frontend
    restart: unless-stopped
    environment:
      VITE_API_URL: http://${VPS_IP}:8000

  nginx:
    image: nginx:alpine
    restart: unless-stopped
    ports:
      - "80:80"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
    depends_on:
      - backend
      - frontend

volumes:
  qdrant_data:
```

### .env file (never commit this)

```env
VPS_IP=your.vps.ip.address
DB_PASSWORD=your_strong_mysql_password
GEMINI_API_KEY=your_gemini_api_key
COHERE_API_KEY=your_cohere_api_key
JWT_SECRET=a_very_long_random_string
LANGFUSE_SECRET=another_random_string
LANGFUSE_PUBLIC_KEY=your_langfuse_public_key
LANGFUSE_SECRET_KEY=your_langfuse_secret_key
```

---

## 12. Key Python Libraries

```txt
# requirements.txt

# Web framework
fastapi==0.115.0
uvicorn[standard]==0.30.0
python-multipart==0.0.12

# Database — MySQL async
aiomysql==0.2.0
sqlalchemy[asyncio]==2.0.35

# Auth
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4

# AI / RAG
google-generativeai==0.8.3
langchain==0.3.7
langchain-google-genai==2.0.4
langchain-community==0.3.7
qdrant-client==1.12.0
cohere==5.11.0
rank-bm25==0.2.2

# Document processing
pymupdf==1.24.11

# Evaluation
ragas==0.2.5
datasets==3.1.0

# Observability
langfuse==2.53.5

# Resilience
tenacity==9.0.0

# Utilities
pydantic-settings==2.6.1
python-dotenv==1.0.1
```

---

## 13. Free API Limits (Know These)

| API | Free Tier Limit | What to Do When Hit |
|---|---|---|
| Gemini 1.5 Flash | 15 requests/min, 1M tokens/day | Add exponential backoff with `tenacity` |
| text-embedding-004 | 1500 requests/min | Very generous — won't hit during dev |
| Cohere Rerank | 1000 requests/month | Cache rerank results per query hash |

**Add exponential backoff on all external API calls.** This is production hygiene that interviewers notice.

```python
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=10)
)
async def embed_with_retry(text: str) -> list[float]:
    return await embedder.embed(text)
```

---

## 14. What NOT to Build (Save Time)

- ❌ **Billing / payments** — not needed for portfolio
- ❌ **Email notifications** — log to dashboard instead
- ❌ **Mobile responsive UI** — desktop-only is fine
- ❌ **Multiple LLM providers** — Gemini only, keep it simple
- ❌ **File types other than PDF** — start with PDF, add DOCX later if time allows
- ❌ **Public sign-up flow** — create users directly in MySQL or via an admin endpoint

---

## 15. The README — Treat It Like a Product

This is what hiring managers actually read. Structure it exactly like this:

```markdown
# Paperly

> Internal document intelligence assistant with hybrid RAG, semantic chunking,
> cross-encoder reranking, and built-in retrieval quality evaluation.

## Live Demo
[Link to your VPS] | [Demo video — 3 min]

## Architecture
[Insert architecture diagram here]

## What Makes This Different

### 1. Three Chunking Strategies — Benchmarked
[Table showing RAGAS scores for fixed vs recursive vs semantic chunking]
Key finding: semantic chunking improved faithfulness by 22%

### 2. Hybrid Search (Dense + Sparse)
Pure vector search misses exact keyword queries like "ISO 27001" or "Form 16A".
Paperly combines Qdrant dense search with BM25 keyword search via Reciprocal Rank
Fusion. [Show code snippet]

### 3. Reranking with Cross-Encoders
After hybrid search returns top 20 candidates, Cohere's cross-encoder reranks them
to find the true top 5. [Show before/after retrieval quality numbers]

### 4. Full Retrieval Observability
Every query is traced end-to-end in Langfuse — retrieval scores, reranking scores,
token counts, latency. [Screenshot of Langfuse trace]

## Tech Stack
[Table]

## Local Development
git clone ...
cp .env.example .env   # fill in your keys
docker compose up -d

## Lessons Learned
- Semantic chunking is slower at ingestion but worth it for long-form policy docs
- Reranking made the single biggest improvement to answer quality
- BM25 alone outperforms vector search for exact product codes and regulation names
- RAGAS context_recall was harder to improve than faithfulness
- MySQL's FULLTEXT index was useful for a fallback keyword search during BM25 cold start
```

**The "Lessons Learned" section is gold.** It proves you ran actual experiments, not just followed a tutorial.

---

## 16. The One Thing That Will Make You Stand Out

At the end of your README, add a section called **"Retrieval Quality Experiments."**

Run your RAGAS evaluation on the same 20 test questions across all configurations:

| Configuration | Faithfulness | Answer Relevancy | Context Precision |
|---|---|---|---|
| Fixed chunking, no rerank | 0.71 | 0.68 | 0.65 |
| Recursive chunking, no rerank | 0.78 | 0.73 | 0.70 |
| Semantic chunking, no rerank | 0.84 | 0.79 | 0.76 |
| Semantic chunking + Cohere rerank | **0.91** | **0.86** | **0.83** |

This is the section that makes an AI Engineer interviewer say "this person actually knows what they're doing."

Most candidates write "I built a RAG app." You will write "I benchmarked three chunking strategies and measured a 28% improvement in faithfulness using semantic chunking + cross-encoder reranking."

That is a different conversation entirely.

---

*Built to learn. Engineered to impress.*
