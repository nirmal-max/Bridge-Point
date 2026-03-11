"""
Bridge Point — User Model
Supports both Employer and Labor user types.
"""

from datetime import datetime, timezone
from sqlalchemy import (
    Column, Integer, String, Text, DateTime, Boolean, Enum as SAEnum
)
from sqlalchemy.orm import relationship
import enum

from app.database import Base


class UserRole(str, enum.Enum):
    EMPLOYER = "employer"
    LABOR = "labor"


class LaborCategory(str, enum.Enum):
    STUDENT = "student"
    FREELANCER = "freelancer"
    LABOR = "labor"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    phone = Column(String(15), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=False)
    roles = Column(Text, nullable=False)  # JSON list of UserRole strings
    is_admin = Column(Boolean, default=False, nullable=False)  # Platform admin flag

    # ─── Labor-specific fields ──────────────────────────
    labor_category = Column(SAEnum(LaborCategory), nullable=True)
    skills = Column(Text, nullable=True)  # JSON list of skill strings
    city = Column(String(100), default="Chennai")
    bio = Column(Text, nullable=True)

    # ─── Cashfree Payouts (worker bank/UPI details) ─────
    bank_account_number = Column(String(20), nullable=True)
    bank_ifsc = Column(String(11), nullable=True)
    payout_upi_id = Column(String(50), nullable=True)

    # ─── Verification ────────────────────────────────────
    phone_verified = Column(Boolean, default=False)
    email_verified = Column(Boolean, default=False)

    # ─── Timestamps ──────────────────────────────────────
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # ─── Relationships ───────────────────────────────────
    posted_jobs = relationship("Job", back_populates="employer", foreign_keys="Job.employer_id")
    applications = relationship("Application", back_populates="labor", foreign_keys="Application.labor_id")
    reviews_given = relationship("Review", back_populates="reviewer", foreign_keys="Review.reviewer_id")
    reviews_received = relationship("Review", back_populates="reviewee", foreign_keys="Review.reviewee_id")
    favorites = relationship("Favorite", back_populates="employer", foreign_keys="Favorite.employer_id")
