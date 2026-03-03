"""
Bridge Point — Commission Ledger Model
Tracks all financial transactions. Immutable once created.
"""

from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship

from app.database import Base


class CommissionLedger(Base):
    __tablename__ = "commission_ledger"

    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(Integer, ForeignKey("jobs.id"), nullable=False, unique=True, index=True)
    employer_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    labor_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # ─── Financial Fields (all in paise) ────────────────
    budget_paise = Column(Integer, nullable=False)
    employer_commission_paise = Column(Integer, nullable=False)
    employer_total_paise = Column(Integer, nullable=False)
    labor_commission_paise = Column(Integer, nullable=False)
    labor_receives_paise = Column(Integer, nullable=False)
    platform_earning_paise = Column(Integer, nullable=False)

    # ─── Payment Details ────────────────────────────────
    payment_method = Column(String(20), nullable=True)  # "upi" or "cash"
    payment_status = Column(String(20), default="pending")  # pending, completed
    upi_reference = Column(String(100), nullable=True)  # UPI Transaction Reference (UTI)

    # ─── Timestamps ──────────────────────────────────────
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # ─── Relationships ───────────────────────────────────
    job = relationship("Job", back_populates="commission_ledger")
    employer = relationship("User", foreign_keys=[employer_id])
    labor = relationship("User", foreign_keys=[labor_id])
