import json
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from typing import List
from app.database import get_db
from app.models import User, Query, ChatSession
from app.auth.jwt import get_current_user
from app.chat import schemas, service

router = APIRouter(prefix="/chat", tags=["chat"])

@router.post("/query", response_model=schemas.ChatResponse)
async def chat_query(
    request: schemas.ChatRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Non-streaming query."""
    return await service.process_query(db, request, current_user.workspace_id, current_user.id)

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
async def chat_stream(
    request: schemas.ChatRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Streaming SSE query."""
    async def event_generator():
        async for token in service.process_query_stream(db, request, current_user.workspace_id, current_user.id):
            yield f"data: {json.dumps({'token': token})}\n\n"
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
