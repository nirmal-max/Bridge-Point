"""
Bridge Point — PrivateRequest Model
Employer sends a private work request to a favorited labor.
"""

from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Index
from sqlalchemy.orm import relationship

from app.database import Base


class PrivateRequest(Base):
    __tablename__ = "private_requests"

    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(Integer, ForeignKey("jobs.id"), nullable=False, index=True)
    employer_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    labor_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    # pending | accepted | denied
    status = Column(String(20), nullable=False, default="pending")
    message = Column(Text, nullable=True)  # Optional note from employer

    # ─── Timestamps ──────────────────────────────────────
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    responded_at = Column(DateTime, nullable=True)

    # ─── Relationships ───────────────────────────────────
    job = relationship("Job", backref="private_requests")
    employer = relationship("User", foreign_keys=[employer_id])
    labor = relationship("User", foreign_keys=[labor_id])

    # ─── Indexes ─────────────────────────────────────────
    __table_args__ = (
        Index("ix_private_requests_labor_status", "labor_id", "status"),
    )
