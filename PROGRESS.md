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
