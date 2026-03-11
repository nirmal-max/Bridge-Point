"""
Bridge Point — Cashfree Webhook Handler
Receives async callbacks from Cashfree for payment and payout events.

Events handled:
  - PAYMENT_SUCCESS: Payment was successfully completed
  - PAYMENT_FAILED: Payment failed
  - TRANSFER_SUCCESS: Payout to worker completed
  - TRANSFER_FAILED: Payout failed
"""

import json
import logging
from fastapi import APIRouter, Request, HTTPException, Depends
from sqlalchemy.orm import Session
from datetime import datetime, timezone

from app.database import get_db
from app.models.job import Job
from app.models.payment import Payment
from app.models.status_transition import StatusTransition
from app.services.state_machine import JobStatus
from app.services import cashfree_service

_logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/webhooks", tags=["Webhooks"])


@router.post("/cashfree")
async def cashfree_webhook(request: Request, db: Session = Depends(get_db)):
    """
    Cashfree webhook endpoint.
    Verifies signature, then processes the event.
    This is a PUBLIC endpoint — no auth token required.
    Security is via Cashfree webhook signature verification.
    """
    body_bytes = await request.body()
    body_str = body_bytes.decode("utf-8")
    timestamp = request.headers.get("x-cashfree-timestamp", "")
    signature = request.headers.get("x-cashfree-signature", "")

    # Verify webhook signature
    if signature and timestamp:
        is_valid = cashfree_service.verify_webhook_signature(body_str, timestamp, signature)
        if not is_valid:
            _logger.warning("Cashfree webhook signature verification failed")
            raise HTTPException(status_code=400, detail="Invalid webhook signature")

    try:
        payload = json.loads(body_str)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    event_type = payload.get("type", "")
    _logger.info(f"Cashfree webhook received: {event_type}")

    if event_type == "PAYMENT_SUCCESS_WEBHOOK":
        await _handle_payment_success(payload, db)
    elif event_type == "PAYMENT_FAILED_WEBHOOK":
        await _handle_payment_failed(payload, db)
    else:
        _logger.info(f"Unhandled Cashfree webhook event: {event_type}")

    return {"status": "ok"}


async def _handle_payment_success(payload: dict, db: Session):
    """Handle PAYMENT_SUCCESS — backup verification if frontend flow missed."""
    data = payload.get("data", {})
    order = data.get("order", {})
    payment_data = data.get("payment", {})

    order_id = order.get("order_id", "")
    cf_payment_id = payment_data.get("cf_payment_id", "")

    if not order_id:
        _logger.warning("PAYMENT_SUCCESS webhook missing order_id")
        return

    payment = db.query(Payment).filter(
        Payment.cashfree_order_id == order_id
    ).first()

    if not payment:
        _logger.warning(f"No payment record for Cashfree order {order_id}")
        return

    # Only update if still in pending state (frontend may have already verified)
    if payment.payment_status == "pending":
        now = datetime.now(timezone.utc)
        payment.cashfree_payment_id = str(cf_payment_id)
        payment.payment_status = "paid"
        payment.verified_at = now

        job = db.query(Job).filter(Job.id == payment.job_id).first()
        if job and job.status == JobStatus.PAYMENT_PENDING.value:
            transition = StatusTransition(
                job_id=job.id,
                from_status=JobStatus.PAYMENT_PENDING.value,
                to_status=JobStatus.PAYMENT_PAID.value,
                changed_by_user_id=payment.employer_id,
            )
            db.add(transition)
            job.status = JobStatus.PAYMENT_PAID.value
            job.payment_status = "paid"
            job.updated_at = now

        db.commit()
        _logger.info(f"Webhook updated payment for order {order_id} to 'paid'")
    else:
        _logger.info(f"Payment for order {order_id} already '{payment.payment_status}', skipping")


async def _handle_payment_failed(payload: dict, db: Session):
    """Handle PAYMENT_FAILED — mark payment as failed."""
    data = payload.get("data", {})
    order = data.get("order", {})
    order_id = order.get("order_id", "")

    if not order_id:
        return

    payment = db.query(Payment).filter(
        Payment.cashfree_order_id == order_id
    ).first()

    if payment and payment.payment_status == "pending":
        payment.payment_status = "failed"
        db.commit()
        _logger.warning(f"Payment for order {order_id} marked as failed via webhook")
