from pydantic import BaseModel
from typing import List, Literal, Optional
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

class FeedbackRequest(BaseModel):
    rating: Literal["positive", "negative"]
    correct_answer: Optional[str] = None  # Optional, for negative feedback

class FeedbackResponse(BaseModel):
    query_id: str
    rating: str
    message: str

class CitationSource(BaseModel):
    document_id: str
    filename: str
    pages: List[int]           # deduplicated, sorted page numbers cited
    excerpt: str               # text of the highest-scoring chunk for this doc

class CitationsResponse(BaseModel):
    query_id: str
    query_text: str
    sources: List[CitationSource]
