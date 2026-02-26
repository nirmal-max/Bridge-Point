"""
Bridge Point — Payment Router
Platform Custody Model: Platform collects payment, verifies, then releases payout.

Flow:
  1. Employer initiates payment → status: payment_in_process
  2. Employer marks payment sent → status: verification_pending
  3. Admin verifies payment → status: verified
  4. Admin releases payout → status: payout_released → payment_completed
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime, timezone

from app.database import get_db
from app.models.user import User
from app.models.job import Job
from app.models.commission import CommissionLedger
from app.models.status_transition import StatusTransition
from app.schemas.common import CommissionResponse
from app.services.state_machine import JobStatus, validate_transition
from app.services.commission import calculate_commission
from app.services.websocket_manager import manager
from app.config import PLATFORM_UPI_ID, PLATFORM_UPI_NAME
from app.utils.deps import get_current_user, require_employer, require_admin

router = APIRouter(prefix="/api/payments", tags=["Payments"])


from pydantic import BaseModel


class PaymentInitiate(BaseModel):
    job_id: int
    payment_method: str  # "upi" or "cash"


# ─── 1. Employer: Initiate Payment ──────────────────────

@router.post("/initiate")
def initiate_payment(
    payload: PaymentInitiate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_employer),
):
    """
    Employer initiates payment for a completed job.
    Transitions: work_completed → payment_in_process.
    Returns Platform UPI details and commission breakdown.
    """
    if payload.payment_method not in ("upi", "cash"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Payment method must be 'upi' or 'cash'",
        )

    job = db.query(Job).filter(Job.id == payload.job_id, Job.employer_id == current_user.id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found or not yours")

    if job.status != JobStatus.WORK_COMPLETED.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Job must be in 'work_completed' status. Current: {job.status}",
        )

    if not job.allotted_labor_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No labor allotted to this job",
        )

    # Create commission ledger
    ledger = CommissionLedger(
        job_id=job.id,
        employer_id=current_user.id,
        labor_id=job.allotted_labor_id,
        budget_paise=job.budget_paise,
        employer_commission_paise=job.employer_commission_paise,
        employer_total_paise=job.employer_total_paise,
        labor_commission_paise=job.labor_commission_paise,
        labor_receives_paise=job.labor_receives_paise,
        platform_earning_paise=job.platform_earning_paise,
        payment_method=payload.payment_method,
        payment_status="initiated",
    )
    db.add(ledger)

    # Transition: work_completed → payment_in_process
    transition = StatusTransition(
        job_id=job.id,
        from_status=JobStatus.WORK_COMPLETED.value,
        to_status=JobStatus.PAYMENT_IN_PROCESS.value,
        changed_by_user_id=current_user.id,
    )
    db.add(transition)

    job.status = JobStatus.PAYMENT_IN_PROCESS.value
    job.payment_method = payload.payment_method
    job.payment_status = "pending"
    job.updated_at = datetime.now(timezone.utc)

    db.commit()

    return {
        "message": "Payment initiated. Pay to Platform UPI.",
        "status": job.status,
        "platform_upi_id": PLATFORM_UPI_ID,
        "platform_upi_name": PLATFORM_UPI_NAME,
        "amount": job.budget_paise / 100,
        "platform_commission": job.platform_commission_paise / 100,
        "worker_payout": job.worker_payout_paise / 100,
    }


# ─── 2. Employer: Mark Payment Sent ─────────────────────

@router.post("/{job_id}/mark-sent")
async def mark_payment_sent(
    job_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_employer),
):
    """
    Employer confirms they have sent payment to Platform UPI.
    Transitions: payment_in_process → verification_pending.
    """
    job = db.query(Job).filter(Job.id == job_id, Job.employer_id == current_user.id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found or not yours")

    if job.status != JobStatus.PAYMENT_IN_PROCESS.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Job must be in 'payment_in_process' status. Current: {job.status}",
        )

    now = datetime.now(timezone.utc)

    transition = StatusTransition(
        job_id=job.id,
        from_status=JobStatus.PAYMENT_IN_PROCESS.value,
        to_status=JobStatus.VERIFICATION_PENDING.value,
        changed_by_user_id=current_user.id,
    )
    db.add(transition)

    job.status = JobStatus.VERIFICATION_PENDING.value
    job.payment_status = "verification_pending"
    job.payment_sent_at = now
    job.updated_at = now

    db.commit()

    # Notify admin (user_id=1 assumed as admin for now)
    # In production, notify all admin users
    await manager.send_to_user(current_user.id, {
        "type": "payment:sent",
        "job_id": job.id,
        "message": f"Payment marked as sent for \"{job.title}\". Awaiting admin verification.",
    })

    return {
        "message": "Payment marked as sent. Awaiting admin verification.",
        "status": job.status,
        "payment_sent_at": now.isoformat(),
    }


# ─── 3. Admin: Verify Payment Received ──────────────────

@router.post("/{job_id}/verify")
async def verify_payment(
    job_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """
    Admin verifies that payment has been received by the platform.
    Transitions: verification_pending → verified.
    """
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if job.status != JobStatus.VERIFICATION_PENDING.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Job must be in 'verification_pending' status. Current: {job.status}",
        )

    now = datetime.now(timezone.utc)

    transition = StatusTransition(
        job_id=job.id,
        from_status=JobStatus.VERIFICATION_PENDING.value,
        to_status=JobStatus.PAYOUT_RELEASED.value,
        changed_by_user_id=current_user.id,
    )
    db.add(transition)

    job.status = JobStatus.PAYOUT_RELEASED.value
    job.payment_status = "payout_released"
    job.payout_released_at = now
    job.updated_at = now

    # Update ledger
    ledger = db.query(CommissionLedger).filter(CommissionLedger.job_id == job.id).first()
    if ledger:
        ledger.payment_status = "payout_released"

    db.commit()

    # Notify employer
    await manager.send_to_user(job.employer_id, {
        "type": "payment:verified",
        "job_id": job.id,
        "message": f"Payment for \"{job.title}\" has been verified. Payout released to worker.",
    })
    # Notify worker
    if job.allotted_labor_id:
        await manager.send_to_user(job.allotted_labor_id, {
            "type": "payment:payout",
            "job_id": job.id,
            "amount": job.worker_payout_paise / 100,
            "message": f"₹{job.worker_payout_paise / 100:.2f} payout released for \"{job.title}\"!",
        })

    return {
        "message": "Payment verified and payout released to worker.",
        "status": job.status,
        "worker_payout": job.worker_payout_paise / 100,
        "platform_commission": job.platform_commission_paise / 100,
    }


# ─── 4. Admin: Mark Job as Fully Completed ──────────────

@router.post("/{job_id}/release-payout")
async def release_payout(
    job_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """
    Admin marks job as fully completed.
    Transitions: payout_released → payment_completed.
    """
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if job.status != JobStatus.PAYOUT_RELEASED.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Job must be in 'payout_released' status. Current: {job.status}",
        )

    now = datetime.now(timezone.utc)

    transition = StatusTransition(
        job_id=job.id,
        from_status=JobStatus.PAYOUT_RELEASED.value,
        to_status=JobStatus.PAYMENT_COMPLETED.value,
        changed_by_user_id=current_user.id,
    )
    db.add(transition)

    job.status = JobStatus.PAYMENT_COMPLETED.value
    job.payment_status = "completed"
    job.updated_at = now

    # Update ledger
    ledger = db.query(CommissionLedger).filter(CommissionLedger.job_id == job.id).first()
    if ledger:
        ledger.payment_status = "completed"

    db.commit()

    # Notify both parties
    await manager.send_to_user(job.employer_id, {
        "type": "payment:completed",
        "job_id": job.id,
        "message": f"Job \"{job.title}\" is now fully completed.",
    })
    if job.allotted_labor_id:
        await manager.send_to_user(job.allotted_labor_id, {
            "type": "payment:completed",
            "job_id": job.id,
            "message": f"Job \"{job.title}\" is now fully completed. Thank you!",
        })

    return {
        "message": "Payout released. Job payment completed.",
        "status": job.status,
        "worker_payout": job.worker_payout_paise / 100,
        "platform_commission": job.platform_commission_paise / 100,
        "payout_released_at": now.isoformat(),
    }


# ─── 5. Admin: List Pending Payments ────────────────────

@router.get("/admin/pending")
def get_pending_payments(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Admin: list all jobs awaiting verification or payout."""
    pending_statuses = [
        JobStatus.VERIFICATION_PENDING.value,
        JobStatus.VERIFIED.value,
    ]
    jobs = (
        db.query(Job)
        .filter(Job.status.in_(pending_statuses))
        .order_by(Job.updated_at.desc())
        .all()
    )

    result = []
    for job in jobs:
        employer = job.employer
        labor = job.allotted_labor
        result.append({
            "id": job.id,
            "title": job.title,
            "status": job.status,
            "employer_name": employer.full_name if employer else None,
            "worker_name": labor.full_name if labor else None,
            "budget": job.budget_paise / 100,
            "platform_commission": job.platform_commission_paise / 100,
            "worker_payout": job.worker_payout_paise / 100,
            "payment_method": job.payment_method,
            "payment_sent_at": job.payment_sent_at.isoformat() if job.payment_sent_at else None,
            "created_at": job.created_at.isoformat() if job.created_at else None,
        })

    return {"jobs": result, "total": len(result)}


# ─── 6. Commission Breakdown (any auth user) ────────────

@router.get("/commission/{job_id}")
def get_commission_breakdown(
    job_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get commission breakdown for a job."""
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    return {
        "budget": job.budget_paise / 100,
        "platform_commission": job.platform_commission_paise / 100,
        "worker_payout": job.worker_payout_paise / 100,
        "employer_total": job.employer_total_paise / 100,
        "platform_upi_id": PLATFORM_UPI_ID,
        "platform_upi_name": PLATFORM_UPI_NAME,
        "payment_status": job.payment_status,
        "currency": "INR",
    }


# ─── 7. Platform Config (public) ────────────────────────

@router.get("/platform-info")
def get_platform_info():
    """Public endpoint: returns platform UPI details."""
    return {
        "upi_id": PLATFORM_UPI_ID,
        "upi_name": PLATFORM_UPI_NAME,
    }
