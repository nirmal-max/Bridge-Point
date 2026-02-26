"""
Bridge Point — Favorite Model
Employer saves labor for rebooking later.
"""

from datetime import datetime, timezone
from sqlalchemy import Column, Integer, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship

from app.database import Base


class Favorite(Base):
    __tablename__ = "favorites"

    id = Column(Integer, primary_key=True, index=True)
    employer_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    labor_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    # ─── Timestamps ──────────────────────────────────────
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # ─── Constraints ─────────────────────────────────────
    __table_args__ = (
        UniqueConstraint("employer_id", "labor_id", name="uq_employer_labor_favorite"),
    )

    # ─── Relationships ───────────────────────────────────
    employer = relationship("User", back_populates="favorites", foreign_keys=[employer_id])
    labor = relationship("User", foreign_keys=[labor_id])
