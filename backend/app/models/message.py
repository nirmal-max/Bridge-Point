"""
Bridge Point — Message Model
In-app messaging between employer and assigned labor.
"""

from datetime import datetime, timezone
from sqlalchemy import (
    Column, Integer, Text, DateTime, ForeignKey, Index
)
from sqlalchemy.orm import relationship

from app.database import Base


class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(Integer, ForeignKey("jobs.id"), nullable=False, index=True)
    sender_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Composite index for efficient chat history queries
    __table_args__ = (
        Index("ix_messages_job_created", "job_id", "created_at"),
    )

    # Relationships
    job = relationship("Job", foreign_keys=[job_id])
    sender = relationship("User", foreign_keys=[sender_id])
