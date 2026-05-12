import json
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
from app.database import get_db
from app.models import User, Query
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
        .order_by(Query.created_at.asc())
    )
    queries = result.scalars().all()
    return queries

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
