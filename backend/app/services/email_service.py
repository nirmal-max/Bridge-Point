"""
Bridge Point — Email Service
Sends transactional emails via Gmail SMTP.

Required env vars:
  SMTP_EMAIL    — your Gmail address
  SMTP_PASSWORD — Gmail App Password (NOT your regular password)
"""

import smtplib
import ssl
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from app.config import SMTP_EMAIL, SMTP_PASSWORD

_logger = logging.getLogger(__name__)


def send_otp_email(to_email: str, otp: str) -> bool:
    if not SMTP_EMAIL or not SMTP_PASSWORD:
        _logger.warning("[EMAIL] SMTP not configured. OTP for %s: %s", to_email, otp)
        return False

    password = SMTP_PASSWORD.replace(" ", "")

    html_body = f"""
    <div style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;max-width:480px;margin:0 auto;padding:40px 20px;">
        <h2 style="color:#1a1a1a;font-size:24px;margin-bottom:8px;">Password Reset</h2>
        <p style="color:#666;font-size:15px;margin-bottom:24px;">Use this code to reset your BridgePoint password:</p>
        <div style="background:#f5f5f7;border-radius:12px;padding:24px;text-align:center;margin-bottom:24px;">
            <span style="font-size:36px;font-weight:700;letter-spacing:8px;color:#1a1a1a;font-family:monospace;">{otp}</span>
        </div>
        <p style="color:#999;font-size:13px;">This code expires in 10 minutes. If you didn't request this, ignore this email.</p>
        <hr style="border:none;border-top:1px solid #eee;margin:24px 0;"/>
        <p style="color:#bbb;font-size:12px;">BridgePoint — Work that matters.</p>
    </div>
    """

    msg = MIMEMultipart("alternative")
    msg["Subject"] = "BridgePoint — Your Password Reset Code"
    msg["From"] = f"BridgePoint <{SMTP_EMAIL}>"
    msg["To"] = to_email
    msg.attach(MIMEText(f"Your BridgePoint reset code is: {otp}\nExpires in 10 minutes.", "plain"))
    msg.attach(MIMEText(html_body, "html"))

    # Method 1: SSL on port 465 (works on Railway/cloud)
    try:
        _logger.info("[EMAIL] Trying SSL port 465 to %s", to_email)
        ctx = ssl.create_default_context()
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=ctx, timeout=15) as s:
            s.login(SMTP_EMAIL, password)
            s.send_message(msg)
        _logger.info("[EMAIL] ✅ OTP sent to %s via SSL 465", to_email)
        return True
    except Exception as e:
        _logger.warning("[EMAIL] SSL 465 failed: %s — trying TLS 587", str(e))

    # Method 2: TLS on port 587 (fallback)
    try:
        with smtplib.SMTP("smtp.gmail.com", 587, timeout=15) as s:
            s.starttls(context=ssl.create_default_context())
            s.login(SMTP_EMAIL, password)
            s.send_message(msg)
        _logger.info("[EMAIL] ✅ OTP sent to %s via TLS 587", to_email)
        return True
    except Exception as e:
        _logger.error("[EMAIL] ❌ Both methods failed for %s: %s", to_email, str(e))
        return False
