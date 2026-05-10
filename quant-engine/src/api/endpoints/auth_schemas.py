from pydantic import BaseModel, EmailStr
from typing import List, Optional

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

class UserCreate(BaseModel):
    email: EmailStr
    password: str

class UserResponse(BaseModel):
    user_id: str
    email: str
    role: str

class APIKeyResponse(BaseModel):
    key_id: str
    raw_key: Optional[str] = None  # Only returned ONCE upon creation
    key_prefix: str
    status: str

class SignalPayload(BaseModel):
    ticker: str
    signal_direction: str
    conviction_score: float
    timestamp: str
