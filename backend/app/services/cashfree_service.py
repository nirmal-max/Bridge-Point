"""
Bridge Point — Cashfree Payment Service
REST API wrapper for Cashfree Payment Gateway and Cashfree Payouts.

Payment Gateway: Collects money from employer
Payouts: Sends money to worker (bank account or UPI)

All monetary values are in RUPEES (float), not paise.
Cashfree uses rupees natively.
"""

import hmac
import hashlib
import logging
import time
from typing import Optional

import httpx

from app.config import (
    CASHFREE_APP_ID,
    CASHFREE_SECRET_KEY,
    CASHFREE_API_BASE,
    CASHFREE_PAYOUT_BASE,
    CASHFREE_ENVIRONMENT,
)

_logger = logging.getLogger(__name__)

# Cashfree API version header
_API_VERSION = "2023-08-01"


def _pg_headers() -> dict:
    """Headers for Cashfree Payment Gateway API."""
    return {
        "x-client-id": CASHFREE_APP_ID,
        "x-client-secret": CASHFREE_SECRET_KEY,
        "x-api-version": _API_VERSION,
        "Content-Type": "application/json",
    }


def _payout_headers() -> dict:
    """Headers for Cashfree Payouts API."""
    return {
        "x-client-id": CASHFREE_APP_ID,
        "x-client-secret": CASHFREE_SECRET_KEY,
        "x-api-version": _API_VERSION,
        "Content-Type": "application/json",
    }


def _check_config():
    """Raise if Cashfree credentials are not configured."""
    if not CASHFREE_APP_ID or not CASHFREE_SECRET_KEY:
        raise RuntimeError(
            "CASHFREE_APP_ID and CASHFREE_SECRET_KEY must be set "
            "in environment variables."
        )


# ─── Payment Gateway: Create Order ──────────────────────

def create_order(
    order_id: str,
    amount: float,
    currency: str,
    customer_id: str,
    customer_name: str,
    customer_email: str,
    customer_phone: str,
    return_url: str | None = None,
    notes: dict | None = None,
) -> dict:
    """
    Create a Cashfree payment order.

    Args:
        order_id: Unique order ID (e.g., "bp_job_42_1709999999")
        amount: Amount in rupees (e.g., 800.00)
        currency: "INR"
        customer_id: Employer user ID as string
        customer_name: Employer full name
        customer_email: Employer email
        customer_phone: Employer phone
        return_url: URL to redirect after payment
        notes: Optional metadata

    Returns:
        Dict with 'cf_order_id', 'order_id', 'payment_session_id', etc.
    """
    _check_config()

    payload = {
        "order_id": order_id,
        "order_amount": amount,
        "order_currency": currency,
        "customer_details": {
            "customer_id": customer_id,
            "customer_name": customer_name,
            "customer_email": customer_email,
            "customer_phone": customer_phone,
        },
        "order_meta": {
            "return_url": return_url or "",
            "notify_url": "",  # Set via webhook config
        },
        "order_note": str(notes) if notes else "",
    }

    with httpx.Client(timeout=30) as client:
        resp = client.post(
            f"{CASHFREE_API_BASE}/orders",
            json=payload,
            headers=_pg_headers(),
        )

    if resp.status_code not in (200, 201):
        _logger.error(f"Cashfree create_order failed: {resp.status_code} {resp.text}")
        raise RuntimeError(f"Cashfree order creation failed: {resp.text}")

    data = resp.json()
    _logger.info(f"Cashfree order created: {data.get('order_id')} for ₹{amount:.2f}")
    return data


# ─── Payment Gateway: Get Order Status ──────────────────

def get_order_status(order_id: str) -> dict:
    """
    Fetch payment status for an order from Cashfree.

    Returns:
        Dict with 'order_status' (PAID, ACTIVE, EXPIRED, etc.)
        and payment details.
    """
    _check_config()

    with httpx.Client(timeout=30) as client:
        resp = client.get(
            f"{CASHFREE_API_BASE}/orders/{order_id}",
            headers=_pg_headers(),
        )

    if resp.status_code != 200:
        _logger.error(f"Cashfree get_order failed: {resp.status_code} {resp.text}")
        raise RuntimeError(f"Cashfree order fetch failed: {resp.text}")

    return resp.json()


# ─── Payment Gateway: Get Payments for Order ────────────

def get_payments_for_order(order_id: str) -> list[dict]:
    """Fetch all payment attempts for an order."""
    _check_config()

    with httpx.Client(timeout=30) as client:
        resp = client.get(
            f"{CASHFREE_API_BASE}/orders/{order_id}/payments",
            headers=_pg_headers(),
        )

    if resp.status_code != 200:
        _logger.error(f"Cashfree get_payments failed: {resp.status_code} {resp.text}")
        return []

    return resp.json()


# ─── Payment Gateway: Verify Payment ────────────────────

