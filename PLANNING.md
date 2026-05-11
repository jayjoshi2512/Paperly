# Paperly — Planning

## Architecture Overview
Paperly is a multi-tenant, internal knowledge assistant enabling teams to upload company PDFs and chat with them using a production-grade RAG pipeline.
- **Frontend**: React + Vite + TailwindCSS. Single Page Application providing UI for uploading documents, chatting, and viewing evaluation metrics.
- **Backend**: FastAPI (Python 3.11). Provides async endpoints for auth, document ingestion, RAG, and admin stats.
- **LLM & Embeddings**: Gemini 1.5 Flash and `text-embedding-004` via `google-generativeai`. Fast, generous free tier.
- **Vector DB**: Qdrant (self-hosted). Used for dense vector retrieval.
- **Sparse Search**: BM25 via `rank-bm25` built in-memory, rebuilt on startup from MySQL.
- **Database**: MySQL 8.0 (on VPS host, outside Docker) for relational metadata, users, document tracking, and audit trail.
- **Observability**: Langfuse (self-hosted) for tracing LLM calls.
- **Deployment**: Docker Compose orchestration, Nginx reverse proxy.

## Technology Decisions
- **FastAPI**: Native async support, excellent developer experience, perfectly suited for SSE and AI workloads.
- **MySQL 8.0**: Pre-existing on the VPS. Relies on SQLAlchemy async (`aiomysql`) to avoid blocking.
- **Gemini 1.5 Flash & text-embedding-004**: High performance, large context window, zero cost during development.
- **Qdrant**: Powerful, easily containerized vector database that pairs well with hybrid search.
- **Cohere Rerank**: Implements a cross-encoder to massively boost precision on top-k retrieval.
- **RAGAS**: Ground-truth-free evaluation to quantify and prove retrieval/generation quality.

## Phase Breakdown
### Phase 1: Foundation
- Goal: Working project skeleton with auth, database, and Docker setup. No AI code yet.
- Deliverable: API with `/auth/register`, `/auth/login`, and `/health` endpoints. Dockerized backend connecting to external MySQL.

### Phase 2: RAG Core
- Goal: Full document ingestion and retrieval pipeline working end-to-end.
- Deliverable: PDF extraction, three chunking strategies, hybrid search (BM25+Qdrant), reranking, and generation with retry logic.

### Phase 3: Differentiated Features
- Goal: The features that separate Paperly from tutorial projects.
- Deliverable: Complete query processing with audit trace logging, RAGAS evaluation, and k-means knowledge gap detection.

### Phase 4: Frontend
- Goal: A clean, functional React frontend that demonstrates every backend feature.
- Deliverable: UI for chat with SSE, document upload, and evaluation/dashboard metrics.

### Phase 5: Deployment
- Goal: Running on VPS, README ready for a hiring manager.
- Deliverable: Docker-compose and Nginx fully wired up, final runbook, and professional portfolio README.

## Known Risks
- Risk: MySQL host.docker.internal mapping on Linux.
  - Mitigation: Use `extra_hosts: host.docker.internal:host-gateway` in docker-compose.
- Risk: BM25 index memory usage scaling with corpus size.
  - Mitigation: Acceptable for portfolio scale. Rebuilt during lifespan startup.
- Risk: Rate limiting from Gemini/Cohere free tiers.
  - Mitigation: Wrap all external calls with `@retry` from `tenacity` (exponential backoff).

## Open Questions
- [ ] Which chunking strategy to default to for ingestion?
- [ ] What is the ideal k for k-means gap detection in this specific domain?
