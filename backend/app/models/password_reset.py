"""
Bridge Point — Password Reset Model
Stores OTP hashes for forgot-password flow. Records expire and have attempt limits.
"""

from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import relationship

from app.database import Base


class PasswordReset(Base):
    __tablename__ = "password_resets"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    otp_hash = Column(String(255), nullable=False)           # bcrypt hash of the 6-digit OTP
    expires_at = Column(DateTime, nullable=False)             # OTP expiry (5 minutes)
    used = Column(Boolean, default=False)                     # Whether OTP has been consumed
    attempts = Column(Integer, default=0)                     # Failed verification attempts
    reset_token = Column(String(255), nullable=True)          # One-time token issued after OTP verified

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    user = relationship("User", foreign_keys=[user_id])
