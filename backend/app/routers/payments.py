"""
Bridge Point — Payment Router
Cashfree Payment Gateway + Cashfree Payouts Integration.

Flow:
  1. Employer creates Cashfree order → status: payment_pending
  2. Employer completes Cashfree Checkout → frontend gets payment_session_id
  3. Server verifies payment via Cashfree API → status: payment_paid
  4. Admin initiates payout to worker → status: payout_transferred
  5. Job marked completed → status: payment_completed
"""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from datetime import datetime, timezone
from typing import Optional
import time

from app.database import get_db
from app.models.user import User
from app.models.job import Job
from app.models.payment import Payment
from app.models.commission import CommissionLedger
from app.models.status_transition import StatusTransition
from app.services.state_machine import JobStatus, validate_transition
from app.services.commission import calculate_commission
from app.services.websocket_manager import manager
from app.services import cashfree_service
from app.config import CASHFREE_APP_ID, CASHFREE_ENVIRONMENT, PLATFORM_UPI_ID, PLATFORM_UPI_NAME
from app.utils.deps import get_current_user, require_employer, require_admin

router = APIRouter(prefix="/api/payments", tags=["Payments"])


# ─── Request Bodies ──────────────────────────────────────

class CreateOrderRequest(BaseModel):
    job_id: int


class VerifyPaymentRequest(BaseModel):
    job_id: int
    cashfree_order_id: str


class InitiateTransferRequest(BaseModel):
    job_id: int


# ─── Legacy: PaymentInitiate (kept for backward compat) ──

class PaymentInitiate(BaseModel):
    job_id: int
    payment_method: str  # "upi", "cash", or "cashfree"


# ─── 1. Create Cashfree Order ───────────────────────────

@router.post("/create-order")
def create_payment_order(
    payload: CreateOrderRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_employer),
):
    """
    Employer initiates payment for a completed job.
    Creates a Cashfree order and transitions job to payment_pending.
    Returns payment_session_id for Cashfree Checkout frontend.
    """
    job = db.query(Job).filter(
        Job.id == payload.job_id,
        Job.employer_id == current_user.id,
    ).first()
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
            detail="No worker assigned to this job",
        )

    # Idempotency: if payment already exists, return existing order
    existing_payment = db.query(Payment).filter(Payment.job_id == job.id).first()
    if existing_payment and existing_payment.cashfree_order_id:
        return {
            "order_id": existing_payment.cashfree_order_id,
            "payment_session_id": "",  # Frontend should re-fetch if needed
            "amount": existing_payment.amount_total_paise / 100,
            "currency": "INR",
            "job_id": job.id,
            "employer_total": existing_payment.amount_total_paise / 100,
            "platform_commission": existing_payment.platform_commission_paise / 100,
            "worker_payout": existing_payment.worker_payout_paise / 100,
            "status": job.status,
            "environment": CASHFREE_ENVIRONMENT,
        }

    # Create Cashfree order — amount is what employer pays (= budget for 3% model)
    employer_total_paise = job.employer_total_paise
    employer_total_rupees = employer_total_paise / 100
    order_id = f"bp_job_{job.id}_{int(time.time())}"

    try:
        order = cashfree_service.create_order(
            order_id=order_id,
            amount=employer_total_rupees,
            currency="INR",
            customer_id=str(current_user.id),
            customer_name=current_user.full_name or "Employer",
            customer_email=current_user.email or "employer@bridgepoint.in",
            customer_phone=current_user.phone or "9999999999",
            notes={"job_id": str(job.id), "worker_id": str(job.allotted_labor_id)},
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to create Cashfree order: {str(e)}",
        )

    # Create Payment record
    payment = Payment(
        job_id=job.id,
        employer_id=current_user.id,
        worker_id=job.allotted_labor_id,
        cashfree_order_id=order.get("order_id", order_id),
        amount_total_paise=employer_total_paise,
        platform_commission_paise=job.platform_commission_paise,
        worker_payout_paise=job.worker_payout_paise,
        payment_status="pending",
    )
    db.add(payment)

    # Also create commission ledger (backward compat)
    existing_ledger = db.query(CommissionLedger).filter(
        CommissionLedger.job_id == job.id
    ).first()
    if not existing_ledger:
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
            payment_method="cashfree",
            payment_status="initiated",
        )
        db.add(ledger)

    # Transition: work_completed → payment_pending
    transition = StatusTransition(
        job_id=job.id,
        from_status=JobStatus.WORK_COMPLETED.value,
        to_status=JobStatus.PAYMENT_PENDING.value,
        changed_by_user_id=current_user.id,
    )
    db.add(transition)

    job.status = JobStatus.PAYMENT_PENDING.value
    job.payment_method = "cashfree"
    job.payment_status = "pending"
    job.cashfree_order_id = order.get("order_id", order_id)
    job.updated_at = datetime.now(timezone.utc)

    db.commit()

    return {
        "order_id": order.get("order_id", order_id),
        "payment_session_id": order.get("payment_session_id", ""),
        "amount": employer_total_rupees,
        "currency": "INR",
        "job_id": job.id,
        "employer_total": employer_total_rupees,
        "platform_commission": job.platform_commission_paise / 100,
        "worker_payout": job.worker_payout_paise / 100,
        "status": job.status,
        "environment": CASHFREE_ENVIRONMENT,
    }


