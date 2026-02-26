"""
Bridge Point — Reviews Router
Post-job review system.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.models.job import Job
from app.models.review import Review
from app.schemas.common import ReviewCreate, ReviewResponse
from app.services.state_machine import JobStatus
from app.utils.deps import get_current_user

router = APIRouter(prefix="/api/reviews", tags=["Reviews"])


@router.post("", response_model=ReviewResponse, status_code=201)
def create_review(
    payload: ReviewCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Submit a review after job completion.
    Only allowed when job status is 'paid' or 'payment_received'.
    """
    job = db.query(Job).filter(Job.id == payload.job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    # Must be completed/paid
    completed_statuses = [
        JobStatus.PAYOUT_RELEASED.value,
        JobStatus.PAYMENT_COMPLETED.value,
    ]
    if job.status not in completed_statuses:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Reviews can only be submitted after payment",
        )

    # Reviewer must be involved in the job
    if current_user.id not in [job.employer_id, job.allotted_labor_id]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not involved in this job",
        )

    # Reviewee must be the other party
    if payload.reviewee_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot review yourself",
        )

    if payload.reviewee_id not in [job.employer_id, job.allotted_labor_id]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Reviewee must be involved in this job",
        )

    # Check for duplicate review
    existing = (
        db.query(Review)
        .filter(
            Review.job_id == payload.job_id,
            Review.reviewer_id == current_user.id,
        )
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="You have already reviewed this job",
        )

    review = Review(
        job_id=payload.job_id,
        reviewer_id=current_user.id,
        reviewee_id=payload.reviewee_id,
        rating=payload.rating,
        comment=payload.comment,
    )
    db.add(review)
    db.commit()
    db.refresh(review)

    return _review_to_response(review)


@router.get("/user/{user_id}", response_model=list[ReviewResponse])
def get_user_reviews(user_id: int, db: Session = Depends(get_db)):
    """Get all reviews received by a user."""
    reviews = (
        db.query(Review)
        .filter(Review.reviewee_id == user_id)
        .order_by(Review.created_at.desc())
        .all()
    )
    return [_review_to_response(r) for r in reviews]


@router.get("/job/{job_id}", response_model=list[ReviewResponse])
def get_job_reviews(job_id: int, db: Session = Depends(get_db)):
    """Get all reviews for a job."""
    reviews = (
        db.query(Review)
        .filter(Review.job_id == job_id)
        .order_by(Review.created_at.desc())
        .all()
    )
    return [_review_to_response(r) for r in reviews]


def _review_to_response(review: Review) -> ReviewResponse:
    """Convert Review ORM to response."""
    reviewer = review.reviewer
    return ReviewResponse(
        id=review.id,
        job_id=review.job_id,
        reviewer_id=review.reviewer_id,
        reviewee_id=review.reviewee_id,
        rating=review.rating,
        comment=review.comment,
        created_at=review.created_at,
        reviewer_name=reviewer.full_name if reviewer else None,
    )
