"""
Bridge Point — Private Requests Router
Direct rehire: employer sends private work request to favorited labor.
"""

import re
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.database import get_db
from app.models.user import User
from app.models.job import Job
from app.models.favorite import Favorite
from app.models.private_request import PrivateRequest
from app.models.status_transition import StatusTransition
from app.schemas.common import (
    PrivateRequestCreate,
    PrivateRequestRespond,
    PrivateRequestResponse,
)
from app.services.state_machine import JobStatus
from app.services.websocket_manager import manager
from app.utils.deps import get_current_user, require_employer

router = APIRouter(prefix="/api/private-requests", tags=["Private Requests"])


# ─── Helpers ─────────────────────────────────────────────

def _request_to_response(req: PrivateRequest) -> PrivateRequestResponse:
    """Convert PrivateRequest ORM to response schema."""
    return PrivateRequestResponse(
        id=req.id,
        job_id=req.job_id,
        employer_id=req.employer_id,
        labor_id=req.labor_id,
        status=req.status,
        message=req.message,
        created_at=req.created_at,
        responded_at=req.responded_at,
        employer_name=req.employer.full_name if req.employer else None,
        labor_name=req.labor.full_name if req.labor else None,
        job_title=req.job.title if req.job else None,
    )


# ─── Employer: Send Private Request ─────────────────────

@router.post("", response_model=PrivateRequestResponse, status_code=201)
async def send_private_request(
    payload: PrivateRequestCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_employer),
):
    """Employer sends a private work request to a favorited labor."""

    # Validate labor is in employer's favorites
    fav = (
        db.query(Favorite)
        .filter(
            Favorite.employer_id == current_user.id,
            Favorite.labor_id == payload.labor_id,
        )
        .first()
    )
    if not fav:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Labor must be in your favorites to send a private request.",
        )

    # Validate job belongs to employer and is posted
    job = db.query(Job).filter(
        Job.id == payload.job_id,
        Job.employer_id == current_user.id,
    ).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found or not yours.")
    if job.status != JobStatus.POSTED.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only posted jobs can have private requests.",
        )

    # Check for existing pending request for this job + labor
    existing = (
        db.query(PrivateRequest)
        .filter(
            PrivateRequest.job_id == payload.job_id,
            PrivateRequest.labor_id == payload.labor_id,
            PrivateRequest.status == "pending",
        )
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A pending request already exists for this labor and job.",
        )

    # Sanitize message
    message = None
    if payload.message:
        message = re.sub(r"<[^>]*>", "", payload.message.strip())[:500]

    req = PrivateRequest(
        job_id=payload.job_id,
        employer_id=current_user.id,
        labor_id=payload.labor_id,
        message=message,
    )
    db.add(req)
    db.commit()
    db.refresh(req)

    # Notify labor via WebSocket
    await manager.send_to_user(payload.labor_id, {
        "type": "private_request:new",
        "request_id": req.id,
        "job_id": job.id,
        "job_title": job.title,
        "employer_name": current_user.full_name,
        "message": f"{current_user.full_name} wants to hire you for \"{job.title}\"",
    })

    return _request_to_response(req)


# ─── Labor: View My Pending Requests ────────────────────

@router.get("/my", response_model=list[PrivateRequestResponse])
def get_my_requests(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Labor: view private requests sent to me."""
    requests = (
        db.query(PrivateRequest)
        .filter(
            PrivateRequest.labor_id == current_user.id,
            PrivateRequest.status == "pending",
        )
        .order_by(PrivateRequest.created_at.desc())
        .all()
    )
    return [_request_to_response(r) for r in requests]


# ─── Labor: Respond to Request ──────────────────────────

@router.post("/{request_id}/respond", response_model=PrivateRequestResponse)
async def respond_to_request(
    request_id: int,
    payload: PrivateRequestRespond,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Labor accepts or denies a private request."""
    req = db.query(PrivateRequest).filter(PrivateRequest.id == request_id).first()
    if not req:
        raise HTTPException(status_code=404, detail="Request not found.")

    # Only the target labor can respond
    if req.labor_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized.")

    if req.status != "pending":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This request has already been responded to.",
        )

    now = datetime.now(timezone.utc)

    if payload.action == "accept":
        # ─── Atomic task acceptance (same logic as accept_task) ───
        job = db.query(Job).filter(Job.id == req.job_id).first()
        if not job or job.status != JobStatus.POSTED.value:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Job is no longer available for acceptance.",
            )

        result = db.execute(
            text(
                "UPDATE jobs SET allotted_labor_id = :labor_id, "
                "status = :new_status, accepted_at = :accepted_at, "
                "updated_at = :updated_at "
                "WHERE id = :job_id AND allotted_labor_id IS NULL AND status = :posted_status"
            ),
            {
                "labor_id": current_user.id,
                "new_status": JobStatus.LABOUR_ALLOTTED.value,
                "accepted_at": now,
                "updated_at": now,
                "job_id": req.job_id,
                "posted_status": JobStatus.POSTED.value,
            },
        )

        if result.rowcount == 0:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Task already accepted by someone else.",
            )

        # Log transition: posted → labour_allotted (single, clean)
        transition = StatusTransition(
            job_id=req.job_id,
            from_status=JobStatus.POSTED.value,
            to_status=JobStatus.LABOUR_ALLOTTED.value,
            changed_by_user_id=current_user.id,
        )
        db.add(transition)

        req.status = "accepted"
        req.responded_at = now
        db.commit()
        db.refresh(req)

        # Notify employer
        await manager.send_to_user(req.employer_id, {
            "type": "private_request:accepted",
            "request_id": req.id,
            "job_id": req.job_id,
            "job_title": job.title,
            "labor_name": current_user.full_name,
            "message": f"{current_user.full_name} accepted your private request for \"{job.title}\"",
        })

    elif payload.action == "deny":
        req.status = "denied"
        req.responded_at = now

        # Optionally update description before reposting
        if payload.updated_description:
            sanitized = re.sub(r"<[^>]*>", "", payload.updated_description.strip())
            if sanitized:
                job = db.query(Job).filter(Job.id == req.job_id).first()
                if job and job.employer_id == req.employer_id:
                    job.role_description = sanitized
                    job.updated_at = now

        db.commit()
        db.refresh(req)

        # Notify employer that request was denied
        job = db.query(Job).filter(Job.id == req.job_id).first()
        await manager.send_to_user(req.employer_id, {
            "type": "private_request:denied",
            "request_id": req.id,
            "job_id": req.job_id,
            "job_title": job.title if job else "Unknown",
            "labor_name": current_user.full_name,
            "message": f"{current_user.full_name} declined your private request. Job remains posted publicly.",
        })

    return _request_to_response(req)
