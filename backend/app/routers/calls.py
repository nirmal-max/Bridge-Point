"""
Bridge Point — Calls Router
REST endpoints for call history and details.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_, desc

from app.database import get_db
from app.utils.deps import get_current_user
from app.models.user import User
from app.models.call import CallLog
from app.models.job import Job
from app.schemas.call import CallLogResponse, CallHistoryResponse

router = APIRouter(prefix="/api/calls", tags=["Calls"])


def _call_to_response(call: CallLog) -> CallLogResponse:
    """Convert CallLog ORM model to response schema — uses eager-loaded relationships."""
    return CallLogResponse(
        id=call.id,
        caller_id=call.caller_id,
        callee_id=call.callee_id,
        caller_name=call.caller.full_name if call.caller else None,
        callee_name=call.callee.full_name if call.callee else None,
        job_id=call.job_id,
        job_title=call.job.title if call.job else None,
        status=call.status.value if hasattr(call.status, 'value') else call.status,
        started_at=call.started_at,
        ended_at=call.ended_at,
        duration_seconds=call.duration_seconds or 0,
        created_at=call.created_at,
    )


@router.get("/history", response_model=CallHistoryResponse)
def get_call_history(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get paginated call history for the current user."""
    query = (
        db.query(CallLog)
        .options(
            joinedload(CallLog.caller),
            joinedload(CallLog.callee),
            joinedload(CallLog.job),
        )
        .filter(
            or_(
                CallLog.caller_id == current_user.id,
                CallLog.callee_id == current_user.id,
            )
        )
        .order_by(desc(CallLog.created_at))
    )

    total = db.query(CallLog).filter(
        or_(CallLog.caller_id == current_user.id, CallLog.callee_id == current_user.id)
    ).count()
    calls = query.offset((page - 1) * per_page).limit(per_page).all()

    return CallHistoryResponse(
        calls=[_call_to_response(c) for c in calls],
        total=total,
        page=page,
        per_page=per_page,
    )


@router.get("/{call_id}", response_model=CallLogResponse)
def get_call_detail(
    call_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a single call log detail."""
    call = db.query(CallLog).filter(CallLog.id == call_id).first()
    if not call:
        raise HTTPException(status_code=404, detail="Call not found")

    # Only allow participants to view
    if call.caller_id != current_user.id and call.callee_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to view this call")

    return _call_to_response(call)
