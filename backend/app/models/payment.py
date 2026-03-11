"""
Bridge Point — Payment Model
Tracks Cashfree payment lifecycle for each job.
One-to-one relationship with jobs table.
"""

from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Index
from sqlalchemy.orm import relationship

from app.database import Base


class Payment(Base):
    __tablename__ = "payments"

    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(Integer, ForeignKey("jobs.id"), nullable=False, unique=True, index=True)
    employer_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    worker_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    # ─── Cashfree Identifiers ───────────────────────────
    cashfree_order_id = Column(String(100), nullable=True, unique=True, index=True)
    cashfree_payment_id = Column(String(100), nullable=True)
    cashfree_payout_id = Column(String(100), nullable=True)

    # ─── Financial Fields (all in paise) ────────────────
    amount_total_paise = Column(Integer, nullable=False)          # What employer paid (= budget)
    platform_commission_paise = Column(Integer, nullable=False)   # Platform earning (3%)
    worker_payout_paise = Column(Integer, nullable=False)         # What worker receives (97%)

    # ─── Status ─────────────────────────────────────────
    # pending → paid → payout_initiated → payout_completed → failed
    payment_status = Column(String(30), nullable=False, default="pending")

    # ─── Timestamps ─────────────────────────────────────
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    verified_at = Column(DateTime, nullable=True)
    transferred_at = Column(DateTime, nullable=True)

    # ─── Relationships ──────────────────────────────────
    job = relationship("Job", back_populates="payment")
    employer = relationship("User", foreign_keys=[employer_id])
    worker = relationship("User", foreign_keys=[worker_id])

    # ─── Indexes ────────────────────────────────────────
    __table_args__ = (
        Index("ix_payments_status", "payment_status"),
        Index("ix_payments_employer_id", "employer_id"),
    )
