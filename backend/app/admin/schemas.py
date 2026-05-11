from pydantic import BaseModel, EmailStr
from typing import List

class InviteRequest(BaseModel):
    email: EmailStr

class StatsResponse(BaseModel):
    total_docs: int
    total_queries: int
    unanswered_count: int
    top_questions: List[str]
