"""
Bridge Point — Call Log Model
Tracks in-app voice calls between users.
"""

from datetime import datetime, timezone
from sqlalchemy import (
    Column, Integer, String, DateTime, ForeignKey, Enum as SAEnum
)
from sqlalchemy.orm import relationship
import enum

from app.database import Base


class CallStatus(str, enum.Enum):
    RINGING = "ringing"
    ACTIVE = "active"
    COMPLETED = "completed"
    MISSED = "missed"
    REJECTED = "rejected"
    FAILED = "failed"


class CallLog(Base):
    __tablename__ = "call_logs"

    id = Column(Integer, primary_key=True, index=True)
    caller_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    callee_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    job_id = Column(Integer, ForeignKey("jobs.id"), nullable=True, index=True)
    status = Column(SAEnum(CallStatus), default=CallStatus.RINGING, nullable=False)
    started_at = Column(DateTime, nullable=True)  # When call was answered
    ended_at = Column(DateTime, nullable=True)     # When call ended
    duration_seconds = Column(Integer, default=0)

    # Timestamps
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    caller = relationship("User", foreign_keys=[caller_id])
    callee = relationship("User", foreign_keys=[callee_id])
    job = relationship("Job", foreign_keys=[job_id])
