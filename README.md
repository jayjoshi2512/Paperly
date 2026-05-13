# Paperly — Enterprise Document Intelligence & Conversational RAG

Paperly is a production-grade Retrieval-Augmented Generation (RAG) platform built for enterprise use. Teams can securely upload internal documents (PDF, DOCX) and converse with them using a high-performance, hallucination-resistant AI architecture.

Built with **FastAPI**, **React**, **Qdrant**, **Groq**, and **Cohere** — designed for extreme performance, factual accuracy, and deep observability.

---

## 🌟 Enterprise Features

### 1. 3-Level Conversational Memory Architecture

Paperly does not simply pass the last N chat messages into the LLM. It implements a fully engineered, three-tier memory system that mirrors how humans actually retain and recall information — short-term, episodic, and semantic long-term memory. Every incoming query triggers all three levels before a response is generated.

---

#### Level 1 — Short-Term Buffer (Immediate Context Window)

**What it does:** Keeps the last 3 conversation turns (6 messages: 3 user + 3 assistant) in a sliding window. This resolves follow-up pronouns and immediate references ("What did you mean by that?", "Can you explain the second point?") without bloating the LLM context.

**How it works (code: `service.py` lines 108–120):**

```python
# Fetch all Q&A for this session from MySQL, in chronological order
result = await db.execute(
    select(Query)
    .where(Query.session_id == request.session_id)
    .order_by(Query.created_at.asc())
)
old_queries = result.scalars().all()
for oq in old_queries:
    chat_history.append({"role": "user",      "content": oq.query_text})
    chat_history.append({"role": "assistant",  "content": oq.answer_text})

chat_history = chat_history[-6:]  # Strict 3-turn window
```

Every previous query and answer for the current session is loaded from MySQL, then immediately **truncated to the last 6 messages** before being sent to the LLM. This keeps the prompt compact while preserving immediate conversational continuity.

**Before the LLM call**, the condensed history is also passed to a `condense_query()` step that rewrites the user's latest question into a fully self-contained, standalone query — eliminating ambiguous pronouns before retrieval runs:

```python
standalone_query = await generator.condense_query(request.query, chat_history)
```

---

#### Level 2 — Semantic Vector Memory (Episodic Recall)

**What it does:** Every completed Q&A exchange is **embedded and stored as a vector** in a dedicated Qdrant collection (`chat_memory`). When a new query arrives, Paperly performs a **vector similarity search across the entire session's history** — not just the last 3 turns — to pull back semantically related exchanges from hours or sessions ago.

**How it works — Write path (code: `memory.py` lines 20–35):**

After every response is streamed and saved, a background task fires asynchronously:

```python
asyncio.create_task(run_memory_cleanup(session_id, db_query.id, workspace_id, user_id))
```

Inside `run_memory_cleanup()`:

```python
# Combine Q&A into a single string and embed it
text_to_embed = f"User: {q.query_text}\nAssistant: {q.answer_text}"
embedding = await embedder.embed_text(text_to_embed)

# Store as a Qdrant vector point tagged with the session_id
point = qmodels.PointStruct(
    id=query_id,
    vector=embedding,
    payload={"session_id": session_id, "text": text_to_embed, "role": "exchange"}
)
await qdrant_db.upsert_chat_memory([point])
```

The full exchange (user + assistant) is embedded together so the vector captures the complete semantic meaning of the topic discussed.

**How it works — Read path (code: `service.py` lines 104–106):**

```python
# The current query's embedding is re-used to search past exchanges
level2_results = await qdrant_db.search_chat_memory(query_emb, request.session_id, top_k=2)
level2_context = [r.get("text") for r in level2_results if r.get("text")]
```

The top-2 semantically closest past exchanges are retrieved and prepended to the chat history as system messages:

```python
past_str = "\n---\n".join(level2_context)
chat_history.insert(0, {"role": "system", "content": f"Recalled Past Conversations:\n{past_str}"})
```

**Key design decision:** The Qdrant search is **scoped by `session_id`** — it only searches within the current session's memory, not across other users or conversations.