def verify_payment(order_id: str) -> dict:
    """
    Verify a payment by checking order status with Cashfree.
    Server-side verification — NEVER trust frontend alone.

    Returns:
        Dict with 'verified' (bool), 'order_status', 'payment_id', etc.
    """
    _check_config()

    order_data = get_order_status(order_id)
    order_status = order_data.get("order_status", "")

    payments = get_payments_for_order(order_id)
    successful_payment = None
    for p in payments:
        if p.get("payment_status") == "SUCCESS":
            successful_payment = p
            break

    return {
        "verified": order_status == "PAID",
        "order_status": order_status,
        "order_id": order_id,
        "cf_order_id": order_data.get("cf_order_id", ""),
        "payment_id": successful_payment.get("cf_payment_id", "") if successful_payment else "",
        "payment_method": successful_payment.get("payment_group", "") if successful_payment else "",
        "payment_amount": order_data.get("order_amount", 0),
    }


# ─── Payouts: Create Beneficiary ────────────────────────

def add_beneficiary(
    beneficiary_id: str,
    name: str,
    email: str,
    phone: str,
    bank_account: str | None = None,
    ifsc: str | None = None,
    upi_id: str | None = None,
) -> dict:
    """
    Add a beneficiary (worker) for Cashfree Payouts.
    Worker can receive payouts via bank transfer or UPI.
    """
    _check_config()

    payload = {
        "beneId": beneficiary_id,
        "name": name,
        "email": email,
        "phone": phone,
    }

    if bank_account and ifsc:
        payload["bankAccount"] = bank_account
        payload["ifsc"] = ifsc
    if upi_id:
        payload["vpa"] = upi_id

    with httpx.Client(timeout=30) as client:
        resp = client.post(
            f"{CASHFREE_PAYOUT_BASE}/v1/addBeneficiary",
            json=payload,
            headers=_payout_headers(),
        )

    data = resp.json()
    if resp.status_code not in (200, 201) and data.get("subCode") != "409":
        _logger.error(f"Cashfree add_beneficiary failed: {resp.status_code} {data}")
        raise RuntimeError(f"Failed to add beneficiary: {data}")

    _logger.info(f"Cashfree beneficiary added: {beneficiary_id}")
    return data


# ─── Payouts: Initiate Transfer ─────────────────────────

def initiate_payout(
    transfer_id: str,
    beneficiary_id: str,
    amount: float,
    transfer_mode: str = "banktransfer",  # "banktransfer" or "upi"
    remarks: str = "",
) -> dict:
    """
    Initiate a payout to a worker via Cashfree Payouts.

    Args:
        transfer_id: Unique transfer ID (e.g., "bp_payout_job_42")
        beneficiary_id: Worker's beneficiary ID in Cashfree
        amount: Payout amount in rupees
        transfer_mode: "banktransfer" or "upi"
        remarks: Transfer remarks

    Returns:
        Dict with 'referenceId', 'status', etc.
    """
    _check_config()

    payload = {
        "beneId": beneficiary_id,
        "amount": str(amount),
        "transferId": transfer_id,
        "transferMode": transfer_mode,
        "remarks": remarks or f"BridgePoint payout {transfer_id}",
    }

    with httpx.Client(timeout=30) as client:
        resp = client.post(
            f"{CASHFREE_PAYOUT_BASE}/v1/requestTransfer",
            json=payload,
            headers=_payout_headers(),
        )

    data = resp.json()
    if resp.status_code not in (200, 201):
        _logger.error(f"Cashfree payout failed: {resp.status_code} {data}")
        raise RuntimeError(f"Payout failed: {data}")

    _logger.info(f"Cashfree payout initiated: {transfer_id} for ₹{amount:.2f}")
    return data


# ─── Payouts: Get Transfer Status ───────────────────────

def get_payout_status(transfer_id: str) -> dict:
    """Check the status of a payout transfer."""
    _check_config()

    with httpx.Client(timeout=30) as client:
        resp = client.get(
            f"{CASHFREE_PAYOUT_BASE}/v1/getTransferStatus",
            params={"transferId": transfer_id},
            headers=_payout_headers(),
        )

    if resp.status_code != 200:
        _logger.error(f"Cashfree payout status failed: {resp.status_code} {resp.text}")
        raise RuntimeError(f"Payout status check failed: {resp.text}")

    return resp.json()


# ─── Webhook Signature Verification ─────────────────────

def verify_webhook_signature(
    raw_body: str,
    timestamp: str,
    signature: str,
) -> bool:
    """
    Verify a Cashfree webhook signature.

    Args:
        raw_body: Raw POST body as string
        timestamp: X-Cashfree-Timestamp header
        signature: X-Cashfree-Signature header

    Returns:
        True if signature matches.
    """
    if not CASHFREE_SECRET_KEY:
        _logger.warning("CASHFREE_SECRET_KEY not set — skipping webhook verification")
        return False

    data = timestamp + raw_body
    expected = hmac.new(
        CASHFREE_SECRET_KEY.encode("utf-8"),
        data.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()

    is_valid = hmac.compare_digest(expected, signature)
    if not is_valid:
        _logger.warning("Cashfree webhook signature verification FAILED")
    return is_valid
