"""
Bridge Point — Applications Router
Labor applies to jobs, employer accepts/rejects.
"""

import json
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from datetime import datetime, timezone

from app.database import get_db
from app.models.user import User
from app.models.job import Job
from app.models.application import Application, ApplicationStatus
from app.models.status_transition import StatusTransition
from app.schemas.common import ApplicationCreate, ApplicationResponse
from app.services.state_machine import JobStatus, validate_transition
from app.utils.deps import get_current_user, require_labor, require_employer

router = APIRouter(prefix="/api/applications", tags=["Applications"])


@router.post("", response_model=ApplicationResponse, status_code=201)
def apply_to_job(
    payload: ApplicationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_labor),
):
    """Labor applies to a job. Job must be in 'posted' status."""
    job = db.query(Job).filter(Job.id == payload.job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if job.status != JobStatus.POSTED.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Job is not accepting applications",
        )

    # Unified mode — prevent applying to own job
    if job.employer_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot apply to your own job",
        )

    # Check if already applied
    existing = (
        db.query(Application)
        .filter(Application.job_id == payload.job_id, Application.labor_id == current_user.id)
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="You have already applied to this job",
        )

    # Job stays in "posted" status until employer accepts an application

    application = Application(
        job_id=payload.job_id,
        labor_id=current_user.id,
        cover_note=payload.cover_note,
    )
    db.add(application)
    db.commit()
    db.refresh(application)

    return _application_to_response(application)


@router.get("/job/{job_id}", response_model=list[ApplicationResponse])
def get_job_applications(
    job_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_employer),
):
    """Employer: view all applications for a job."""
    job = db.query(Job).filter(Job.id == job_id, Job.employer_id == current_user.id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found or not yours")

    apps = (
        db.query(Application)
        .filter(Application.job_id == job_id)
        .order_by(Application.created_at.asc())
        .all()
    )

    return [_application_to_response(a) for a in apps]


@router.post("/{application_id}/accept", response_model=ApplicationResponse)
def accept_application(
    application_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_employer),
):
    """
    Employer accepts a labor application.
    Allots labor to the job, transitions status, and shares contact details.
    First applicant accepted wins — per document spec.
    """
    application = db.query(Application).filter(Application.id == application_id).first()
    if not application:
        raise HTTPException(status_code=404, detail="Application not found")

    job = db.query(Job).filter(Job.id == application.job_id, Job.employer_id == current_user.id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found or not yours")

    if job.status != JobStatus.POSTED.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Job must be in 'posted' status to accept applications. Current: {job.status}",
        )

    # Atomic: ensure no one else already claimed the job
    now = datetime.now(timezone.utc)
    from sqlalchemy import text
    result = db.execute(
        text(
            "UPDATE jobs SET allotted_labor_id = :labor_id, "
            "status = :new_status, accepted_at = :accepted_at, "
            "updated_at = :updated_at "
            "WHERE id = :job_id AND allotted_labor_id IS NULL AND status = :posted_status"
        ),
        {
            "labor_id": application.labor_id,
            "new_status": JobStatus.LABOUR_ALLOTTED.value,
            "accepted_at": now,
            "updated_at": now,
            "job_id": job.id,
            "posted_status": JobStatus.POSTED.value,
        },
    )

    if result.rowcount == 0:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Job already accepted by someone else.",
        )

    # Accept this application
    application.status = ApplicationStatus.ACCEPTED
    application.updated_at = now

    # Reject all other pending applications
    other_apps = (
        db.query(Application)
        .filter(
            Application.job_id == job.id,
            Application.id != application.id,
            Application.status == ApplicationStatus.PENDING,
        )
        .all()
    )
    for app in other_apps:
        app.status = ApplicationStatus.REJECTED
        app.updated_at = now

    # Log transition: posted → labour_allotted
    transition = StatusTransition(
        job_id=job.id,
        from_status=JobStatus.POSTED.value,
        to_status=JobStatus.LABOUR_ALLOTTED.value,
        changed_by_user_id=current_user.id,
    )
    db.add(transition)

    db.commit()
    db.refresh(application)

    return _application_to_response(application, share_contact=True)


@router.get("/labor/my-applications", response_model=list[ApplicationResponse])
def get_my_applications(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_labor),
):
    """Labor: view my job applications."""
    apps = (
        db.query(Application)
        .filter(Application.labor_id == current_user.id)
        .order_by(Application.created_at.desc())
        .all()
    )
    return [_application_to_response(a) for a in apps]


@router.get("/labor/history", response_model=list[ApplicationResponse])
def get_labor_history(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_labor),
):
    """Labor: view completed task history."""
    history_statuses = [JobStatus.PAYOUT_RELEASED.value, JobStatus.PAYMENT_COMPLETED.value]
    apps = (
        db.query(Application)
        .join(Job)
        .filter(
            Application.labor_id == current_user.id,
            Application.status == ApplicationStatus.ACCEPTED,
            Job.status.in_(history_statuses),
        )
        .order_by(Job.updated_at.desc())
        .all()
    )
    return [_application_to_response(a, share_contact=True) for a in apps]


def _application_to_response(
    app: Application,
    share_contact: bool = False,
) -> ApplicationResponse:
    """Convert Application ORM to response."""
    labor = app.labor
    skills = None
    if labor and labor.skills:
        try:
            skills = json.loads(labor.skills)
        except (json.JSONDecodeError, TypeError):
            skills = []

    return ApplicationResponse(
        id=app.id,
        job_id=app.job_id,
        labor_id=app.labor_id,
        status=app.status.value if hasattr(app.status, 'value') else str(app.status),
        cover_note=app.cover_note,
        created_at=app.created_at,
        labor_name=labor.full_name if labor else None,
        labor_phone=labor.phone if (labor and share_contact) else None,
        labor_skills=skills,
    )
