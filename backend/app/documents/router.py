"""Documents router: upload (202 async), status polling, list, get, delete, diff."""

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, Request, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List

from app.database import get_db
from app.models import User, Document
from app.auth.jwt import get_current_user
from app.documents import schemas, service
from app.limiter import limiter

router = APIRouter(prefix="/docs", tags=["documents"])


@router.post("/upload", response_model=schemas.DocumentUploadResponse, status_code=202)
@limiter.limit("10/minute")
async def upload_document(
    request: Request,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    strategy: str = Form("recursive"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> schemas.DocumentUploadResponse:
    """
    Upload a PDF or DOCX document.
    Returns 202 Accepted immediately; processing runs in the background.
    Poll GET /docs/{document_id}/status for progress.
    Rate-limited: 10 uploads per minute per IP.
    """
    allowed = (".pdf", ".docx", ".doc")
    if not any(file.filename.lower().endswith(ext) for ext in allowed):
        raise HTTPException(
            status_code=400,
            detail="Only PDF and DOCX files are supported",
        )

    try:
        document_id, file_bytes = await service.create_document_record(
            db=db,
            file=file,
            workspace_id=current_user.workspace_id,
            user_id=current_user.id,
            strategy=strategy,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create document record: {e}")

    background_tasks.add_task(
        service.process_document_async,
        document_id,
        file_bytes,
        file.filename,
        strategy,
        current_user.workspace_id,
    )

    return schemas.DocumentUploadResponse(
        document_id=document_id,
        filename=file.filename,
        status="processing",
        message="Document accepted and is being processed. Poll /docs/{document_id}/status for updates.",
    )


@router.post("/upload/batch", response_model=schemas.BatchUploadResponse, status_code=202)
@limiter.limit("5/minute")
async def upload_batch(
    request: Request,
    background_tasks: BackgroundTasks,
    files: List[UploadFile] = File(...),
    strategy: str = Form("recursive"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> schemas.BatchUploadResponse:
    """
    Upload up to 10 PDF or DOCX files in a single request.
    Returns 202 with a list of accepted documents immediately.
    Each document can be polled individually via GET /docs/{id}/status.
    Rate-limited: 5 batch requests per minute per IP.
    """
    allowed = (".pdf", ".docx", ".doc")

    if len(files) > 10:
        raise HTTPException(status_code=400, detail="Maximum 10 files per batch upload.")

    accepted: List[schemas.DocumentUploadResponse] = []
    rejected: List[dict] = []

    for file in files:
        if not any(file.filename.lower().endswith(ext) for ext in allowed):
            rejected.append({"filename": file.filename, "reason": "Unsupported file type"})
            continue

        try:
            document_id, file_bytes = await service.create_document_record(
                db=db,
                file=file,
                workspace_id=current_user.workspace_id,
                user_id=current_user.id,
                strategy=strategy,
            )
            background_tasks.add_task(
                service.process_document_async,
                document_id,
                file_bytes,
                file.filename,
                strategy,
                current_user.workspace_id,
            )
            accepted.append(schemas.DocumentUploadResponse(
                document_id=document_id,
                filename=file.filename,
                status="processing",
                message="Accepted",
            ))
        except Exception as e:
            rejected.append({"filename": file.filename, "reason": str(e)})

    return schemas.BatchUploadResponse(
        accepted=accepted,
        rejected=rejected,
        total_accepted=len(accepted),
        total_rejected=len(rejected),
    )


@router.get("/", response_model=List[schemas.DocumentResponse])
async def list_documents(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all documents in the current workspace."""
    result = await db.execute(
        select(Document)
        .where(Document.workspace_id == current_user.workspace_id)
        .order_by(Document.created_at.desc())
    )
    return result.scalars().all()


@router.get("/{document_id}/status", response_model=schemas.DocumentStatusResponse)
async def get_document_status(
    document_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> schemas.DocumentStatusResponse:
    """Poll real-time processing status for a document (progress_pct 0-100)."""
    try:
        return await service.get_document_status(document_id, current_user.workspace_id, db)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{id}", response_model=schemas.DocumentResponse)
async def get_document(
    id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a single document by ID."""
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
    current_user: User = Depends(get_current_user),
):
    """Permanently delete a document and all its chunks."""
    await service.delete_document(db, id, current_user.workspace_id)


@router.get("/{id}/diff", response_model=schemas.DiffResponse)
async def get_diff(
    id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return the chunk-level diff for a re-uploaded document vs its previous version."""
    return await service.get_document_diff(db, id, current_user.workspace_id)
