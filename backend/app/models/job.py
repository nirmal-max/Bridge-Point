"""
Bridge Point — Job Model
Represents a micro-job posting with all document-required fields.
Platform Custody Payment columns included.
"""

from datetime import datetime, timezone
from sqlalchemy import (
    Column, Integer, String, Text, Float, DateTime, ForeignKey,
    Enum as SAEnum, Index
)
from sqlalchemy.orm import relationship
import enum

from app.database import Base


class JobCategory(str, enum.Enum):
    HOUSEHOLD = "household"
    INDUSTRY = "industry"
    PROFESSIONAL = "professional"


class LocationType(str, enum.Enum):
    ONLINE = "online"
    OFFLINE = "offline"


class TimeSpan(str, enum.Enum):
    FEW_HOURS = "few_hours"
    SINGLE_DAY = "single_day"
    WEEK = "week"


class OrganizationType(str, enum.Enum):
    INDIVIDUAL = "individual"
    ORGANIZATION = "organization"


class WorkDescription(str, enum.Enum):
    """Predefined work type categories."""
    EMERGENCY_REPLACEMENT_STAFF = "emergency_replacement_staff"
    FOUR_HOUR_SHIFT_HELPER = "four_hour_shift_helper"
    ONE_DAY_EVENT_ASSISTANT = "one_day_event_assistant"
    PEAK_HOUR_STORE_STAFF = "peak_hour_store_staff"
    ON_DEMAND_LOCAL_WORKER = "on_demand_local_worker"
    DAILY_WAGE_CONSTRUCTION_HELPER = "daily_wage_construction_helper"
    TEMPORARY_DELIVERY_RIDER = "temporary_delivery_rider"
    WAREHOUSE_LOADING_ASSISTANT = "warehouse_loading_assistant"
    ACTING_DRIVER_SHORT_TERM = "acting_driver_short_term"
    RECURRING_PART_TIME_SUPPORT = "recurring_part_time_support"


class Job(Base):
    __tablename__ = "jobs"

    id = Column(Integer, primary_key=True, index=True)
    employer_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    # ─── Required Job Fields ────────────────────────────
    title = Column(String(255), nullable=False)
    category = Column(SAEnum(JobCategory), nullable=False)
    work_description = Column(String(100), nullable=False)
    role_description = Column(Text, nullable=False)
    required_skill = Column(String(255), nullable=True)

    # ─── Location ────────────────────────────────────────
    city = Column(String(100), nullable=False, default="Chennai")
    location_type = Column(SAEnum(LocationType), nullable=False)
    address = Column(Text, nullable=True)

    # ─── Timing ──────────────────────────────────────────
    date_of_task = Column(DateTime, nullable=False)
    time_span = Column(SAEnum(TimeSpan), nullable=False)

    # ─── Organization ────────────────────────────────────
    organization_type = Column(SAEnum(OrganizationType), nullable=False)

    # ─── Budget & Commission (stored as paise) ──────────
    budget_paise = Column(Integer, nullable=False)
    employer_commission_paise = Column(Integer, nullable=False, default=0)
    employer_total_paise = Column(Integer, nullable=False, default=0)
    labor_commission_paise = Column(Integer, nullable=False, default=0)
    labor_receives_paise = Column(Integer, nullable=False, default=0)
    platform_earning_paise = Column(Integer, nullable=False, default=0)

    # ─── Platform Custody Payment Fields ─────────────────
    platform_commission_paise = Column(Integer, nullable=False, default=0)   # budget × 0.03
    worker_payout_paise = Column(Integer, nullable=False, default=0)         # budget × 0.97
    payment_status = Column(String(30), nullable=True, default="pending")    # pending/verification_pending/verified/payout_released
    payment_sent_at = Column(DateTime, nullable=True)                        # When employer marked payment sent
    payout_released_at = Column(DateTime, nullable=True)                     # When admin released payout

    # ─── Status ──────────────────────────────────────────
    status = Column(String(30), nullable=False, default="posted", index=True)
    allotted_labor_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    accepted_at = Column(DateTime, nullable=True)

    # ─── Payment ─────────────────────────────────────────
    payment_method = Column(String(20), nullable=True)  # "upi" or "cash"

    # ─── Timestamps ──────────────────────────────────────
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # ─── Relationships ───────────────────────────────────
    employer = relationship("User", back_populates="posted_jobs", foreign_keys=[employer_id])
    allotted_labor = relationship("User", foreign_keys=[allotted_labor_id])
    applications = relationship("Application", back_populates="job")
    status_transitions = relationship("StatusTransition", back_populates="job", order_by="StatusTransition.created_at")
    reviews = relationship("Review", back_populates="job")
    commission_ledger = relationship("CommissionLedger", back_populates="job", uselist=False)

    # ─── Composite Indexes ───────────────────────────────
    __table_args__ = (
        Index("ix_jobs_status_employer", "status", "employer_id"),
        Index("ix_jobs_payment_status", "payment_status"),
    )
