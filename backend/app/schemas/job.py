"""
Bridge Point — Job Schemas
Pydantic models for job posting and response.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, model_validator


# ─── Job Creation ───────────────────────────────────────
class JobCreate(BaseModel):
    title: str = Field(..., min_length=3, max_length=255)
    category: str = Field(..., pattern=r"^(household|industry|professional)$")
    work_description: str
    role_description: str = Field(..., min_length=10)
    required_skill: Optional[str] = None
    city: str = Field(default="Chennai", max_length=100)
    location_type: str = Field(..., pattern=r"^(online|offline)$")
    address: Optional[str] = None
    date_of_task: datetime
    time_span: str = Field(..., pattern=r"^(few_hours|single_day|week)$")
    organization_type: str = Field(..., pattern=r"^(individual|organization)$")
    budget: float = Field(..., gt=0, description="Job budget in ₹")

    @model_validator(mode="after")
    def validate_address_for_offline(self):
        if self.location_type == "offline" and not self.address:
            raise ValueError("Address is mandatory for offline jobs")
        return self


# ─── Status Transition ─────────────────────────────────
class JobStatusUpdate(BaseModel):
    status: str


# ─── Job Response ──────────────────────────────────────
class JobResponse(BaseModel):
    id: int
    employer_id: int
    title: str
    category: str
    work_description: str
    role_description: str
    required_skill: Optional[str] = None
    city: str
    location_type: str
    address: Optional[str] = None
    date_of_task: datetime
    time_span: str
    organization_type: str
    status: str
    allotted_labor_id: Optional[int] = None
    allotted_labor_name: Optional[str] = None
    accepted_at: Optional[datetime] = None
    payment_method: Optional[str] = None
    created_at: datetime

    # ─── Financial (visible to relevant parties) ────────
    budget: float = 0
    employer_commission: float = 0
    employer_total: float = 0
    labor_commission: float = 0
    labor_receives: float = 0

    # ─── Platform Custody Payment ────────────────────────
    platform_commission: float = 0
    worker_payout: float = 0
    payment_status: Optional[str] = None
    payment_sent_at: Optional[datetime] = None
    payout_released_at: Optional[datetime] = None
    cashfree_order_id: Optional[str] = None

    employer_name: Optional[str] = None

    model_config = {"from_attributes": True}


# ─── Job List Response ─────────────────────────────────
class JobListResponse(BaseModel):
    jobs: list[JobResponse]
    total: int
    page: int
    per_page: int
