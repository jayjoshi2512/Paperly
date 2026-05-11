# Paperly — Architecture Decision Records

## ADR-001: MySQL over PostgreSQL
**Date:** 2026-05-11
**Status:** Accepted
**Context:** MySQL 8.0 is already running on the VPS. Setting up PostgreSQL would require a Docker container, consuming extra memory.
**Decision:** Use MySQL 8.0 with aiomysql driver via SQLAlchemy async.
**Consequences:** Cannot use pgvector for embedding storage in MySQL. Vectors go to Qdrant. MySQL handles all relational data.

## ADR-002: BM25 in-memory index
**Date:** 2026-05-11
**Status:** Accepted
**Context:** rank-bm25 builds the index in memory. On restart, index must be rebuilt from MySQL chunk_text column.
**Decision:** On FastAPI startup (lifespan), load all chunk texts from MySQL and rebuild BM25 index. Add a background task to update index on new document upload.
**Consequences:** Startup time increases with corpus size. Acceptable for portfolio scale.

## ADR-003: BM25/Dense Metadata Resolution
**Date:** 2026-05-11
**Status:** Accepted
**Context:** Hybrid search combines chunks from Qdrant (which caches payload) and BM25 (which only stores chunk ID).
**Decision:** Fetch missing chunk metadata from MySQL using an `IN()` query for chunks found only via BM25.
**Consequences:** Small additional latency for hybrid search, but avoids storing duplicate payloads in BM25 index memory.

## ADR-004: Document Diffing using SequenceMatcher
**Date:** 2026-05-11
**Status:** Accepted
**Context:** Need to determine added/removed/modified chunks when a document is re-uploaded.
**Decision:** Extract all old chunks from DB and use Python's built-in `difflib.SequenceMatcher` to compare with newly generated chunks before inserting to DB.
**Consequences:** CPU-bound diffing on ingest, which scales perfectly fine for typical corporate PDFs. Avoids complex database-level triggers or separate differ services.
