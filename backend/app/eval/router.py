from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List

from app.database import get_db
from app.models import User, Query
from app.auth.jwt import get_current_user
from app.eval import ragas_eval, gap_detector

router = APIRouter(prefix="/eval", tags=["evaluation"])

@router.post("/run")
async def run_eval(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(
        select(Query.id)
        .where(Query.workspace_id == current_user.workspace_id)
        .order_by(Query.created_at.desc())
        .limit(10)
    )
    query_ids = result.scalars().all()
    if not query_ids:
        raise HTTPException(status_code=400, detail="No queries to evaluate")
        
    return await ragas_eval.run_ragas_evaluation(db, list(query_ids), current_user.workspace_id)

@router.get("/scores")
async def get_scores(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(
        select(Query)
        .where(Query.workspace_id == current_user.workspace_id)
        .where(Query.faithfulness_score.isnot(None))
    )
    queries = result.scalars().all()
    
    return [
        {
            "query_id": q.id,
            "faithfulness": q.faithfulness_score,
            "relevancy": q.relevancy_score,
            "query_text": q.query_text
        } for q in queries
    ]

@router.get("/gaps", response_model=List[gap_detector.GapCluster])
async def get_gaps(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return await gap_detector.detect_knowledge_gaps(db, current_user.workspace_id)
