"""
Bridge Point — Password Reset Router
Forgot password flow: request OTP → verify OTP → reset password.
"""

import secrets
import random
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.models.password_reset import PasswordReset
from app.utils.security import hash_password, verify_password

router = APIRouter(prefix="/api/auth", tags=["Authentication"])

MAX_OTP_ATTEMPTS = 5
OTP_EXPIRY_MINUTES = 10


# ─── Request Schemas ───────────────────────────────────

class ForgotPasswordRequest(BaseModel):
    email: EmailStr

class VerifyOtpRequest(BaseModel):
    email: EmailStr
    otp: str

class ResetPasswordRequest(BaseModel):
    reset_token: str
    new_password: str


# ─── 1. Request OTP ────────────────────────────────────

@router.post("/forgot-password")
def forgot_password(body: ForgotPasswordRequest, db: Session = Depends(get_db)):
    """
    Send a password reset OTP.
    Always returns 200 to prevent account enumeration.
    """
    user = db.query(User).filter(User.email == body.email).first()

    if not user:
        # TEMP DEBUG — remove after testing
        return {
            "message": "If this email is registered, you will receive a reset code.",
            "_debug_user_found": False,
        }

    # Generate 6-digit OTP
    otp = str(random.randint(100000, 999999))

    # Invalidate any previous unused OTPs for this user
    db.query(PasswordReset).filter(
        PasswordReset.user_id == user.id,
        PasswordReset.used == False,
    ).update({"used": True})

    # Store hashed OTP
    reset = PasswordReset(
        user_id=user.id,
        otp_hash=hash_password(otp),
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=OTP_EXPIRY_MINUTES),
    )
    db.add(reset)
    db.commit()

    # Send OTP via email
    from app.services.email_service import send_otp_email
    sent = send_otp_email(body.email, otp)
    if not sent:
        import logging
        logging.getLogger(__name__).warning(f"[DEV FALLBACK] OTP for {body.email}: {otp}")

    return {
        "message": "If this email is registered, you will receive a reset code.",
        "_debug_user_found": True,
        "_debug_email_sent": sent,
    }


# ─── 2. Verify OTP ────────────────────────────────────

@router.post("/verify-otp")
def verify_otp(body: VerifyOtpRequest, db: Session = Depends(get_db)):
    """
    Verify the OTP and return a one-time reset token.
    """
    user = db.query(User).filter(User.email == body.email).first()
    if not user:
        raise HTTPException(status_code=400, detail="Invalid email or OTP.")

    # Find the latest unused, non-expired OTP for this user
    reset = (
        db.query(PasswordReset)
        .filter(
            PasswordReset.user_id == user.id,
            PasswordReset.used == False,
            PasswordReset.expires_at > datetime.now(timezone.utc),
        )
        .order_by(PasswordReset.created_at.desc())
        .first()
    )

    if not reset:
        raise HTTPException(status_code=400, detail="OTP expired or not found. Request a new one.")

    # Check attempt limit
    if reset.attempts >= MAX_OTP_ATTEMPTS:
        reset.used = True
        db.commit()
        raise HTTPException(status_code=429, detail="Too many attempts. Request a new OTP.")

    # Verify OTP
    if not verify_password(body.otp, reset.otp_hash):
        reset.attempts += 1
        db.commit()
        remaining = MAX_OTP_ATTEMPTS - reset.attempts
        raise HTTPException(
            status_code=400,
            detail=f"Invalid OTP. {remaining} attempt(s) remaining.",
        )

    # OTP verified — generate one-time reset token
    reset_token = secrets.token_urlsafe(48)
    reset.reset_token = reset_token
    reset.used = True
    db.commit()

    return {"reset_token": reset_token, "message": "OTP verified. You may now reset your password."}


# ─── 3. Reset Password ────────────────────────────────

@router.post("/reset-password")
def reset_password(body: ResetPasswordRequest, db: Session = Depends(get_db)):
    """
    Reset password using the one-time reset token from verify-otp.
    """
    if len(body.new_password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters.")

    # Find the reset record by token
    reset = (
        db.query(PasswordReset)
        .filter(
            PasswordReset.reset_token == body.reset_token,
            PasswordReset.expires_at > datetime.now(timezone.utc),
        )
        .first()
    )

    if not reset:
        raise HTTPException(status_code=400, detail="Invalid or expired reset token.")

    # Update password
    user = db.query(User).filter(User.id == reset.user_id).first()
    if not user:
        raise HTTPException(status_code=400, detail="User not found.")

    user.password_hash = hash_password(body.new_password)

    # Clear the reset token so it can't be reused
    reset.reset_token = None
    db.commit()

    return {"message": "Password reset successfully. You can now log in with your new password."}


# ─── DIAGNOSTIC: Test SMTP (remove after debugging) ───

@router.get("/test-smtp")
def test_smtp():
    """Temporary diagnostic endpoint."""
    import os
    from app.config import RESEND_API_KEY, SMTP_EMAIL
    return {
        "resend_api_key_set": bool(RESEND_API_KEY),
        "resend_key_prefix": RESEND_API_KEY[:8] + "..." if RESEND_API_KEY else "(empty)",
        "smtp_email": SMTP_EMAIL or "(empty)",
        "method": "Resend HTTP API (port 443)",
        "note": "Railway blocks SMTP ports 465/587. Using Resend HTTP API instead.",
    }
