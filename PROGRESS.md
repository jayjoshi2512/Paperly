# Paperly — Progress Log

## [2026-05-11] Phase 1 Complete — Foundation
**Built:**
- Project structure created
- requirements.txt finalized
- config.py: Settings with all env vars
- database.py: async MySQL engine, session factory, get_db dependency
- models.py: all 6 tables — workspaces, users, documents, chunks, queries, unanswered_queries
- auth system: jwt.py, schemas.py, service.py, router.py
- FastAPI main.py with router registration and health check
- Docker: backend Dockerfile, .dockerignore
- docker-compose.yml and nginx.conf

**Decisions made:**
- Using CHAR(36) with UUID() default instead of binary UUIDs for readability in dev.
- pool_pre_ping=True on engine to handle MySQL connection drops.
- Login payload uses custom JSON `LoginRequest` rather than form-encoded `OAuth2PasswordRequestForm` to match specified schemas.

**Blockers hit:**
- None.

**Next:** Phase 2 — RAG Core (extractor, chunkers, embedder, Qdrant)

## [2026-05-11] Phase 2 Complete — RAG Core
**Built:**
- qdrant_client.py: Setup collection and batch upsert vectors
- embedder.py: Gemini text-embedding-004 wrapper with tenacity retry
- bm25_index.py: In-memory sparse index using rank-bm25
- chunkers: base.py, fixed.py, recursive.py, semantic.py
- extractor.py: PyMuPDF extraction with header/footer stripping
- diff.py: SequenceMatcher diffing of chunks across doc versions
- documents/: schemas.py, service.py, router.py with full ingest pipeline
- retrieval.py: Hybrid search combining dense+sparse with RRF (k=60)
- reranker.py: Cohere rerank with in-memory LRU cache
- generator.py: Gemini answer generation with streaming capability
- main.py: Lifespan updated to rebuild BM25 index on startup

**Decisions made:**
- Used difflib SequenceMatcher for chunk diffing to keep dependencies low while accurately tracking chunk insertions/deletions.
- Missing Qdrant payload metadata for purely BM25-found chunks are fetched dynamically from MySQL during hybrid search.
- Used LangChain Experimental for SemanticChunker since it moved from core.

**Blockers hit:**
- None.

**Next:** Phase 3 — Differentiated Features (Chat orchestration, Eval, Admin)

## [2026-05-11] Phase 3 Complete — Differentiated Features
**Built:**
- chat/schemas.py, service.py, router.py: Full orchestration of RAG pipeline, async answer streaming, and retrieval trace logging.
- eval/ragas_eval.py: Integration with RAGAS for evaluation of faithfulness and relevancy metrics based on stored queries.
- eval/gap_detector.py: Unanswered query clustering using scikit-learn KMeans, and title generation via Gemini for actionable gap insights.
- eval/router.py: Endpoints to run evaluations and fetch scores/gaps.
- admin/schemas.py, router.py: Admin workspace usage stats, query volumes, top questions, and user invites.

**Decisions made:**
- Used KMeans with a capped `k=5` for gap clustering to maintain cluster cohesion, dynamically adjusting if fewer queries are available.
- Dummy ground truths used for context recall/precision in RAGAS due to zero-shot unlabelled system scope. Primary evaluation focuses on faithfulness and relevancy.

**Blockers hit:**
- None.

**Next:** Phase 4 — Frontend (React App)

## [2026-05-11] Phase 4 Complete — Frontend
**Built:**
- Vite + React scaffolded.
- api/client.js: Fetch wrapper with Auth Bearer injection.
- Hooks: useAuth (JWT logic), useDocuments (CRUD logic), useStreamingChat (SSE parsing logic).
- Layout: Sidebar navigation with Lucide icons.
- Pages: 
  - Login: Toggle between sign in and register workspace.
  - Chat: Render Markdown, stream chunks in real-time, smooth scrolling.
  - Documents: Upload with strategy select, table view of chunk counts and status.
  - EvalDashboard: Combined admin usage stats (docs, queries, gaps) and RAGAS score viewer.

**Decisions made:**
- Used `fetch` with standard SSE decoding instead of heavy libraries.
- React-Markdown used for rendering Gemini outputs.
- Direct connection to `localhost:8000` via CORS to simplify dev environment setup.

**Blockers hit:**
- None.

**Next:** Complete Portfolio Deliverables.