# ─── 2. Verify Payment (Server-Side) ────────────────────

@router.post("/verify")
async def verify_payment(
    payload: VerifyPaymentRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_employer),
):
    """
    After Cashfree Checkout success, frontend sends order_id.
    Server verifies payment status via Cashfree API.
    NEVER trust frontend confirmation alone.
    Transitions: payment_pending → payment_paid.
    """
    job = db.query(Job).filter(
        Job.id == payload.job_id,
        Job.employer_id == current_user.id,
    ).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found or not yours")

    if job.status != JobStatus.PAYMENT_PENDING.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Job must be in 'payment_pending' status. Current: {job.status}",
        )

    # Find the payment record
    payment = db.query(Payment).filter(Payment.job_id == job.id).first()
    if not payment:
        raise HTTPException(status_code=404, detail="Payment record not found")

    # Verify order ID matches
    if payment.cashfree_order_id != payload.cashfree_order_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Order ID mismatch",
        )

    # ─── CRITICAL: Server-side verification via Cashfree API ─────
    try:
        result = cashfree_service.verify_payment(payload.cashfree_order_id)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to verify payment: {str(e)}",
        )

    if not result.get("verified"):
        payment.payment_status = "failed"
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Payment verification failed. Order status: {result.get('order_status')}",
        )

    now = datetime.now(timezone.utc)

    # Update payment record
    payment.cashfree_payment_id = result.get("payment_id", "")
    payment.payment_status = "paid"
    payment.verified_at = now

    # Transition: payment_pending → payment_paid
    transition = StatusTransition(
        job_id=job.id,
        from_status=JobStatus.PAYMENT_PENDING.value,
        to_status=JobStatus.PAYMENT_PAID.value,
        changed_by_user_id=current_user.id,
    )
    db.add(transition)

    job.status = JobStatus.PAYMENT_PAID.value
    job.payment_status = "paid"
    job.updated_at = now

    # Update ledger
    ledger = db.query(CommissionLedger).filter(CommissionLedger.job_id == job.id).first()
    if ledger:
        ledger.payment_status = "paid"

    db.commit()

    # Notify both parties via WebSocket
    await manager.send_to_user(current_user.id, {
        "type": "payment:verified",
        "job_id": job.id,
        "message": f"Payment verified for \"{job.title}\".",
    })
    if job.allotted_labor_id:
        await manager.send_to_user(job.allotted_labor_id, {
            "type": "payment:verified",
            "job_id": job.id,
            "message": f"Payment received for \"{job.title}\". Payout will be transferred shortly.",
        })

    return {
        "message": "Payment verified successfully.",
        "status": job.status,
        "payment_id": result.get("payment_id", ""),
        "worker_payout": job.worker_payout_paise / 100,
        "platform_commission": job.platform_commission_paise / 100,
    }


