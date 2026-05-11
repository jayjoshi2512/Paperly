from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.database import get_db
from app.models import User, Document, Query, UnansweredQuery, RoleEnum
from app.auth.jwt import get_current_user
from app.auth import schemas as auth_schemas
from app.admin import schemas

router = APIRouter(prefix="/admin", tags=["admin"])

def require_admin(current_user: User = Depends(get_current_user)):
    if current_user.role != RoleEnum.admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user

@router.get("/users", response_model=list[auth_schemas.UserResponse])
async def list_users(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    result = await db.execute(select(User).where(User.workspace_id == current_user.workspace_id))
    return result.scalars().all()

@router.post("/invite")
async def invite_user(
    request: schemas.InviteRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    result = await db.execute(select(User).where(User.email == request.email))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="User already exists")
        
    from app.auth.service import get_password_hash
    hashed_password = get_password_hash("changeme123")
    
    new_user = User(
        email=request.email,
        password_hash=hashed_password,
        workspace_id=current_user.workspace_id,
        role=RoleEnum.member
    )
    db.add(new_user)
    await db.commit()
    
    return {"message": "User invited", "default_password": "changeme123"}

@router.get("/stats", response_model=schemas.StatsResponse)
async def get_stats(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user) 
):
    workspace_id = current_user.workspace_id
    
    doc_res = await db.execute(select(func.count(Document.id)).where(Document.workspace_id == workspace_id))
    total_docs = doc_res.scalar() or 0
    
    query_res = await db.execute(select(func.count(Query.id)).where(Query.workspace_id == workspace_id))
    total_queries = query_res.scalar() or 0
    
    un_res = await db.execute(select(func.count(UnansweredQuery.id)).where(UnansweredQuery.workspace_id == workspace_id))
    unanswered_count = un_res.scalar() or 0
    
    top_q_res = await db.execute(
        select(Query.query_text)
        .where(Query.workspace_id == workspace_id)
        .group_by(Query.query_text)
        .order_by(func.count(Query.id).desc())
        .limit(5)
    )
    top_questions = top_q_res.scalars().all()
    
    return schemas.StatsResponse(
        total_docs=total_docs,
        total_queries=total_queries,
        unanswered_count=unanswered_count,
        top_questions=list(top_questions)
    )
