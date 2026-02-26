"""
Bridge Point — User Schemas
Pydantic models for request/response validation.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field


# ─── Registration ───────────────────────────────────────
class UserRegister(BaseModel):
    email: EmailStr
    phone: str = Field(..., min_length=10, max_length=15, pattern=r"^\+?[0-9]{10,15}$")
    password: str = Field(..., min_length=8)
    full_name: str = Field(..., min_length=2, max_length=255)
    role: str = Field(default="both", pattern=r"^(employer|labor|both)$")  # Deprecated: unified mode

    # Labor-specific (required if role == labor)
    labor_category: Optional[str] = None
    skills: Optional[list[str]] = None
    city: str = "Chennai"
    bio: Optional[str] = None


# ─── Login ──────────────────────────────────────────────
class UserLogin(BaseModel):
    email: EmailStr
    password: str


# ─── Token Response ────────────────────────────────────
class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: "UserResponse"


# ─── Profile Update ────────────────────────────────────
class UserProfileUpdate(BaseModel):
    full_name: Optional[str] = None
    phone: Optional[str] = None
    labor_category: Optional[str] = None
    skills: Optional[list[str]] = None
    city: Optional[str] = None
    bio: Optional[str] = None


# ─── Response ──────────────────────────────────────────
class UserResponse(BaseModel):
    id: int
    email: str
    phone: str
    full_name: str
    roles: list[str]
    role: str  # Computed for backward compat
    is_admin: bool = False
    labor_category: Optional[str] = None
    skills: Optional[list[str]] = None
    city: Optional[str] = None
    bio: Optional[str] = None
    phone_verified: bool
    email_verified: bool
    created_at: datetime

    model_config = {"from_attributes": True}


# Forward reference resolution
TokenResponse.model_rebuild()
