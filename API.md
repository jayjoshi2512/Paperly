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
