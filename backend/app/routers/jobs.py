"""
Bridge Point — Jobs Router
Job posting, listing, detail, status transitions.
"""

import json
import re
import time
from collections import defaultdict
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import text
from datetime import datetime, timezone

from app.database import get_db
from app.models.user import User
from app.models.job import Job, JobCategory, LocationType, TimeSpan, OrganizationType
from app.models.status_transition import StatusTransition
from app.schemas.job import JobCreate, JobResponse, JobListResponse, JobStatusUpdate
from app.services.commission import calculate_commission
from app.services.state_machine import (
    JobStatus, validate_transition,
    FEED_VISIBLE_STATUSES, ACTIVE_WORK_STATUSES, HISTORY_STATUSES,
)
from app.services.websocket_manager import manager
from app.utils.deps import get_current_user, require_employer

router = APIRouter(prefix="/api/jobs", tags=["Jobs"])

# ─── In-memory rate limiter for accept-task ───────────
_accept_rate_limit: dict[int, list[float]] = defaultdict(list)
RATE_LIMIT_MAX = 5       # max requests
RATE_LIMIT_WINDOW = 60   # seconds


def _check_rate_limit(user_id: int) -> None:
    """Raise 429 if user exceeds accept-task rate limit."""
    now = time.time()
    # Prune old entries
    _accept_rate_limit[user_id] = [
        t for t in _accept_rate_limit[user_id] if now - t < RATE_LIMIT_WINDOW
    ]
    if len(_accept_rate_limit[user_id]) >= RATE_LIMIT_MAX:
        raise HTTPException(
            status_code=429,
            detail="Too many accept requests. Please try again later.",
        )
    _accept_rate_limit[user_id].append(now)


@router.post("", response_model=JobResponse, status_code=201)
def create_job(
    payload: JobCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_employer),
):
    """Post a new micro-job. Commission calculated deterministically."""
    # Validate work_description — accepts predefined or custom string
    raw_wd = payload.work_description.strip() if payload.work_description else ""
    # Strip HTML/script tags for safety
    raw_wd = re.sub(r"<[^>]*>", "", raw_wd)
    if not raw_wd:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="work_description is required.",
        )
    if len(raw_wd) > 100:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="work_description must be 100 characters or fewer.",
        )
    work_desc = raw_wd

    # Calculate commission (backend deterministic — AI never touches this)
    breakdown = calculate_commission(payload.budget)

    job = Job(
        employer_id=current_user.id,
        title=payload.title,
        category=JobCategory(payload.category),
        work_description=work_desc,
        role_description=payload.role_description,
        required_skill=payload.required_skill,
        city=payload.city,
        location_type=LocationType(payload.location_type),
        address=payload.address,
        date_of_task=payload.date_of_task,
        time_span=TimeSpan(payload.time_span),
        organization_type=OrganizationType(payload.organization_type),
        budget_paise=breakdown.budget_paise,
        employer_commission_paise=breakdown.employer_commission_paise,
        employer_total_paise=breakdown.employer_total_paise,
        labor_commission_paise=breakdown.labor_commission_paise,
        labor_receives_paise=breakdown.labor_receives_paise,
        platform_earning_paise=breakdown.platform_earning_paise,
        platform_commission_paise=breakdown.platform_commission_paise,
        worker_payout_paise=breakdown.worker_payout_paise,
        status=JobStatus.POSTED.value,
    )

    db.add(job)
    db.commit()
    db.refresh(job)

    # Log initial transition
    transition = StatusTransition(
        job_id=job.id,
        from_status="created",
        to_status=JobStatus.POSTED.value,
        changed_by_user_id=current_user.id,
    )
    db.add(transition)
    db.commit()

    return _job_to_response(job, current_user)


@router.get("", response_model=JobListResponse)
def list_jobs(
    db: Session = Depends(get_db),
    category: str | None = None,
    city: str | None = None,
    work_description: str | None = None,
    status_filter: str | None = Query(None, alias="status"),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
):
    """List jobs with optional filters. Default: only posted + labour_allotted (feed visibility)."""
    query = db.query(Job)

    if category:
        query = query.filter(Job.category == category)
    if city:
        query = query.filter(Job.city.ilike(f"%{city}%"))
    if work_description:
        query = query.filter(Job.work_description == work_description)
    if status_filter:
        query = query.filter(Job.status == status_filter)
    else:
        # Default feed: only show available and recently-taken jobs
        # Hide: work_started, work_in_progress, work_completed, paid, payment_received
        query = query.filter(Job.status.in_([
            JobStatus.POSTED.value,
            JobStatus.LABOUR_ALLOTTED.value,
        ]))

    total = query.count()
    jobs = query.order_by(Job.created_at.desc()).offset((page - 1) * per_page).limit(per_page).all()

    return JobListResponse(
        jobs=[_job_to_response(j) for j in jobs],
        total=total,
        page=page,
        per_page=per_page,
    )


# ─── IMPORTANT: Static sub-paths MUST be declared BEFORE /{job_id} ───
# ─── Otherwise FastAPI interprets "employer" as a job_id integer ──────

