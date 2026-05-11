from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List

from app.database import get_db
from app.models import User, Document
from app.auth.jwt import get_current_user
from app.documents import schemas, service

router = APIRouter(prefix="/docs", tags=["documents"])

@router.post("/upload", response_model=schemas.DocumentResponse, status_code=201)
async def upload_document(
    file: UploadFile = File(...),
    strategy: str = Form("recursive"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Upload a PDF document. File size limit enforced by Nginx (50MB).
    """
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")
        
    doc = await service.upload_document(
        db=db,
        file=file,
        workspace_id=current_user.workspace_id,
        user_id=current_user.id,
        strategy=strategy
    )
    return doc

@router.get("/", response_model=List[schemas.DocumentResponse])
async def list_documents(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(
        select(Document)
        .where(Document.workspace_id == current_user.workspace_id)
        .order_by(Document.created_at.desc())
    )
    return result.scalars().all()

@router.get("/{id}", response_model=schemas.DocumentResponse)
async def get_document(
    id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(
        select(Document).where(Document.id == id, Document.workspace_id == current_user.workspace_id)
    )
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return doc

@router.delete("/{id}", status_code=204)
async def delete_document(
    id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    await service.delete_document(db, id, current_user.workspace_id)

@router.get("/{id}/diff", response_model=schemas.DiffResponse)
async def get_diff(
    id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return await service.get_document_diff(db, id, current_user.workspace_id)
