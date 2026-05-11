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
