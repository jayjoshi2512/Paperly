# Paperly — API Reference

## Health
### GET /health
**Description:** API health check endpoint.
**Auth required:** No
**Response 200:**
```json
{
  "status": "ok"
}
```

## Auth

### POST /auth/register
**Description:** Register a new user and workspace. First user becomes the admin of the workspace.
**Auth required:** No
**Request body:**
```json
{
  "email": "user@example.com",
  "password": "minimum8chars",
  "workspace_name": "Acme Corp"
}
```
**Response 201:**
```json
{
  "access_token": "jwt...",
  "refresh_token": "jwt...",
  "token_type": "bearer",
  "user_id": "uuid",
  "workspace_id": "uuid"
}
```
**Errors:** 400 email already exists, 422 validation error (e.g. password < 8 chars).

### POST /auth/login
**Description:** Login with email and password to receive access and refresh tokens.
**Auth required:** No
**Request body:**
```json
{
  "email": "user@example.com",
  "password": "minimum8chars"
}
```
**Response 200:**
```json
{
  "access_token": "jwt...",
  "refresh_token": "jwt...",
  "token_type": "bearer",
  "user_id": "uuid",
  "workspace_id": "uuid"
}
```
**Errors:** 401 incorrect email or password.

### POST /auth/refresh
**Description:** Exchange a valid refresh token for a new access token.
**Auth required:** No
**Request body:**
```json
{
  "refresh_token": "jwt..."
}
```
**Response 200:**
```json
{
  "access_token": "new_jwt...",
  "refresh_token": "jwt...",
  "token_type": "bearer",
  "user_id": "uuid",
  "workspace_id": "uuid"
}
```
**Errors:** 401 invalid refresh token or user not found.

## Documents

### POST /docs/upload
**Description:** Upload a PDF document for processing and embedding.
**Auth required:** Yes (Bearer token)
**Request body:** `multipart/form-data` with `file` (PDF) and `strategy` (fixed, recursive, semantic).
**Response 201:** `DocumentResponse`
**Errors:** 400 invalid file type.

### GET /docs/
**Description:** List all documents in the workspace.
**Auth required:** Yes
**Response 200:** List of `DocumentResponse`

### GET /docs/{id}
**Description:** Get document details by ID.
**Auth required:** Yes
**Response 200:** `DocumentResponse`
**Errors:** 404 not found.

### DELETE /docs/{id}
**Description:** Delete document and remove all vectors from Qdrant.
**Auth required:** Yes
**Response 204:** No content
**Errors:** 404 not found.

### GET /docs/{id}/diff
**Description:** Show chunk-level diff vs previous version.
**Auth required:** Yes
**Response 200:** `DiffResponse`
**Errors:** 404 no diff available.

## Chat

### POST /chat/query
**Description:** Non-streaming RAG query endpoint. Orchestrates hybrid search, reranking, and generation.
**Auth required:** Yes
**Request body:** `{"query": "What is our leave policy?"}`
**Response 200:** `ChatResponse` with `query_id` and `answer`.

### POST /chat/stream
**Description:** Streaming SSE RAG query.
**Auth required:** Yes
**Request body:** `{"query": "What is our leave policy?"}`
**Response 200:** Server-Sent Events stream.

### GET /chat/{id}/trace
**Description:** Get full retrieval trace and audit log for a query.
**Auth required:** Yes
**Response 200:** `TraceResponse` with scores, chunks, latency, and whether it was answered.

## Evaluation

### POST /eval/run
**Description:** Run RAGAS evaluation on recent queries.
**Auth required:** Yes
**Response 200:** Aggregate and per-query scores.

### GET /eval/scores
**Description:** Fetch evaluation scores.
**Auth required:** Yes
**Response 200:** List of scores.

### GET /eval/gaps
**Description:** Fetch knowledge gap clusters.
**Auth required:** Yes
**Response 200:** List of `GapCluster`

## Admin

### GET /admin/users
**Description:** List all users in the workspace.
**Auth required:** Yes (Admin role)
**Response 200:** List of users.

### POST /admin/invite
**Description:** Create a new user account without email flow.
**Auth required:** Yes (Admin role)
**Request body:** `{"email": "..."}`
**Response 200:** Invite success message with default password.

### GET /admin/stats
**Description:** Usage stats for the workspace.
**Auth required:** Yes
**Response 200:** `StatsResponse` (totals and top questions).
