from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from app.models import DocStatusEnum, ChunkingStrategyEnum

class DocumentResponse(BaseModel):
    id: str
    workspace_id: str
    filename: str
    file_size_bytes: Optional[int]
    page_count: Optional[int]
    chunking_strategy: ChunkingStrategyEnum
    chunk_count: Optional[int]
    status: DocStatusEnum
    progress_pct: int = 0
    progress_message: Optional[str] = None
    version: int
    created_at: datetime

    model_config = {
        "from_attributes": True
    }

class DiffResponse(BaseModel):
    added: List[str]
    removed: List[str]
    modified: List[str]
    unchanged_count: int

class DocumentUploadResponse(BaseModel):
    document_id: str
    filename: str
    status: str    # always "processing" immediately after upload
    message: str

class DocumentStatusResponse(BaseModel):
    document_id: str
    status: str          # processing | ready | failed
    progress_pct: int    # 0-100
    progress_message: Optional[str] = None
    chunk_count: Optional[int] = None

class BatchUploadResponse(BaseModel):
    accepted: List[DocumentUploadResponse]
    rejected: List[dict]
    total_accepted: int
    total_rejected: int
