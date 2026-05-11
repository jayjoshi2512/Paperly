import time
import json
import uuid
import logging
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import HTTPException

from app.models import Query, UnansweredQuery
from app.chat.schemas import ChatRequest
from app.rag.retrieval import hybrid_search, RetrievedChunk
from app.rag.reranker import reranker, RerankedChunk
from app.rag.generator import generator

logger = logging.getLogger(__name__)

async def _save_trace(
    db: AsyncSession,
    workspace_id: str,
    user_id: str,
    query_text: str,
    answer_text: str,
    chunks: list[RerankedChunk],
    latency_ms: int
) -> Query:
    was_answered = True
    if "I don't have information about this" in answer_text or "I don't have information" in answer_text:
        was_answered = False

    chunk_data = []
    for c in chunks:
        chunk_data.append({
            "chunk_id": c.chunk_id,
            "document_id": c.document_id,
            "page_number": c.page_number,
            "dense_score": c.dense_score,
            "sparse_score": c.sparse_score,
            "fused_score": c.fused_score,
            "rerank_score": c.rerank_score,
            "text": c.text
        })

    db_query = Query(
        workspace_id=workspace_id,
        user_id=user_id,
        query_text=query_text,
        answer_text=answer_text,
        retrieved_chunk_ids=chunk_data,
        was_answered=was_answered,
        latency_ms=latency_ms
    )
    db.add(db_query)
    
    if not was_answered:
        unanswered = UnansweredQuery(
            workspace_id=workspace_id,
            query_text=query_text
        )
        db.add(unanswered)

    await db.commit()
    await db.refresh(db_query)
    return db_query

async def process_query(db: AsyncSession, request: ChatRequest, workspace_id: str, user_id: str) -> dict:
    start_time = time.time()
    
    retrieved_chunks = await hybrid_search(request.query, workspace_id, top_k=20)
    reranked_chunks = reranker.rerank(request.query, retrieved_chunks, top_n=5)
    answer = await generator.generate(request.query, reranked_chunks)
    
    latency_ms = int((time.time() - start_time) * 1000)
    db_query = await _save_trace(db, workspace_id, user_id, request.query, answer, reranked_chunks, latency_ms)
    
    return {
        "query_id": db_query.id,
        "answer": answer
    }

async def process_query_stream(db: AsyncSession, request: ChatRequest, workspace_id: str, user_id: str) -> AsyncGenerator[str, None]:
    start_time = time.time()
    
    retrieved_chunks = await hybrid_search(request.query, workspace_id, top_k=20)
    reranked_chunks = reranker.rerank(request.query, retrieved_chunks, top_n=5)
    
    full_answer = []
    
    async for token in generator.stream_generate(request.query, reranked_chunks):
        full_answer.append(token)
        yield token

    answer_text = "".join(full_answer)
    latency_ms = int((time.time() - start_time) * 1000)
    
    await _save_trace(db, workspace_id, user_id, request.query, answer_text, reranked_chunks, latency_ms)

async def get_query_trace(db: AsyncSession, query_id: str, workspace_id: str) -> dict:
    result = await db.execute(select(Query).where(Query.id == query_id, Query.workspace_id == workspace_id))
    db_query = result.scalar_one_or_none()
    if not db_query:
        raise HTTPException(status_code=404, detail="Query not found")
        
    return {
        "query_id": db_query.id,
        "query_text": db_query.query_text,
        "answer_text": db_query.answer_text,
        "latency_ms": db_query.latency_ms,
        "was_answered": db_query.was_answered,
        "chunks": db_query.retrieved_chunk_ids or []
    }