@router.get("/employer/my-jobs", response_model=JobListResponse)
def get_my_posted_jobs(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_employer),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
):
    """Employer: get my posted jobs (all statuses)."""
    query = db.query(Job).filter(Job.employer_id == current_user.id)
    total = query.count()
    jobs = query.order_by(Job.created_at.desc()).offset((page - 1) * per_page).limit(per_page).all()

    return JobListResponse(
        jobs=[_job_to_response(j, current_user) for j in jobs],
        total=total,
        page=page,
        per_page=per_page,
    )


@router.get("/labor/active-tasks", response_model=JobListResponse)
def get_labor_active_tasks(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
):
    """Labor: get jobs assigned to me that are currently active (server-side secure)."""
    active_values = [s.value for s in ACTIVE_WORK_STATUSES]
    query = db.query(Job).filter(
        Job.allotted_labor_id == current_user.id,
        Job.status.in_(active_values),
    )
    total = query.count()
    jobs = query.order_by(Job.updated_at.desc()).offset((page - 1) * per_page).limit(per_page).all()

    return JobListResponse(
        jobs=[_job_to_response(j, current_user) for j in jobs],
        total=total,
        page=page,
        per_page=per_page,
    )


@router.get("/labor/history", response_model=JobListResponse)
def get_labor_history(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
):
    """Labor: get completed jobs (payment finished)."""
    history_values = [s.value for s in HISTORY_STATUSES]
    query = db.query(Job).filter(
        Job.allotted_labor_id == current_user.id,
        Job.status.in_(history_values),
    )
    total = query.count()
    jobs = query.order_by(Job.updated_at.desc()).offset((page - 1) * per_page).limit(per_page).all()

    return JobListResponse(
        jobs=[_job_to_response(j, current_user) for j in jobs],
        total=total,
        page=page,
        per_page=per_page,
    )


# ─── Dynamic path routes AFTER static sub-paths ─────────────────────

@router.get("/{job_id}", response_model=JobResponse)
def get_job(job_id: int, db: Session = Depends(get_db)):
    """Get job details by ID."""
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return _job_to_response(job)


