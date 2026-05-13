# Paperly — Enterprise Document Intelligence & Conversational RAG

Paperly is a production-grade Retrieval-Augmented Generation (RAG) platform built for enterprise use. Teams can securely upload internal documents (PDF, DOCX) and converse with them using a high-performance, hallucination-resistant AI architecture.

Built with **FastAPI**, **React**, **Qdrant**, **Groq**, and **Cohere** — designed for extreme performance, factual accuracy, and deep observability.

---

## 🌟 Enterprise Features

### 1. 3-Level Conversational Memory
- **Level 1 – Short-Term Buffer:** Sliding window of the last 3 turns for pronoun resolution.
- **Level 2 – Semantic Vector History:** Every Q&A is embedded and stored in a dedicated Qdrant collection. New queries semantically recall any past topic.
- **Level 3 – Session Summarization:** Background LLM synthesizes a running session summary every 5 turns, injected into the system prompt for long-range coherence.

### 2. Multi-Stage Hybrid Retrieval
- **Dense Vector Search** via Cohere `embed-english-v3.0` (1024 dims)
- **Sparse / BM25 Search** — custom in-memory inverted index for exact keyword recall
- **Reciprocal Rank Fusion (RRF)** — merges dense + sparse rankings
- **Cross-Encoder Reranking** via `bge-reranker-v2-m3` for maximum context relevance

### 3. Async Document Processing with Real-Time Status
- Documents are accepted immediately (`202 Accepted`) and processed in the background.
- Per-document progress polling via `GET /docs/{id}/status` (0–100%).
- Frontend shows live progress bars per file.

### 4. Answer Feedback Loop → RAGAS Ground Truth
- Users rate each answer 👍 / 👎 after it streams.
- Positive ratings auto-save the answer as `ground_truth` for future RAGAS evaluation.
- Negative ratings flag the query for review and accept a user-supplied correction.

### 5. Semantic Query Cache
- In-process LRU cache with 0.92 cosine similarity threshold and 30-minute TTL.
- Cache hits are streamed token-by-token for consistent UX, with a ⚡ **Cached** badge.
- Cache is invalidated automatically whenever a document is uploaded or deleted.

### 6. Batch Multi-File Upload
- Upload multiple PDFs/DOCx simultaneously via `POST /docs/upload/batch`.
- Frontend shows individual per-file progress rows with live polling.
- Accepted files begin processing in parallel; rejected files (wrong type, too large) show inline errors.

### 7. Cross-Document Citation Viewer
- Every AI answer includes a **Sources** button.
- Opens a slide-in drawer listing the source documents, page numbers cited, and the highest-scoring text excerpt per document.
- Powered by `GET /chat/{query_id}/citations` which groups retrieved chunks by document.

### 8. Chunking Strategy Benchmark Report
- Compares `recursive`, `fixed`, and `semantic` chunking strategies in a live dashboard table.
- Metrics: document count, average chunk count, average RAG latency, cache hit rate.
- Endpoint: `GET /admin/chunking-benchmark`

### 9. Workspace Q&A Export
- One-click CSV download of all workspace Q&A pairs from the Insights dashboard.
- Columns: query, answer, feedback rating, ground truth, cache hit, latency, timestamp.
- UTF-8 BOM ensures Excel opens the file correctly without encoding issues.
- Endpoint: `GET /admin/export/qa`

### 10. System Health + Metrics Endpoint
- `GET /admin/health` returns a live health snapshot:
  - **Database** — connectivity + round-trip latency (ms)
  - **Qdrant** — collection list
  - **Semantic Cache** — total cached entries across workspaces
  - **Uptime** — seconds since server start
  - **Queries Today** — count of queries in the current UTC day
- The Insights dashboard displays a color-coded health widget (🟢 / 🔴 per service).

### 11. Knowledge Gap Detection & RAGAS Evaluation Dashboard
- Clusters unanswered questions using K-Means to surface suggested knowledge base articles.
- Built-in RAGAS evaluation measuring **Faithfulness** and **Answer Relevancy**.
- Multi-tenant isolation: all data is hard-filtered by `workspace_id`.

---

## 🛠 Tech Stack

| Layer | Technology |
|-------|-----------|
| **Frontend** | React 19, React Router v7, Lucide Icons, Vanilla CSS Modules |
| **Backend** | FastAPI, SQLAlchemy (Async), Uvicorn |
| **Database** | MySQL (users, documents, queries, feedback, ground truth) |
| **Vector DB** | Qdrant (local SQLite mode or Docker-hosted) |
| **LLM Inference** | Groq API (`llama-3.3-70b-versatile`) — ultra-low latency streaming |
| **Embeddings** | Cohere API (`embed-english-v3.0`, 1024 dims) |
| **Reranker** | BGE Reranker v2-m3 via `FlagEmbedding` (local inference) |
| **Cache** | In-process semantic LRU cache (cosine similarity, TTL-based) |

---

## 🚀 Running Locally (Development)

### 1. Database Setup (MySQL via XAMPP)
1. Start MySQL in XAMPP Control Panel.
2. Open phpMyAdmin → create a database named `paperly`.

### 2. Backend Setup

```bash
cd backend
python -m venv venv
.\venv\Scripts\activate        # Windows
# source venv/bin/activate     # Mac/Linux
pip install -r requirements.txt
```

Create `backend/.env`:

```env
MYSQL_URL=mysql+aiomysql://root:@localhost:3306/paperly
QDRANT_URL=local_qdrant_storage
GROQ_API_KEY=your_groq_api_key
COHERE_API_KEY=your_cohere_api_key
JWT_SECRET=super_secret_key_development_only
```

Apply schema migrations:

```bash
python fix_schema.py
```

Start the server:

```bash
uvicorn app.main:app --reload --port 8000
```

### 3. Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173` in your browser.

---

## 🌍 Production Deployment (Docker Compose)

```bash
# Create .env in root from .env.example, then:
docker-compose up --build -d
```

Serves the full stack (FastAPI + React + Qdrant) behind Nginx.

---

## 📄 API Reference

FastAPI auto-generates Swagger docs at `http://localhost:8000/docs`.

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/auth/register` | Register a new user |
| `POST` | `/auth/login` | JWT login |
| `POST` | `/docs/upload` | Upload single document (202 Async) |
| `POST` | `/docs/upload/batch` | Upload multiple documents in parallel |
| `GET` | `/docs/{id}/status` | Poll document processing progress |
| `GET` | `/docs/` | List workspace documents |
| `DELETE` | `/docs/{id}` | Soft-delete a document |
| `POST` | `/chat/stream` | Streaming SSE chat (RAG pipeline) |
| `GET` | `/chat/{id}/trace` | Full retrieval trace for a query |
| `GET` | `/chat/{id}/citations` | Deduplicated source citations |
| `POST` | `/chat/{id}/feedback` | Submit answer feedback (thumbs up/down) |
| `GET` | `/admin/stats` | Workspace query & document stats |
| `GET` | `/admin/feedback-stats` | Feedback health metrics |
| `GET` | `/admin/chunking-benchmark` | Chunking strategy comparison |
| `GET` | `/admin/export/qa` | Download Q&A pairs as CSV |
| `GET` | `/admin/health` | System health + uptime metrics |
| `GET` | `/eval/gaps` | Knowledge gap clusters |
| `GET` | `/eval/scores` | RAGAS evaluation scores |
| `POST` | `/eval/run` | Trigger RAGAS evaluation run |
| `GET` | `/health` | Basic liveness check |