---

#### Level 3 — Long-Term Session Summarization (Semantic State)

**What it does:** Every **5th query** in a session, a background LLM call synthesizes the most recent 5 exchanges into a rolling **"Session Summary State"** — a compressed representation of the user's intent, the key entities discussed, and the overall direction of the conversation. This summary persists in MySQL and is injected into the system prompt on every subsequent query.

**How it works — Trigger (code: `memory.py` lines 51–54):**

```python
count_result = await db.execute(
    select(func.count(Query.id)).where(Query.session_id == session_id)
)
query_count = count_result.scalar()

if query_count > 0 and query_count % 5 == 0:  # Every 5th query
    # ... run summarization
```

**Summarization process (code: `memory.py` lines 55–72):**

```python
# Fetch the 5 most recent exchanges
recent_queries = await db.execute(
    select(Query).where(Query.session_id == session_id)
    .order_by(Query.created_at.desc()).limit(5)
)

# Build exchange list for LLM
exchanges = [
    {"role": "user",      "content": rq.query_text},
    {"role": "assistant", "content": rq.answer_text},
    ...
]

# The LLM updates the summary — passing the existing summary so it can be refined
new_summary = await generator.summarize_session(chat_session.summary_state, exchanges)
chat_session.summary_state = new_summary
await db.commit()
```

The `summarize_session()` call passes the **previous summary** alongside the new exchanges, so the LLM produces an **incremental refinement** rather than a from-scratch summary every time.

**How it works — Read path (code: `service.py` lines 98–102):**

```python
session_res = await db.execute(select(ChatSession).where(ChatSession.id == request.session_id))
chat_session = session_res.scalar_one_or_none()
if chat_session and chat_session.summary_state:
    level3_summary = chat_session.summary_state
```

If a summary exists, it is injected at position 0 of the chat history:

```python
chat_history.insert(0, {"role": "system", "content": f"Long-term Session Summary: {level3_summary}"})
```

---

#### Full Memory Pipeline — Request Lifecycle

Every streaming chat request executes this pipeline in order:

```
User sends query
        │
        ▼
[Embed query] ──► Cohere embed-english-v3.0 (1024-dim vector)
        │
        ▼
[Semantic Cache lookup] ──► cosine similarity ≥ 0.92 → stream cached answer + return
        │ (cache miss)
        ▼
[Level 3] Load ChatSession.summary_state from MySQL
        │
        ▼
[Level 2] Vector search in Qdrant chat_memory (top-k=2, scoped by session_id)
        │
        ▼
[Level 1] Load all session queries from MySQL → truncate to last 6 messages
        │
        ▼
[Condense query] ──► LLM rewrites query into standalone form using Level 1 buffer
        │
        ▼
[Hybrid Retrieval] Dense (Qdrant) + Sparse (BM25) → RRF fusion → top-20 chunks
        │
        ▼
[Reranker] BGE cross-encoder → top-5 chunks
        │
        ▼
[Build prompt] Level 3 summary → Level 2 recall → Level 1 buffer → retrieved chunks
        │
        ▼
[LLM Generation] Groq llama-3.3-70b-versatile streaming
        │
        ▼
[Save trace] MySQL (query, answer, chunks, latency, cache_hit)
        │
        ▼
[Background tasks]
    ├─► Semantic cache: store answer vector (if answered)
    ├─► Level 2: embed + upsert Q&A exchange to Qdrant chat_memory
    └─► Level 3: if turn % 5 == 0 → LLM summarize → save to ChatSession
```

---

#### Why This Design?

| Problem | Naive Approach | Paperly's Solution |
|---------|---------------|-------------------|
| Long conversations blow up token limit | Pass all history | Level 1: strict 3-turn buffer |
| Early context forgotten after buffer fills | None | Level 2: vector similarity recall |
| Topic drift across many turns | Re-read all history | Level 3: rolling LLM summary |
| Repeated identical questions slow down the LLM | None | Semantic cache (0.92 cosine threshold) |
| Follow-up pronouns confuse retrieval | Pass raw query | Query condensation step |


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
