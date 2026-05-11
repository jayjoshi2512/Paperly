from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime
from app.models import RoleEnum

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    workspace_name: str

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class RefreshRequest(BaseModel):
    refresh_token: str

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user_id: str
    workspace_id: str

class UserResponse(BaseModel):
    id: str
    workspace_id: str
    email: EmailStr
    role: RoleEnum
    created_at: datetime

    model_config = {
        "from_attributes": True
    }
