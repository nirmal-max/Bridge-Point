"""
Bridge Point — Email Service
Sends transactional emails via Gmail SMTP.

Required env vars:
  SMTP_EMAIL    — your Gmail address (e.g. iitian.nirmal482@gmail.com)
  SMTP_PASSWORD — Gmail App Password (NOT your regular password)
"""

import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from app.config import SMTP_EMAIL, SMTP_PASSWORD

_logger = logging.getLogger(__name__)

SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 587


def send_otp_email(to_email: str, otp: str) -> bool:
    """
    Send a 6-digit OTP to the given email address.
    Returns True on success, False on failure (logged but not raised).
    """
    if not SMTP_EMAIL or not SMTP_PASSWORD:
        _logger.warning(
            "[EMAIL] SMTP_EMAIL or SMTP_PASSWORD not set. OTP NOT sent to %s. OTP: %s",
            to_email, otp,
        )
        return False

    subject = "BridgePoint — Your Password Reset Code"

    html_body = f"""
    <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 480px; margin: 0 auto; padding: 40px 20px;">
        <h2 style="color: #1a1a1a; font-size: 24px; margin-bottom: 8px;">Password Reset</h2>
        <p style="color: #666; font-size: 15px; margin-bottom: 24px;">
            You requested a password reset for your BridgePoint account. Use the code below:
        </p>
        <div style="background: #f5f5f7; border-radius: 12px; padding: 24px; text-align: center; margin-bottom: 24px;">
            <span style="font-size: 36px; font-weight: 700; letter-spacing: 8px; color: #1a1a1a; font-family: monospace;">
                {otp}
            </span>
        </div>
        <p style="color: #999; font-size: 13px;">
            This code expires in 10 minutes. If you didn't request this, ignore this email.
        </p>
        <hr style="border: none; border-top: 1px solid #eee; margin: 24px 0;" />
        <p style="color: #bbb; font-size: 12px;">BridgePoint — Work that matters.</p>
    </div>
    """

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"BridgePoint <{SMTP_EMAIL}>"
    msg["To"] = to_email

    # Plain text fallback
    msg.attach(MIMEText(f"Your BridgePoint password reset code is: {otp}\n\nExpires in 10 minutes.", "plain"))
    msg.attach(MIMEText(html_body, "html"))

    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_EMAIL, SMTP_PASSWORD)
            server.send_message(msg)
        _logger.info("[EMAIL] OTP sent to %s", to_email)
        return True
    except Exception as e:
        _logger.error("[EMAIL] Failed to send OTP to %s: %s", to_email, str(e))
        return False