# ─── 3. Admin: Initiate Worker Payout ───────────────────

@router.post("/initiate-transfer")
async def initiate_transfer(
    payload: InitiateTransferRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """
    Admin initiates payout to worker via Cashfree Payouts.
    Transitions: payment_paid → payout_transferred.
    """
    job = db.query(Job).filter(Job.id == payload.job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if job.status != JobStatus.PAYMENT_PAID.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Job must be in 'payment_paid' status. Current: {job.status}",
        )

    payment = db.query(Payment).filter(Payment.job_id == job.id).first()
    if not payment or not payment.cashfree_payment_id:
        raise HTTPException(status_code=404, detail="Payment record or payment ID not found")

    # Get worker details
    worker = db.query(User).filter(User.id == job.allotted_labor_id).first()
    if not worker:
        raise HTTPException(status_code=404, detail="Worker not found")

    # Worker needs bank account or UPI for payout
    has_bank = worker.bank_account_number and worker.bank_ifsc
    has_upi = worker.payout_upi_id

    if not has_bank and not has_upi:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Worker has no bank account or UPI ID configured for payout. "
                   "Worker must update their payout details first.",
        )

    # Add worker as beneficiary in Cashfree
    beneficiary_id = f"bp_worker_{worker.id}"
    try:
        cashfree_service.add_beneficiary(
            beneficiary_id=beneficiary_id,
            name=worker.full_name,
            email=worker.email,
            phone=worker.phone,
            bank_account=worker.bank_account_number if has_bank else None,
            ifsc=worker.bank_ifsc if has_bank else None,
            upi_id=worker.payout_upi_id if has_upi else None,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to add worker as beneficiary: {str(e)}",
        )

    # Initiate payout
    transfer_id = f"bp_payout_job_{job.id}_{int(time.time())}"
    payout_amount = payment.worker_payout_paise / 100
    transfer_mode = "upi" if has_upi and not has_bank else "banktransfer"

    try:
        payout = cashfree_service.initiate_payout(
            transfer_id=transfer_id,
            beneficiary_id=beneficiary_id,
            amount=payout_amount,
            transfer_mode=transfer_mode,
            remarks=f"BridgePoint payout for job {job.id}: {job.title}",
        )
        payment.cashfree_payout_id = transfer_id
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to initiate payout: {str(e)}",
        )

    now = datetime.now(timezone.utc)

    payment.payment_status = "payout_initiated"
    payment.transferred_at = now

    # Transition: payment_paid → payout_transferred
    transition = StatusTransition(
        job_id=job.id,
        from_status=JobStatus.PAYMENT_PAID.value,
        to_status=JobStatus.PAYOUT_TRANSFERRED.value,
        changed_by_user_id=current_user.id,
    )
    db.add(transition)

    job.status = JobStatus.PAYOUT_TRANSFERRED.value
    job.payment_status = "payout_transferred"
    job.payout_released_at = now
    job.updated_at = now

    # Update ledger
    ledger = db.query(CommissionLedger).filter(CommissionLedger.job_id == job.id).first()
    if ledger:
        ledger.payment_status = "payout_released"

    db.commit()

    # Notify both parties
    await manager.send_to_user(job.employer_id, {
        "type": "payment:payout_transferred",
        "job_id": job.id,
        "message": f"Payout of ₹{payout_amount:.2f} transferred for \"{job.title}\".",
    })
    if job.allotted_labor_id:
        await manager.send_to_user(job.allotted_labor_id, {
            "type": "payment:payout",
            "job_id": job.id,
            "amount": payout_amount,
            "message": f"₹{payout_amount:.2f} payout transferred for \"{job.title}\"!",
        })

    return {
        "message": "Payout transfer initiated.",
        "status": job.status,
        "worker_payout": payout_amount,
        "platform_commission": job.platform_commission_paise / 100,
        "payout_transferred_at": now.isoformat(),
    }


# ─── 4. Admin: Mark Job Completed ───────────────────────

