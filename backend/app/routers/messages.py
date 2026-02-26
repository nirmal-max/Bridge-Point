"""
Bridge Point — Messages Router
In-app chat between employer and assigned labor.
Secured: only job participants can send/view messages.
"""

import re
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

from app.database import get_db
from app.models.user import User
from app.models.job import Job
from app.models.message import Message
from app.utils.deps import get_current_user
from app.services.websocket_manager import manager

router = APIRouter(prefix="/api/messages", tags=["Messages"])


# ─── Schemas ──────────────────────────────────────────────

class MessageCreate(BaseModel):
    job_id: int
    content: str = Field(..., min_length=1, max_length=2000)


class MessageResponse(BaseModel):
    id: int
    job_id: int
    sender_id: int
    sender_name: Optional[str] = None
    content: str
    created_at: datetime

    model_config = {"from_attributes": True}


# ─── Endpoints ───────────────────────────────────────────

@router.post("", response_model=MessageResponse, status_code=201)
async def send_message(
    payload: MessageCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Send a message in a job's chat. Only participants allowed."""
    job = db.query(Job).filter(Job.id == payload.job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    # Security: only employer and assigned labor can chat
    if current_user.id not in [job.employer_id, job.allotted_labor_id]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only job participants can send messages",
        )

    # Security: chat only available after task acceptance
    if not job.allotted_labor_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Chat is only available after a worker has been assigned",
        )

    # Input sanitization: strip HTML/script tags
    clean_content = re.sub(r"<[^>]*>", "", payload.content).strip()
    if not clean_content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Message content cannot be empty",
        )

    msg = Message(
        job_id=payload.job_id,
        sender_id=current_user.id,
        content=clean_content,
    )
    db.add(msg)
    db.commit()
    db.refresh(msg)

    response = _message_to_response(msg, current_user.full_name)

    # Notify the other participant via WebSocket
    other_user_id = (
        job.allotted_labor_id if current_user.id == job.employer_id else job.employer_id
    )
    await manager.send_to_user(other_user_id, {
        "type": "chat:message",
        "job_id": job.id,
        "message": {
            "id": msg.id,
            "sender_id": msg.sender_id,
            "sender_name": current_user.full_name,
            "content": clean_content,
            "created_at": msg.created_at.isoformat() if msg.created_at else None,
        },
    })

    return response


@router.get("/job/{job_id}", response_model=list[MessageResponse])
def get_job_messages(
    job_id: int,
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get chat messages for a job. Only participants allowed."""
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    # Security: only participants
    if current_user.id not in [job.employer_id, job.allotted_labor_id]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only job participants can view messages",
        )

    messages = (
        db.query(Message)
        .filter(Message.job_id == job_id)
        .order_by(Message.created_at.asc())
        .offset((page - 1) * per_page)
        .limit(per_page)
        .all()
    )

    return [_message_to_response(m) for m in messages]


def _message_to_response(
    msg: Message, sender_name: str | None = None
) -> MessageResponse:
    """Convert Message ORM to response."""
    name = sender_name
    if not name and msg.sender:
        name = msg.sender.full_name

    return MessageResponse(
        id=msg.id,
        job_id=msg.job_id,
        sender_id=msg.sender_id,
        sender_name=name,
        content=msg.content,
        created_at=msg.created_at,
    )