## [2026-05-11] Phase 5 Complete — Deployment & Finalization
**Built:**
- Finalized `README.md` with complete local setup instructions (XAMPP + local python/node) and production deployment instructions.
- Confirmed `docker-compose.yml` and `nginx.conf` readiness.
- Completed all task tracking files.

**Deployment Runbook:**
1. **Local Dev:** Start XAMPP MySQL -> Run Qdrant docker container -> Run `uvicorn app.main:app --reload` -> Run `npm run dev` in frontend.
2. **Production:** Define `.env` -> Ensure VPS MySQL is running -> Run `docker-compose up --build -d` -> Nginx handles reverse proxying on port 80.

**Blockers hit:**
- None. Project is ready for portfolio submission.

**Next:** Final Handover.

---

## [2026-05-13] Phase 6, Feature 1 Complete — DOCX Support

**Built:**
- `backend/app/documents/extractor.py`: Upgraded `extract_text_from_docx()` to spec — 500-word virtual pagination, table extraction (pipe-separated rows), heading preservation, robust ImportError and corruption handling. `extract_text()` router updated with clearer error message.
- `backend/requirements.txt`: `python-docx>=1.1.0` already present.
- `backend/app/documents/router.py`: Already accepts `.pdf`, `.docx`, `.doc`.
- `backend/app/documents/service.py`: Already calls `extract_text(file_bytes, file.filename)`.
- `frontend/src/pages/Chat.jsx`: Already uses `accept=".pdf,.docx,.doc"`.

**Decisions made:**
- Chose 500-word virtual pages for DOCX (vs 3000-char prior) to match the spec exactly and give more consistent chunk sizes with the downstream chunkers.
- Tables extracted after body paragraphs to preserve document order semantics.

**Blockers hit:**
- None.

**Next:** Feature 2 — Rate Limiting Middleware.

---

## [2026-05-13] Phase 6, Feature 2 Complete — Rate Limiting Middleware

**Built:**
- `backend/app/limiter.py` (new): Singleton `slowapi.Limiter` instance keyed on client IP.
- `backend/app/main.py`: Imports limiter, attaches `app.state.limiter`, registers `RateLimitExceeded` handler, sets `app.state.start_time` for uptime tracking.
- `backend/app/chat/router.py`: Added `@limiter.limit("15/minute")` to `POST /chat/stream` and `POST /chat/query`; added `request: Request` param as slowapi requires.
- `backend/app/documents/router.py`: Added `@limiter.limit("10/minute")` to `POST /docs/upload`; added `request: Request` param.
- `backend/requirements.txt`: Added `slowapi==0.1.9`.

**Decisions made:**
- Used `get_remote_address` as the key function (IP-based limiting). JWT-user-based limiting would need custom key functions and adds complexity not required at this stage.
- Rate limits match Groq free tier: 15/min for chat, 10/min for uploads (Cohere embed budget).

**Blockers hit:**
- None.

**Next:** Feature 3 — Async Document Processing with Real-Time Status.

---

## [2026-05-13] Phase 6, Feature 3 Complete — Async Document Processing

**Built:**
- `backend/app/documents/service.py`: Split into `create_document_record()` (sync, inserts row, returns 202) and `process_document_async()` (background, full pipeline with 5 progress steps). Added `_update_progress()` helper that commits immediately so polling sees live updates. Added `get_document_status()` with workspace isolation.
- `backend/app/documents/router.py`: Upload endpoint now returns 202 `DocumentUploadResponse` + kicks off `BackgroundTasks`. New `GET /docs/{id}/status` endpoint for polling.
- `backend/app/documents/schemas.py`: Added `DocumentUploadResponse` and `DocumentStatusResponse` schemas; `DocumentResponse` now includes `progress_pct` and `progress_message`.
- `backend/app/models.py`: Added `progress_pct` (TINYINT) and `progress_message` (VARCHAR 255) columns to `Document`.
- `backend/fix_schema.py`: Added `ALTER TABLE documents ADD COLUMN IF NOT EXISTS progress_pct/progress_message` — migration run and verified.
- `frontend/src/hooks/useDocuments.js`: `uploadDocument()` handles 202 response; new `pollDocumentStatus()` polls every 2s, calls `onUpdate/onComplete/onError` callbacks.
- `frontend/src/pages/Chat.jsx`: Upload now shows animated progress bar (% + message), green "Ready" flash on completion, red error banner on failure. Uses `useDocuments` hook.
- `frontend/src/pages/Chat.module.css`: Added progress bar CSS (fill animation, fadeIn, success/error states).