@router.patch("/{job_id}/status", response_model=JobResponse)
def update_job_status(
    job_id: int,
    payload: JobStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Transition job status.
    STRICT STATE MACHINE: only valid forward transitions allowed.
    AUTHORIZATION: enforced per stage:
      - labour_allotted → work_started: assigned labor only
      - work_started → work_in_progress: assigned labor only
      - work_in_progress → work_completed: employer or assigned labor
    Payment stages are handled by dedicated payment endpoints.
    """
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    current_status = JobStatus(job.status)
    try:
        target_status = JobStatus(payload.status)
    except ValueError:
        valid = [e.value for e in JobStatus]
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid status. Must be one of: {valid}",
        )

    # STRICT: validate transition
    if not validate_transition(current_status, target_status):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid transition: {current_status.value} → {target_status.value}. "
                   f"No skipping allowed.",
        )

    # ─── AUTHORIZATION: who can trigger each transition ──────
    is_employer = current_user.id == job.employer_id
    is_assigned_labor = current_user.id == job.allotted_labor_id
    is_admin = current_user.is_admin

    # Work stages: only assigned labor or employer can advance
    work_transitions = {
        JobStatus.LABOUR_ALLOTTED: JobStatus.WORK_STARTED,      # labor starts work
        JobStatus.WORK_STARTED: JobStatus.WORK_IN_PROGRESS,     # labor confirms in-progress
        JobStatus.WORK_IN_PROGRESS: JobStatus.WORK_COMPLETED,   # employer or labor marks done
    }

    if current_status in work_transitions:
        if current_status in (JobStatus.LABOUR_ALLOTTED, JobStatus.WORK_STARTED):
            # Only assigned labor can start/progress work
            if not is_assigned_labor and not is_admin:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Only the assigned worker can advance this stage.",
                )
        elif current_status == JobStatus.WORK_IN_PROGRESS:
            # Only employer (or admin) can mark work as completed
            if not is_employer and not is_admin:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Only the employer can mark work as completed.",
                )
    else:
        # Payment transitions should use dedicated payment endpoints
        if not is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Payment stage transitions must use the payment endpoints.",
            )

    # Log the transition with timestamp
    transition = StatusTransition(
        job_id=job.id,
        from_status=current_status.value,
        to_status=target_status.value,
        changed_by_user_id=current_user.id,
    )
    db.add(transition)

    job.status = target_status.value
    job.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(job)

    return _job_to_response(job, current_user)


@router.get("/{job_id}/transitions")
def get_job_transitions(job_id: int, db: Session = Depends(get_db)):
    """Get full timestamped transition history for a job."""
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    transitions = (
        db.query(StatusTransition)
        .filter(StatusTransition.job_id == job_id)
        .order_by(StatusTransition.created_at.asc())
        .all()
    )

    return [
        {
            "id": t.id,
            "from_status": t.from_status,
            "to_status": t.to_status,
            "changed_by_user_id": t.changed_by_user_id,
            "created_at": t.created_at.isoformat() if t.created_at else None,
        }
        for t in transitions
    ]


@router.post("/{job_id}/repost", response_model=JobResponse, status_code=201)
def repost_job(
    job_id: int,
    date_of_task: datetime = Query(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_employer),
):
    """Employer: repost a completed job with a new date."""
    original = db.query(Job).filter(Job.id == job_id, Job.employer_id == current_user.id).first()
    if not original:
        raise HTTPException(status_code=404, detail="Job not found")

    # Recalculate commission for new posting
    budget_rupees = original.budget_paise / 100
    breakdown = calculate_commission(budget_rupees)

    new_job = Job(
        employer_id=current_user.id,
        title=original.title,
        category=original.category,
        work_description=original.work_description,
        role_description=original.role_description,
        required_skill=original.required_skill,
        city=original.city,
        location_type=original.location_type,
        address=original.address,
        date_of_task=date_of_task,
        time_span=original.time_span,
        organization_type=original.organization_type,
        budget_paise=breakdown.budget_paise,
        employer_commission_paise=breakdown.employer_commission_paise,
        employer_total_paise=breakdown.employer_total_paise,
        labor_commission_paise=breakdown.labor_commission_paise,
        labor_receives_paise=breakdown.labor_receives_paise,
        platform_earning_paise=breakdown.platform_earning_paise,
        platform_commission_paise=breakdown.platform_commission_paise,
        worker_payout_paise=breakdown.worker_payout_paise,
        status=JobStatus.POSTED.value,
    )

    db.add(new_job)
    db.commit()
    db.refresh(new_job)

    transition = StatusTransition(
        job_id=new_job.id,
        from_status="created",
        to_status=JobStatus.POSTED.value,
        changed_by_user_id=current_user.id,
    )
    db.add(transition)
    db.commit()

    return _job_to_response(new_job, current_user)


@router.post("/{job_id}/accept-task", response_model=JobResponse)
async def accept_task(
    job_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Instant task acceptance — first-come-first-serve.
    Atomic UPDATE ensures only one user can claim a task.
    No employer approval step. No waiting state.
    """
    # ─── Rate limiting ────────────────────────────────────
    _check_rate_limit(current_user.id)

    # Pre-validate: fetch job for checks
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    # Security: cannot accept own job
    if job.employer_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot accept your own task",
        )

    # Security: only posted jobs can be accepted
    if job.status != JobStatus.POSTED.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This task is no longer available",
        )

    # ─── ATOMIC UPDATE: First-come-first-serve ───────────
    now = datetime.now(timezone.utc)
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
            "job_id": job_id,
            "posted_status": JobStatus.POSTED.value,
        },
    )

    if result.rowcount == 0:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Task already accepted.",
        )

    # Log status transition: posted → labour_allotted (single, clean)
    transition = StatusTransition(
        job_id=job_id,
        from_status=JobStatus.POSTED.value,
        to_status=JobStatus.LABOUR_ALLOTTED.value,
        changed_by_user_id=current_user.id,
    )
    db.add(transition)
    db.commit()

    # Expire ORM cache and re-read from DB to get fresh data after raw SQL
    db.expire(job)
    db.refresh(job)

    # ─── Notify employer via WebSocket ───────────────────
    await manager.send_to_user(job.employer_id, {
        "type": "task:accepted",
        "job_id": job.id,
        "job_title": job.title,
        "labor_id": current_user.id,
        "labor_name": current_user.full_name,
        "message": f"{current_user.full_name} has accepted your task \"{job.title}\"",
    })

    return _job_to_response(job, current_user)


def _job_to_response(job: Job, current_user: User | None = None) -> JobResponse:
    """Convert Job ORM model to response schema."""
    employer = job.employer if job.employer else None
    allotted_labor = job.allotted_labor if job.allotted_labor_id else None

    return JobResponse(
        id=job.id,
        employer_id=job.employer_id,
        title=job.title,
        category=job.category.value if hasattr(job.category, 'value') else str(job.category),
        work_description=str(job.work_description),
        role_description=job.role_description,
        required_skill=job.required_skill,
        city=job.city,
        location_type=job.location_type.value if hasattr(job.location_type, 'value') else str(job.location_type),
        address=job.address,
        date_of_task=job.date_of_task,
        time_span=job.time_span.value if hasattr(job.time_span, 'value') else str(job.time_span),
        organization_type=job.organization_type.value if hasattr(job.organization_type, 'value') else str(job.organization_type),
        status=job.status,
        allotted_labor_id=job.allotted_labor_id,
        allotted_labor_name=allotted_labor.full_name if allotted_labor else None,
        accepted_at=job.accepted_at,
        payment_method=job.payment_method,
        created_at=job.created_at,
        budget=job.budget_paise / 100,
        employer_commission=job.employer_commission_paise / 100,
        employer_total=job.employer_total_paise / 100,
        labor_commission=job.labor_commission_paise / 100,
        labor_receives=job.labor_receives_paise / 100,
        platform_commission=job.platform_commission_paise / 100,
        worker_payout=job.worker_payout_paise / 100,
        payment_status=job.payment_status,
        payment_sent_at=job.payment_sent_at,
        payout_released_at=job.payout_released_at,
        employer_name=employer.full_name if employer else None,
    )
