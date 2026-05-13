import json
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from typing import List
from app.database import get_db
from app.models import User, Query, ChatSession
from app.auth.jwt import get_current_user
from app.chat import schemas, service
from app.limiter import limiter

router = APIRouter(prefix="/chat", tags=["chat"])

@router.post("/query", response_model=schemas.ChatResponse)
@limiter.limit("15/minute")
async def chat_query(
    request: Request,
    body: schemas.ChatRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Non-streaming query (rate-limited: 15/minute)."""
    return await service.process_query(db, body, current_user.workspace_id, current_user.id)

@router.get("/history", response_model=List[schemas.ChatHistoryItem])
async def get_history(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get chat history for current user in current workspace."""
    result = await db.execute(
        select(Query)
        .where(Query.workspace_id == current_user.workspace_id)
        .where(Query.user_id == current_user.id)
        .where(Query.is_deleted == False)
        .order_by(Query.created_at.asc())
    )
    queries = result.scalars().all()
    return queries

@router.delete("/session/{session_id}")
async def delete_session(
    session_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Soft delete a chat session."""
    # Mark ChatSession as deleted
    await db.execute(
        update(ChatSession)
        .where(ChatSession.id == session_id)
        .where(ChatSession.workspace_id == current_user.workspace_id)
        .values(is_deleted=True)
    )
    # Mark all queries in the session as deleted
    await db.execute(
        update(Query)
        .where(Query.session_id == session_id)
        .where(Query.workspace_id == current_user.workspace_id)
        .values(is_deleted=True)
    )
    return {"status": "success"}

@router.post("/stream")
@limiter.limit("15/minute")
async def chat_stream(
    request: Request,
    body: schemas.ChatRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Streaming SSE query (rate-limited: 15/minute)."""
    async def event_generator():
        meta: dict = {}
        async for event in service.process_query_stream(
            db, body, current_user.workspace_id, current_user.id
        ):
            if isinstance(event, dict):   # metadata packet
                meta = event
            else:
                yield f"data: {json.dumps({'token': event})}\n\n"
        # Emit metadata (query_id, cache_hit) before DONE so client can capture it
        if meta:
            yield f"data: {json.dumps({'meta': meta})}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")

@router.get("/{id}/trace", response_model=schemas.TraceResponse)
async def get_trace(
    id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Full retrieval trace for a single query."""
    return await service.get_query_trace(db, id, current_user.workspace_id)

@router.post("/{query_id}/feedback", response_model=schemas.FeedbackResponse)
async def submit_feedback(
    query_id: str,
    body: schemas.FeedbackRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> schemas.FeedbackResponse:
    """
    Submit thumbs-up / thumbs-down feedback on an answer.

    Positive feedback: stores answer_text as ground_truth for RAGAS evaluation.
    Negative feedback: flags for review, optionally stores user-supplied correct answer.
    """
    result = await db.execute(
        select(Query)
        .where(Query.id == query_id)
        .where(Query.workspace_id == current_user.workspace_id)
    )
    query = result.scalar_one_or_none()
    if not query:
        raise HTTPException(status_code=404, detail="Query not found")

    try:
        if body.rating == "positive":
            query.feedback = "positive"
            # The model's own answer becomes real ground truth
            query.ground_truth = query.answer_text
        else:
            query.feedback = "negative"
            query.flagged_for_review = True
            if body.correct_answer and body.correct_answer.strip():
                query.ground_truth = body.correct_answer.strip()

        await db.commit()
        return schemas.FeedbackResponse(
            query_id=query_id,
            rating=body.rating,
            message="Thank you for your feedback!" if body.rating == "positive"
                    else "Noted — we'll use this to improve.",
        )
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to save feedback: {e}")


@router.get("/{query_id}/citations", response_model=schemas.CitationsResponse)
async def get_citations(
    query_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> schemas.CitationsResponse:
    """
    Returns deduplicated citation sources for a given query.
    Groups retrieved chunks by document, collects unique page numbers,
    and surfaces the highest-scoring excerpt per document.
    """
    from app.models import Document
    from sqlalchemy import select

    result = await db.execute(
        select(Query).where(Query.id == query_id, Query.workspace_id == current_user.workspace_id)
    )
    query = result.scalar_one_or_none()
    if not query:
        raise HTTPException(status_code=404, detail="Query not found")

    chunks = query.retrieved_chunk_ids or []  # list of dicts saved in _save_trace
    if not chunks:
        return schemas.CitationsResponse(query_id=query_id, query_text=query.query_text, sources=[])

    # Group chunks by document_id
    doc_map: dict[str, dict] = {}
    for chunk in chunks:
        doc_id = chunk.get("document_id")
        if not doc_id:
            continue
        if doc_id not in doc_map:
            doc_map[doc_id] = {"pages": set(), "best_chunk": None, "best_score": -1}
        page = chunk.get("page_number")
        if page is not None:
            doc_map[doc_id]["pages"].add(page)
        score = chunk.get("rerank_score") or chunk.get("fused_score") or 0
        if score > doc_map[doc_id]["best_score"]:
            doc_map[doc_id]["best_score"] = score
            doc_map[doc_id]["best_chunk"] = chunk

    # Look up filenames in bulk
    doc_ids = list(doc_map.keys())
    docs_result = await db.execute(
        select(Document).where(Document.id.in_(doc_ids))
    )
    docs = {d.id: d.filename for d in docs_result.scalars().all()}

    sources = []
    for doc_id, data in doc_map.items():
        best = data["best_chunk"]
        sources.append(schemas.CitationSource(
            document_id=doc_id,
            filename=docs.get(doc_id, "Unknown document"),
            pages=sorted(data["pages"]),
            excerpt=(best.get("text", "")[:300] + "…") if best and best.get("text") else "",
        ))

    # Sort by descending best score
    sources.sort(key=lambda s: doc_map[s.document_id]["best_score"], reverse=True)

    return schemas.CitationsResponse(
        query_id=query_id,
        query_text=query.query_text,
        sources=sources,
    )