**Decisions made:**
- Background task uses its own `AsyncSessionLocal()` session (cannot share request-scoped session which closes after 202 is returned).
- `_update_progress()` commits immediately so the 2s poll always sees fresh data.
- Legacy `upload_document()` kept for any internal callers (runs pipeline synchronously).

**Blockers hit:**
- None.

**Next:** Feature 4 — Answer Feedback Loop → Real RAGAS Ground Truth.

---

## [2026-05-13] Phase 6, Feature 4 Complete — Answer Feedback Loop

**Built:**
- `backend/app/models.py`: Added `feedback` (ENUM), `ground_truth` (TEXT), and `flagged_for_review` (BOOLEAN) to the `Query` model.
- `backend/fix_schema.py`: Ran migrations for the new `Query` columns.
- `backend/app/chat/schemas.py`: Added `FeedbackRequest` and `FeedbackResponse`.
- `backend/app/chat/router.py`: Implemented `POST /chat/{query_id}/feedback` endpoint. 
    - Positive feedback saves the model's answer as `ground_truth`.
    - Negative feedback sets `flagged_for_review=True` and optionally saves a user-provided `correct_answer` as `ground_truth`.
- `backend/app/admin/router.py`: Added `GET /admin/feedback-stats` to calculate positive/negative counts, positive rate, and ground truth collection count.
- `frontend/src/pages/EvalDashboard.jsx`: Added a new "Answer Feedback" summary card at the top, showing real-time feedback metrics and indicating if RAGAS evaluation is using real ground truths.
- `frontend/src/pages/Chat.jsx`: Built the `FeedbackBar` component inline. It attaches below assistant messages and provides Thumbs Up / Thumbs Down buttons, plus a collapsible textarea to capture the correct answer on negative feedback.
- `frontend/src/pages/Chat.module.css`: Added CSS for the `FeedbackBar` components.

**Decisions made:**
- Kept the feedback UI within `Chat.jsx` to closely tie it to the streaming message loop.
- RAGAS evaluations (currently using dummy ground truths in `service.py`) will automatically leverage the new `ground_truth` column in a future update (when we tie the evaluation script strictly to this data). For now, the loop collects the data.

**Blockers hit:**
- None.

**Next:** Feature 5 — Semantic Query Cache.

---

## [2026-05-13] Phase 6, Feature 5 Complete — Semantic Query Cache

**Built:**
- `backend/app/cache/semantic_cache.py` (new): In-process singleton `SemanticCache`. Per-workspace LRU deque (max 200 entries). Cosine similarity lookup with 0.92 threshold and 30-minute TTL. `invalidate_workspace()` clears stale entries when documents change.
- `backend/app/cache/__init__.py` (new): Package init.
- `backend/app/chat/service.py`: Both `process_query` and `process_query_stream` now embed the query once upfront, check the cache before retrieval, and store the answer after generation. Cache-hit answers are streamed word-by-word for consistent UX. Only non-"unanswered" responses are cached. Yields `{"query_id": ..., "cache_hit": ...}` metadata at end of stream.
- `backend/app/chat/router.py`: `POST /chat/stream` now reads metadata dict events from the generator and emits them as `data: {"meta": ...}` SSE events before `[DONE]`.
- `backend/app/documents/service.py`: `process_document_async()` calls `semantic_cache.invalidate_workspace()` on successful document processing, preventing stale cache answers after a new upload.
- `backend/app/models.py`: Added `cache_hit` BOOLEAN column to `Query`.
- `backend/fix_schema.py`: Added `cache_hit` migration (verified).
- `frontend/src/hooks/useStreamingChat.js`: Parses `data.meta` SSE events and patches the last assistant message with `queryId` and `cacheHit`. History loading attaches `queryId: item.id` to assistant messages.
- `frontend/src/pages/Chat.jsx`: Renders `⚡ Cached` badge on cache-hit messages. Passes `msg.queryId` to `FeedbackBar`.
- `frontend/src/pages/Chat.module.css`: Added `.messageColumn` wrapper and `.cacheBadge` styles.

**Decisions made:**
- Cache is in-process memory (not Redis) — intentionally simple; clears on restart = safe after rollbacks/redeploys.
- 0.92 similarity threshold is tight by design; semantically similar but differently-phrased questions get fresh answers.
- Only successful answers cached (no "I don't have information" responses).

**Blockers hit:**
- None.

**Next:** Feature 6 — Batch Multi-File Upload.
