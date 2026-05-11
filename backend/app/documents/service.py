import uuid
import logging
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from qdrant_client.http import models as qmodels
from fastapi import UploadFile, HTTPException

from app.models import Document, Chunk, DocumentDiff, DocStatusEnum
from app.documents.extractor import extract_text_from_pdf, ExtractionError
from app.documents.diff import compute_chunk_diff, DiffResult
from app.vector_store.qdrant_client import qdrant_db
from app.rag.bm25_index import bm25_manager
from app.rag.embedder import embedder

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

async def upload_document(
    db: AsyncSession, 
    file: UploadFile, 
    workspace_id: str, 
    user_id: str, 
    strategy: str
) -> Document:
    # 1. Create document record as processing
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
        version=new_version
    )
    db.add(doc)
    await db.commit()
    await db.refresh(doc)

    try:
        # 2. Extract text
        pages = extract_text_from_pdf(file_bytes)
        doc.page_count = len(pages)
        full_text = "\n\n".join(p.text for p in pages)

        # 3. Chunk
        chunker = await get_chunker(strategy)
        raw_chunks = chunker.chunk(full_text)
        doc.chunk_count = len(raw_chunks)

        if len(raw_chunks) == 0:
            doc.status = DocStatusEnum.ready
            await db.commit()
            return doc

        # 4. Embed
        embeddings = await embedder.embed_batch(raw_chunks)

        # 5. Insert chunks to MySQL and Qdrant
        qdrant_points = []
        bm25_corpus = []
        new_chunk_texts = []
        
        for i, (text, emb) in enumerate(zip(raw_chunks, embeddings)):
            chunk_id = str(uuid.uuid4())
            qdrant_point_id = str(uuid.uuid4())

            # MySQL
            db_chunk = Chunk(
                id=chunk_id,
                document_id=doc.id,
                qdrant_point_id=qdrant_point_id,
                chunk_index=i,
                token_count=0,
                chunk_text=text
            )
            db.add(db_chunk)
            new_chunk_texts.append(text)

            # Qdrant point
            qdrant_points.append(
                qmodels.PointStruct(
                    id=qdrant_point_id,
                    vector=emb,
                    payload={
                        "chunk_id": chunk_id,
                        "document_id": doc.id,
                        "workspace_id": workspace_id,
                        "text": text,
                        "page_number": 1 
                    }
                )
            )

            # BM25 corpus
            bm25_corpus.append((chunk_id, text))

        await db.commit()

        # Update Qdrant
        await qdrant_db.upsert(qdrant_points)

        # Update BM25
        bm25_manager.add_document(workspace_id, bm25_corpus)

        # 6. Diff if new version
        if prev_doc:
            result = await db.execute(
                select(Chunk.chunk_text)
                .where(Chunk.document_id == prev_doc.id)
                .order_by(Chunk.chunk_index.asc())
            )
            old_chunks = result.scalars().all()
            diff_res = compute_chunk_diff(list(old_chunks), new_chunk_texts)
            
            doc_diff = DocumentDiff(
                document_id=doc.id,
                from_version=prev_doc.version,
                to_version=doc.version,
                diff_summary={
                    "added": diff_res.added,
                    "removed": diff_res.removed,
                    "modified": diff_res.modified,
                    "unchanged_count": diff_res.unchanged_count
                }
            )
            db.add(doc_diff)
            await db.commit()

        doc.status = DocStatusEnum.ready
        await db.commit()

    except Exception as e:
        logger.error(f"Error processing document {doc.id}: {str(e)}")
        doc.status = DocStatusEnum.failed
        await db.commit()
        raise e

    return doc

async def delete_document(db: AsyncSession, document_id: str, workspace_id: str):
    result = await db.execute(select(Document).where(Document.id == document_id, Document.workspace_id == workspace_id))
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

    diff_res = await db.execute(select(DocumentDiff).where(DocumentDiff.document_id == document_id))
    diff = diff_res.scalar_one_or_none()
    
    if not diff:
        raise HTTPException(status_code=404, detail="No diff available for this document (might be version 1)")
        
    summary = diff.diff_summary
    return DiffResult(
        added=summary.get("added", []),
        removed=summary.get("removed", []),
        modified=summary.get("modified", []),
        unchanged_count=summary.get("unchanged_count", 0)
    )
