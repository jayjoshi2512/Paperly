from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class ChatRequest(BaseModel):
    query: str
    session_id: Optional[str] = None

class ChatResponse(BaseModel):
    query_id: str
    answer: str

class RetrievedChunkInfo(BaseModel):
    chunk_id: str
    document_id: str
    text: str
    page_number: int
    dense_score: float
    sparse_score: float
    fused_score: float
    rerank_score: Optional[float] = None

class TraceResponse(BaseModel):
    query_id: str
    query_text: str
    answer_text: str
    latency_ms: int
    was_answered: bool
    chunks: List[RetrievedChunkInfo]

class ChatHistoryItem(BaseModel):
    id: str
    session_id: Optional[str]
    query_text: str
    answer_text: Optional[str]
    created_at: datetime
