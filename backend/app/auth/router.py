from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models import User
from app.auth import schemas, service, jwt

router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/register", response_model=schemas.TokenResponse, status_code=201)
async def register(request: schemas.RegisterRequest, db: AsyncSession = Depends(get_db)):
    """Register a new user and workspace."""
    user, workspace = await service.register_user(db, request)
    
    access_token = jwt.create_access_token(
        data={"sub": user.id, "workspace_id": user.workspace_id}
    )
    refresh_token = jwt.create_refresh_token(
        data={"sub": user.id}
    )
    
    return schemas.TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user_id=user.id,
        workspace_id=workspace.id
    )

@router.post("/login", response_model=schemas.TokenResponse)
async def login(request: schemas.LoginRequest, db: AsyncSession = Depends(get_db)):
    """Login and receive access and refresh tokens."""
    user = await service.authenticate_user(db, request)
    
    access_token = jwt.create_access_token(
        data={"sub": user.id, "workspace_id": user.workspace_id}
    )
    refresh_token = jwt.create_refresh_token(
        data={"sub": user.id}
    )
    
    return schemas.TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user_id=user.id,
        workspace_id=user.workspace_id
    )

@router.post("/refresh", response_model=schemas.TokenResponse)
async def refresh(request: schemas.RefreshRequest, db: AsyncSession = Depends(get_db)):
    """Exchange a valid refresh token for a new access token."""
    access_token = await service.refresh_access_token(db, request.refresh_token)
    user_id = jwt.verify_token(request.refresh_token)
    
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one()
    
    return schemas.TokenResponse(
        access_token=access_token,
        refresh_token=request.refresh_token,
        user_id=user.id,
        workspace_id=user.workspace_id
    )
