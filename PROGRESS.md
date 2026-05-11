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
