from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from fastapi import HTTPException, status
from app.models import User, Workspace
from app.auth.schemas import RegisterRequest, LoginRequest
from app.auth.jwt import create_access_token, verify_token

import bcrypt

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))

def get_password_hash(password: str) -> str:
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

async def register_user(db: AsyncSession, request: RegisterRequest) -> tuple[User, Workspace]:
    # Check if user exists
    result = await db.execute(select(User).where(User.email == request.email))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email already registered")
        
    if len(request.password) < 8:
        raise HTTPException(status_code=422, detail="Password must be at least 8 characters")
    
    # Create workspace
    workspace = Workspace(name=request.workspace_name)
    db.add(workspace)
    await db.flush()  # Gets the workspace ID
    
    # Create user
    hashed_password = get_password_hash(request.password)
    user = User(
        email=request.email,
        password_hash=hashed_password,
        workspace_id=workspace.id,
        role="admin"  # First user in workspace gets admin
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    
    return user, workspace

async def authenticate_user(db: AsyncSession, request: LoginRequest) -> User:
    result = await db.execute(select(User).where(User.email == request.email))
    user = result.scalar_one_or_none()
    
    if not user or not verify_password(request.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user

async def refresh_access_token(db: AsyncSession, refresh_token: str) -> str:
    user_id = verify_token(refresh_token)
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
        
    return create_access_token(data={"sub": user.id, "workspace_id": user.workspace_id})
