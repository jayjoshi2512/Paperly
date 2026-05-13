import time
import json
import uuid
import logging
import asyncio
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import HTTPException

from app.models import Query, UnansweredQuery, ChatSession
from app.chat.schemas import ChatRequest
from app.rag.retrieval import hybrid_search, RetrievedChunk
from app.rag.reranker import reranker, RerankedChunk
from app.rag.generator import generator
from app.chat.memory import run_memory_cleanup
from app.rag.embedder import embedder
from app.vector_store.qdrant_client import qdrant_db
from app.cache.semantic_cache import semantic_cache

logger = logging.getLogger(__name__)

async def _save_trace(
    db: AsyncSession,
    workspace_id: str,
    user_id: str,
    query_text: str,
    answer_text: str,
    chunks: list[RerankedChunk],
    latency_ms: int,
    session_id: str = None,
    cache_hit: bool = False,
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
        session_id=session_id,
        query_text=query_text,
        answer_text=answer_text,
        retrieved_chunk_ids=chunk_data,
        was_answered=was_answered,
        cache_hit=cache_hit,
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
    chat_history = []
    level3_summary = None
    level2_context = []

    # Embed query first (needed for both cache lookup and Level-2 memory)
    query_emb = await embedder.embed_text(request.query)

    # ── Semantic cache lookup ──────────────────────────────────────
    cache_result = semantic_cache.lookup(workspace_id, query_emb)
    if cache_result:
        cached_answer, cached_query_id, sim = cache_result
        latency_ms = int((time.time() - start_time) * 1000)
        db_query = await _save_trace(
            db, workspace_id, user_id,
            request.query, cached_answer, [],
            latency_ms, request.session_id, cache_hit=True
        )
        return {"query_id": db_query.id, "answer": cached_answer, "cache_hit": True}
    # ─────────────────────────────────────────────────────────────

    if request.session_id:
        # Level 3 Summary
        session_res = await db.execute(select(ChatSession).where(ChatSession.id == request.session_id))
        chat_session = session_res.scalar_one_or_none()
        if chat_session and chat_session.summary_state:
            level3_summary = chat_session.summary_state

        # Level 2 Semantic
        level2_results = await qdrant_db.search_chat_memory(query_emb, request.session_id, top_k=2)
        level2_context = [r.get("text") for r in level2_results if r.get("text")]

        # Level 1 Buffer
        result = await db.execute(
            select(Query)
            .where(Query.session_id == request.session_id)
            .order_by(Query.created_at.asc())
        )
        old_queries = result.scalars().all()
        for oq in old_queries:
            chat_history.append({"role": "user", "content": oq.query_text})
            if oq.answer_text:
                chat_history.append({"role": "assistant", "content": oq.answer_text})

    chat_history = chat_history[-6:]  # Last 3 turns
    standalone_query = await generator.condense_query(request.query, chat_history)

    retrieved_chunks = await hybrid_search(standalone_query, workspace_id, top_k=20)
    reranked_chunks = reranker.rerank(standalone_query, retrieved_chunks, top_n=5)

    # Inject Level 2 and Level 3
    if level3_summary:
        chat_history.insert(0, {"role": "system", "content": f"Long-term Session Summary: {level3_summary}"})
    if level2_context:
        past_str = "\n---\n".join(level2_context)
        chat_history.insert(0, {"role": "system", "content": f"Recalled Past Conversations:\n{past_str}"})

    answer = await generator.generate(request.query, reranked_chunks, chat_history)

    latency_ms = int((time.time() - start_time) * 1000)
    db_query = await _save_trace(db, workspace_id, user_id, request.query, answer, reranked_chunks, latency_ms, request.session_id)

    # Store in semantic cache (only cache answered queries)
    if "I don't have information" not in answer:
        semantic_cache.store(workspace_id, query_emb, answer, db_query.id)

    if request.session_id:
        asyncio.create_task(run_memory_cleanup(request.session_id, db_query.id, workspace_id, user_id))

    return {"query_id": db_query.id, "answer": answer, "cache_hit": False}

async def process_query_stream(db: AsyncSession, request: ChatRequest, workspace_id: str, user_id: str) -> AsyncGenerator[str, None]:
    start_time = time.time()
    chat_history = []
    level3_summary = None
    level2_context = []

    # Embed query first
    query_emb = await embedder.embed_text(request.query)

    # ── Semantic cache lookup ──────────────────────────────────────
    cache_result = semantic_cache.lookup(workspace_id, query_emb)
    if cache_result:
        cached_answer, cached_query_id, sim = cache_result
        # Stream the cached answer token by token for consistent UX
        for word in cached_answer.split(" "):
            yield word + " "
        latency_ms = int((time.time() - start_time) * 1000)
        try:
            await _save_trace(
                db, workspace_id, user_id,
                request.query, cached_answer, [],
                latency_ms, request.session_id, cache_hit=True
            )
        except Exception as e:
            logger.warning(f"Failed to save cache-hit trace (non-fatal): {e}")
        return
    # ─────────────────────────────────────────────────────────────

    if request.session_id:
        # Level 3 Summary
        session_res = await db.execute(select(ChatSession).where(ChatSession.id == request.session_id))
        chat_session = session_res.scalar_one_or_none()
        if chat_session and chat_session.summary_state:
            level3_summary = chat_session.summary_state

        # Level 2 Semantic
        level2_results = await qdrant_db.search_chat_memory(query_emb, request.session_id, top_k=2)
        level2_context = [r.get("text") for r in level2_results if r.get("text")]

        # Level 1 Buffer
        result = await db.execute(
            select(Query)
            .where(Query.session_id == request.session_id)
            .order_by(Query.created_at.asc())
        )
        old_queries = result.scalars().all()
        for oq in old_queries:
            chat_history.append({"role": "user", "content": oq.query_text})
            if oq.answer_text:
                chat_history.append({"role": "assistant", "content": oq.answer_text})

    chat_history = chat_history[-6:]  # Last 3 turns
    standalone_query = await generator.condense_query(request.query, chat_history)

    retrieved_chunks = await hybrid_search(standalone_query, workspace_id, top_k=20)
    reranked_chunks = reranker.rerank(standalone_query, retrieved_chunks, top_n=5)

    # Inject Level 2 and Level 3
    if level3_summary:
        chat_history.insert(0, {"role": "system", "content": f"Long-term Session Summary: {level3_summary}"})
    if level2_context:
        past_str = "\n---\n".join(level2_context)
        chat_history.insert(0, {"role": "system", "content": f"Recalled Past Conversations:\n{past_str}"})

    full_answer = []

    async for token in generator.stream_generate(request.query, reranked_chunks, chat_history):
        full_answer.append(token)
        yield token

    answer_text = "".join(full_answer)
    latency_ms = int((time.time() - start_time) * 1000)

    try:
        db_query = await _save_trace(db, workspace_id, user_id, request.query, answer_text, reranked_chunks, latency_ms, request.session_id)
        # Store in semantic cache (only cache answered queries)
        if "I don't have information" not in answer_text:
            semantic_cache.store(workspace_id, query_emb, answer_text, db_query.id)
        if request.session_id:
            asyncio.create_task(run_memory_cleanup(request.session_id, db_query.id, workspace_id, user_id))
        # Yield metadata packet for the SSE router to forward to the client
        yield {"query_id": db_query.id, "cache_hit": False}
    except Exception as e:
        logger.warning(f"Failed to save query trace (non-fatal): {e}")
        await db.rollback()

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
