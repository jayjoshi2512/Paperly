"""Document service: record creation, async background processing, and status polling."""
from __future__ import annotations

import uuid
import logging
from typing import List

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from qdrant_client.http import models as qmodels
from fastapi import UploadFile, HTTPException

from app.database import AsyncSessionLocal
from app.models import Document, Chunk, DocumentDiff, DocStatusEnum
from app.documents.extractor import extract_text, ExtractionError
from app.documents.diff import compute_chunk_diff, DiffResult
from app.documents.schemas import DocumentStatusResponse
from app.vector_store.qdrant_client import qdrant_db
from app.rag.bm25_index import bm25_manager
from app.rag.embedder import embedder
from app.cache.semantic_cache import semantic_cache

logger = logging.getLogger(__name__)


async def get_chunker(strategy: str):
    if strategy == "fixed":
        from app.documents.chunkers.fixed import FixedSizeChunker
        return FixedSizeChunker()
    elif strategy == "semantic":
        from app.documents.chunkers.semantic import SemanticChunker
        return SemanticChunker()
    else:
        from app.documents.chunkers.recursive import RecursiveChunker
        return RecursiveChunker()


# ──────────────────────────────────────────────────────────────────────────────
# Step 1: create record immediately (sync part, returns 202 to caller)
# ──────────────────────────────────────────────────────────────────────────────

async def create_document_record(
    db: AsyncSession,
    file: UploadFile,
    workspace_id: str,
    user_id: str,
    strategy: str,
) -> tuple[str, bytes]:
    """
    Insert a documents row with status='processing' and return (document_id, file_bytes).
    Does NOT process the document — that happens in process_document_async().
    """
    result = await db.execute(
        select(Document)
        .where(Document.workspace_id == workspace_id)
        .where(Document.filename == file.filename)
        .order_by(Document.version.desc())
    )
    prev_doc = result.scalars().first()
    new_version = (prev_doc.version + 1) if prev_doc else 1

    file_bytes = await file.read()

    doc = Document(
        workspace_id=workspace_id,
        uploaded_by=user_id,
        filename=file.filename,
        file_size_bytes=len(file_bytes),
        chunking_strategy=strategy,
        status=DocStatusEnum.processing,
        progress_pct=0,
        progress_message="Queued for processing...",
        version=new_version,
    )
    db.add(doc)
    await db.commit()
    await db.refresh(doc)
    return doc.id, file_bytes


# ──────────────────────────────────────────────────────────────────────────────
# Helper: update progress columns
# ──────────────────────────────────────────────────────────────────────────────

async def _update_progress(
    session: AsyncSession,
    document_id: str,
    pct: int,
    message: str,
    status: DocStatusEnum = DocStatusEnum.processing,
) -> None:
    result = await session.execute(
        select(Document).where(Document.id == document_id)
    )
    doc = result.scalar_one_or_none()
    if doc:
        doc.progress_pct = pct
        doc.progress_message = message
        doc.status = status
        await session.commit()


# ──────────────────────────────────────────────────────────────────────────────
# Step 2: background task — full pipeline with progress updates
# ──────────────────────────────────────────────────────────────────────────────

