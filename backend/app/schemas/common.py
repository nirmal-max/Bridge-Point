"""
Bridge Point — Application, Review, Favorite Schemas
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


# ─── Application ────────────────────────────────────────
class ApplicationCreate(BaseModel):
    job_id: int
    cover_note: Optional[str] = None


class ApplicationResponse(BaseModel):
    id: int
    job_id: int
    labor_id: int
    status: str
    cover_note: Optional[str] = None
    created_at: datetime
    labor_name: Optional[str] = None
    labor_phone: Optional[str] = None
    labor_skills: Optional[list[str]] = None

    model_config = {"from_attributes": True}


# ─── Review ─────────────────────────────────────────────
class ReviewCreate(BaseModel):
    job_id: int
    reviewee_id: int
    rating: int = Field(..., ge=1, le=5)
    comment: Optional[str] = None


class ReviewResponse(BaseModel):
    id: int
    job_id: int
    reviewer_id: int
    reviewee_id: int
    rating: int
    comment: Optional[str] = None
    created_at: datetime
    reviewer_name: Optional[str] = None

    model_config = {"from_attributes": True}


# ─── Favorite ──────────────────────────────────────────
class FavoriteCreate(BaseModel):
    labor_id: int


class FavoriteResponse(BaseModel):
    id: int
    employer_id: int
    labor_id: int
    labor_name: Optional[str] = None
    labor_skills: Optional[list[str]] = None
    labor_phone: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


# ─── Commission ────────────────────────────────────────
class CommissionResponse(BaseModel):
    budget: float
    employer_commission: float
    employer_total: float
    labor_commission: float
    labor_receives: float
    platform_earning: float
    currency: str = "INR"


# ─── Private Request (Direct Rehire) ──────────────────
class PrivateRequestCreate(BaseModel):
    job_id: int
    labor_id: int
    message: Optional[str] = None


class PrivateRequestRespond(BaseModel):
    action: str = Field(..., pattern=r"^(accept|deny)$")
    updated_description: Optional[str] = None  # For repost on deny


class PrivateRequestResponse(BaseModel):
    id: int
    job_id: int
    employer_id: int
    labor_id: int
    status: str
    message: Optional[str] = None
    created_at: datetime
    responded_at: Optional[datetime] = None
    employer_name: Optional[str] = None
    labor_name: Optional[str] = None
    job_title: Optional[str] = None

    model_config = {"from_attributes": True}

