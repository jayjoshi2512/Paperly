# Paperly — Tasks

## Phase 1: Foundation
- [x] Create project folder structure
- [x] Write PLANNING.md
- [x] Write TASKS.md
- [x] Write SCHEMA.md
- [x] Write .env.example
- [x] Write .gitignore
- [x] Write requirements.txt
- [x] Write backend/app/config.py
- [x] Write backend/app/database.py
- [x] Write backend/app/models.py
- [x] Write backend/app/auth/jwt.py
- [x] Write backend/app/auth/schemas.py
- [x] Write backend/app/auth/service.py
- [x] Write backend/app/auth/router.py
- [x] Write backend/app/main.py
- [x] Write backend/Dockerfile and backend/.dockerignore
- [x] Write docker-compose.yml
- [x] Write nginx.conf
- [x] Update TASKS.md (check off Phase 1 tasks)
- [x] Update PROGRESS.md
- [x] Update API.md
- [x] Update DECISIONS.md

## Phase 2: RAG Core
- [x] Write backend/app/vector_store/qdrant_client.py
- [x] Write backend/app/rag/embedder.py
- [x] Write backend/app/rag/bm25_index.py
- [x] Write backend/app/documents/chunkers/base.py
- [x] Write backend/app/documents/chunkers/fixed.py
- [x] Write backend/app/documents/chunkers/recursive.py
- [x] Write backend/app/documents/chunkers/semantic.py
- [x] Write backend/app/documents/extractor.py
- [x] Write backend/app/documents/diff.py
- [x] Write backend/app/documents/schemas.py and backend/app/documents/service.py
- [x] Write backend/app/documents/router.py
- [x] Write backend/app/rag/retrieval.py
- [x] Write backend/app/rag/reranker.py
- [x] Write backend/app/rag/generator.py
- [x] Update main.py lifespan for BM25
- [x] Update TASKS.md, PROGRESS.md, API.md, DECISIONS.md

## Phase 3: Differentiated Features
- [x] Write backend/app/chat/schemas.py, service.py, router.py
- [x] Write backend/app/eval/ragas_eval.py
- [x] Write backend/app/eval/gap_detector.py
- [x] Write backend/app/eval/router.py
- [x] Write backend/app/admin/schemas.py and router.py
- [x] Update TASKS.md, PROGRESS.md, API.md, DECISIONS.md

## Phase 4: Frontend
- [ ] Scaffold Vite + React + TailwindCSS project
- [ ] Write frontend/src/api/client.js
- [ ] Write frontend/src/hooks/useAuth.js
- [ ] Write frontend/src/hooks/useDocuments.js
- [ ] Write frontend/src/hooks/useStreamingChat.js
- [ ] Write frontend/src/pages/Login.jsx
- [ ] Write frontend/src/pages/Documents.jsx
- [ ] Write frontend/src/pages/Chat.jsx
- [ ] Write frontend/src/pages/EvalDashboard.jsx
- [ ] Write frontend/src/pages/Dashboard.jsx
- [ ] Write frontend/src/components/ChatMessage.jsx, SourcePanel.jsx, DocUploader.jsx, ScoreCard.jsx, GapAlert.jsx
- [ ] Write frontend/Dockerfile
- [ ] Update TASKS.md, PROGRESS.md

## Phase 5: Deployment & Final Docs
- [ ] Finalize docker-compose.yml
- [ ] Finalize nginx.conf
- [ ] Write deployment runbook in PROGRESS.md
- [ ] Write README.md
- [ ] Final update to tracking files