async def process_document_async(
    document_id: str,
    file_bytes: bytes,
    filename: str,
    strategy: str,
    workspace_id: str,
) -> None:
    """
    Background task: extract → chunk → embed → upsert → BM25 update.
    Updates progress_pct and progress_message at each step.
    Opens its own DB session (cannot share the request-scoped one).
    """
    async with AsyncSessionLocal() as session:
        try:
            # Fetch the document and any previous version for diff
            result = await session.execute(
                select(Document).where(Document.id == document_id)
            )
            doc = result.scalar_one_or_none()
            if not doc:
                logger.error(f"process_document_async: document {document_id} not found")
                return

            # Find previous version for diff
            prev_result = await session.execute(
                select(Document)
                .where(Document.workspace_id == workspace_id)
                .where(Document.filename == filename)
                .where(Document.id != document_id)
                .order_by(Document.version.desc())
            )
            prev_doc = prev_result.scalars().first()

            # Step 1: Extract text
            await _update_progress(session, document_id, 10, "Extracting text...")
            try:
                pages = extract_text(file_bytes, filename)
            except ExtractionError as e:
                await _update_progress(session, document_id, 0, str(e), DocStatusEnum.failed)
                return

            doc.page_count = len(pages)
            full_text = "\n\n".join(p.text for p in pages)
            await session.commit()

            # Step 2: Chunk
            await _update_progress(session, document_id, 30, "Chunking document...")
            chunker = await get_chunker(strategy)
            raw_chunks: List[str] = chunker.chunk(full_text)
            doc.chunk_count = len(raw_chunks)
            await session.commit()

            if len(raw_chunks) == 0:
                await _update_progress(session, document_id, 100, "Ready (empty document)", DocStatusEnum.ready)
                return

            # Step 3: Embed
            await _update_progress(session, document_id, 50, "Generating embeddings...")
            embeddings = await embedder.embed_batch(raw_chunks)

            # Step 4: Upsert chunks
            await _update_progress(session, document_id, 70, "Indexing vectors...")
            qdrant_points = []
            bm25_corpus = []
            new_chunk_texts = []

            for i, (text, emb) in enumerate(zip(raw_chunks, embeddings)):
                chunk_id = str(uuid.uuid4())
                qdrant_point_id = str(uuid.uuid4())

                db_chunk = Chunk(
                    id=chunk_id,
                    document_id=document_id,
                    qdrant_point_id=qdrant_point_id,
                    chunk_index=i,
                    token_count=0,
                    chunk_text=text,
                )
                session.add(db_chunk)
                new_chunk_texts.append(text)

                qdrant_points.append(
                    qmodels.PointStruct(
                        id=qdrant_point_id,
                        vector=emb,
                        payload={
                            "chunk_id": chunk_id,
                            "document_id": document_id,
                            "workspace_id": workspace_id,
                            "text": text,
                            "page_number": 1,
                        },
                    )
                )
                bm25_corpus.append((chunk_id, text))

            await session.commit()
            await qdrant_db.upsert(qdrant_points)

            # Step 5: Update BM25 index
            await _update_progress(session, document_id, 85, "Updating search index...")
            bm25_manager.add_document(workspace_id, bm25_corpus)

            # Step 6: Compute diff if re-upload
            if prev_doc:
                chunk_result = await session.execute(
                    select(Chunk.chunk_text)
                    .where(Chunk.document_id == prev_doc.id)
                    .order_by(Chunk.chunk_index.asc())
                )
                old_chunks = chunk_result.scalars().all()
                diff_res = compute_chunk_diff(list(old_chunks), new_chunk_texts)
                doc_diff = DocumentDiff(
                    document_id=document_id,
                    from_version=prev_doc.version,
                    to_version=doc.version,
                    diff_summary={
                        "added": diff_res.added,
                        "removed": diff_res.removed,
                        "modified": diff_res.modified,
                        "unchanged_count": diff_res.unchanged_count,
                    },
                )
                session.add(doc_diff)
                await session.commit()

            # Done
            await _update_progress(session, document_id, 100, "Ready", DocStatusEnum.ready)
            # Invalidate semantic cache so next query picks up fresh document context
            semantic_cache.invalidate_workspace(workspace_id)
            logger.info(f"Document {document_id} processed successfully ({len(raw_chunks)} chunks).")

        except Exception as e:
            logger.error(f"process_document_async failed for {document_id}: {e}", exc_info=True)
            try:
                await _update_progress(
                    session, document_id, 0, f"Processing failed: {str(e)[:200]}", DocStatusEnum.failed
                )
            except Exception:
                pass  # Don't let error-reporting itself crash


# ──────────────────────────────────────────────────────────────────────────────
# Status polling
# ──────────────────────────────────────────────────────────────────────────────

async def get_document_status(
    document_id: str,
    workspace_id: str,
    session: AsyncSession,
) -> DocumentStatusResponse:
    """Return processing status for a document. Enforces workspace isolation."""
    result = await session.execute(
        select(Document).where(Document.id == document_id)
    )
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    if doc.workspace_id != workspace_id:
        raise HTTPException(status_code=403, detail="Access denied")
    return DocumentStatusResponse(
        document_id=doc.id,
        status=doc.status.value,
        progress_pct=doc.progress_pct,
        progress_message=doc.progress_message,
        chunk_count=doc.chunk_count,
    )


# ──────────────────────────────────────────────────────────────────────────────
# Kept for backwards compat (used by delete and diff endpoints)
# ──────────────────────────────────────────────────────────────────────────────

async def delete_document(db: AsyncSession, document_id: str, workspace_id: str):
    result = await db.execute(
        select(Document).where(Document.id == document_id, Document.workspace_id == workspace_id)
    )
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    chunk_res = await db.execute(select(Chunk.id).where(Chunk.document_id == document_id))
    chunk_ids = chunk_res.scalars().all()

    await db.delete(doc)
    await db.commit()

    await qdrant_db.delete_by_document_id(document_id)

    if chunk_ids:
        bm25_manager.remove_document(workspace_id, list(chunk_ids))


async def get_document_diff(db: AsyncSession, document_id: str, workspace_id: str) -> DiffResult:
    result = await db.execute(
        select(Document).where(Document.id == document_id, Document.workspace_id == workspace_id)
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Document not found")

    diff_res = await db.execute(
        select(DocumentDiff).where(DocumentDiff.document_id == document_id)
    )
    diff = diff_res.scalar_one_or_none()

    if not diff:
        raise HTTPException(
            status_code=404,
            detail="No diff available for this document (might be version 1)",
        )

    summary = diff.diff_summary
    return DiffResult(
        added=summary.get("added", []),
        removed=summary.get("removed", []),
        modified=summary.get("modified", []),
        unchanged_count=summary.get("unchanged_count", 0),
    )


# Legacy synchronous upload kept for any internal callers that haven't migrated
async def upload_document(
    db: AsyncSession,
    file: UploadFile,
    workspace_id: str,
    user_id: str,
    strategy: str,
) -> Document:
    """
    Synchronous upload — kept for backwards compatibility.
    New callers should use create_document_record() + process_document_async().
    """
    document_id, file_bytes = await create_document_record(db, file, workspace_id, user_id, strategy)
    await process_document_async(document_id, file_bytes, file.filename, strategy, workspace_id)
    result = await db.execute(select(Document).where(Document.id == document_id))
    return result.scalar_one()
