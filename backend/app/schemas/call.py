"""
Bridge Point — Call Schemas
Pydantic models for call-related request/response validation.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class CallLogResponse(BaseModel):
    id: int
    caller_id: int
    callee_id: int
    caller_name: Optional[str] = None
    callee_name: Optional[str] = None
    job_id: Optional[int] = None
    job_title: Optional[str] = None
    status: str
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    duration_seconds: int = 0
    created_at: datetime

    model_config = {"from_attributes": True}


class CallHistoryResponse(BaseModel):
    calls: list[CallLogResponse]
    total: int
    page: int
    per_page: int