@router.post("/{job_id}/complete")
async def mark_completed(
    job_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """
    Admin marks job as fully completed after payout transfer.
    Transitions: payout_transferred → payment_completed.
    """
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if job.status != JobStatus.PAYOUT_TRANSFERRED.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Job must be in 'payout_transferred' status. Current: {job.status}",
        )

    now = datetime.now(timezone.utc)

    transition = StatusTransition(
        job_id=job.id,
        from_status=JobStatus.PAYOUT_TRANSFERRED.value,
        to_status=JobStatus.PAYMENT_COMPLETED.value,
        changed_by_user_id=current_user.id,
    )
    db.add(transition)

    job.status = JobStatus.PAYMENT_COMPLETED.value
    job.payment_status = "completed"
    job.updated_at = now

    # Update payment record
    payment = db.query(Payment).filter(Payment.job_id == job.id).first()
    if payment:
        payment.payment_status = "payout_completed"

    # Update ledger
    ledger = db.query(CommissionLedger).filter(CommissionLedger.job_id == job.id).first()
    if ledger:
        ledger.payment_status = "completed"

    db.commit()

    return {
        "message": "Job marked as completed.",
        "status": job.status,
    }


# ─── 5. Admin: List Pending Payments ────────────────────

@router.get("/admin/pending")
def get_pending_payments(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Admin: list all jobs awaiting payment action."""
    pending_statuses = [
        JobStatus.PAYMENT_PENDING.value,
        JobStatus.PAYMENT_PAID.value,
        JobStatus.PAYOUT_TRANSFERRED.value,
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
        payment = db.query(Payment).filter(Payment.job_id == job.id).first()
        result.append({
            "id": job.id,
            "title": job.title,
            "status": job.status,
            "employer_name": employer.full_name if employer else None,
            "worker_name": labor.full_name if labor else None,
            "budget": job.budget_paise / 100,
            "employer_total": job.employer_total_paise / 100,
            "platform_commission": job.platform_commission_paise / 100,
            "worker_payout": job.worker_payout_paise / 100,
            "payment_method": job.payment_method,
            "cashfree_order_id": payment.cashfree_order_id if payment else None,
            "cashfree_payment_id": payment.cashfree_payment_id if payment else None,
            "payment_status": payment.payment_status if payment else None,
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
        "employer_commission": job.employer_commission_paise / 100,
        "employer_total": job.employer_total_paise / 100,
        "labor_commission": job.labor_commission_paise / 100,
        "worker_payout": job.worker_payout_paise / 100,
        "platform_commission": job.platform_commission_paise / 100,
        "payment_status": job.payment_status,
        "currency": "INR",
    }


# ─── 7. Platform Config (public) ────────────────────────

@router.get("/platform-info")
def get_platform_info():
    """Public endpoint: returns platform payment info."""
    return {
        "payment_gateway": "cashfree",
        "environment": CASHFREE_ENVIRONMENT,
        "upi_id": PLATFORM_UPI_ID,
        "upi_name": PLATFORM_UPI_NAME,
    }


# ─── 8. Employer: Mark UPI Payment Sent ─────────────────

class MarkPaymentSentBody(BaseModel):
    upi_reference: str  # UPI Transaction Reference (UTR)

@router.post("/{job_id}/mark-sent")
async def mark_payment_sent(
    job_id: int,
    body: MarkPaymentSentBody,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_employer),
):
    """
    Employer confirms they sent UPI payment to the platform.
    Stores the UTR reference. Job stays in payment_pending until admin verifies.
    """
    job = db.query(Job).filter(Job.id == job_id, Job.employer_id == current_user.id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found or not yours")

    if job.status not in (JobStatus.PAYMENT_PENDING.value, "payment_in_process"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Job must be in 'payment_pending' status. Current: {job.status}",
        )

    # Validate UTR: non-empty, numeric, 12+ chars
    utr = body.upi_reference.strip()
    if not utr:
        raise HTTPException(status_code=400, detail="UPI Transaction Reference (UTR) is required.")
    if not utr.replace(" ", "").isdigit():
        raise HTTPException(status_code=400, detail="UTR must contain only digits.")
    if len(utr.replace(" ", "")) < 12:
        raise HTTPException(status_code=400, detail="UTR must be at least 12 digits.")

    now = datetime.now(timezone.utc)

    job.payment_status = "sent"
    job.payment_sent_at = now
    job.updated_at = now

    # Store UTR in commission ledger
    ledger = db.query(CommissionLedger).filter(CommissionLedger.job_id == job.id).first()
    if ledger:
        ledger.upi_reference = utr

    db.commit()

    # Notify
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


# ─── 9. Admin: Verify UPI Payment ───────────────────────

@router.post("/{job_id}/verify-upi")
async def admin_verify_upi(
    job_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """
    Admin verifies UPI payment received (checks UTR in bank statement).
    Transitions: payment_pending → payment_paid.
    """
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if job.status not in (JobStatus.PAYMENT_PENDING.value, "payment_in_process",
                          "verification_pending"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Job must be in payment_pending status. Current: {job.status}",
        )

    now = datetime.now(timezone.utc)

    transition = StatusTransition(
        job_id=job.id,
        from_status=job.status,
        to_status=JobStatus.PAYMENT_PAID.value,
        changed_by_user_id=current_user.id,
    )
    db.add(transition)

    job.status = JobStatus.PAYMENT_PAID.value
    job.payment_status = "paid"
    job.updated_at = now

    ledger = db.query(CommissionLedger).filter(CommissionLedger.job_id == job.id).first()
    if ledger:
        ledger.payment_status = "verified"

    db.commit()

    # Notify both
    await manager.send_to_user(job.employer_id, {
        "type": "payment:verified",
        "job_id": job.id,
        "message": f"Payment for \"{job.title}\" verified by admin.",
    })
    if job.allotted_labor_id:
        await manager.send_to_user(job.allotted_labor_id, {
            "type": "payment:verified",
            "job_id": job.id,
            "message": f"Payment for \"{job.title}\" verified. Payout coming soon!",
        })

    return {
        "message": "Payment verified.",
        "status": job.status,
        "worker_payout": job.worker_payout_paise / 100,
        "platform_commission": job.platform_commission_paise / 100,
    }


# ═══════════════════════════════════════════════════════════
# LEGACY ENDPOINTS (backward compat — will be phased out)
# ═══════════════════════════════════════════════════════════

@router.post("/initiate")
def initiate_payment_legacy(
    payload: PaymentInitiate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_employer),
):
    """
    LEGACY: Initiate payment via UPI/cash (kept for backward compat).
    New clients should use POST /create-order for Cashfree.
    """
    if payload.payment_method == "cashfree":
        # Redirect to new flow
        return create_payment_order(
            CreateOrderRequest(job_id=payload.job_id), db, current_user
        )

    # Legacy UPI/cash flow
    job = db.query(Job).filter(
        Job.id == payload.job_id,
        Job.employer_id == current_user.id,
    ).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found or not yours")

    if job.status != JobStatus.WORK_COMPLETED.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Job must be in 'work_completed' status. Current: {job.status}",
        )

    # Transition to payment_pending
    transition = StatusTransition(
        job_id=job.id,
        from_status=JobStatus.WORK_COMPLETED.value,
        to_status=JobStatus.PAYMENT_PENDING.value,
        changed_by_user_id=current_user.id,
    )
    db.add(transition)

    job.status = JobStatus.PAYMENT_PENDING.value
    job.payment_method = payload.payment_method
    job.payment_status = "pending"
    job.updated_at = datetime.now(timezone.utc)

    db.commit()

    return {
        "message": "Payment initiated.",
        "status": job.status,
        "platform_upi_id": PLATFORM_UPI_ID,
        "platform_upi_name": PLATFORM_UPI_NAME,
        "amount": job.budget_paise / 100,
        "employer_total": job.employer_total_paise / 100,
        "platform_commission": job.platform_commission_paise / 100,
        "worker_payout": job.worker_payout_paise / 100,
    }
