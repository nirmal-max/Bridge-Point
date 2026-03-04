"""
Bridge Point — Email Service
Sends transactional emails via Resend HTTP API (HTTPS port 443).
Railway blocks SMTP (ports 465/587), so we use HTTP-based email instead.

Required env var:
  RESEND_API_KEY — get from https://resend.com/api-keys
"""

import logging
import urllib.request
import urllib.error
import json

from app.config import RESEND_API_KEY, SMTP_EMAIL

_logger = logging.getLogger(__name__)

RESEND_API_URL = "https://api.resend.com/emails"


def send_otp_email(to_email: str, otp: str) -> bool:
    """Send a 6-digit OTP via Resend HTTP API. Returns True on success."""

    if not RESEND_API_KEY:
        _logger.warning("[EMAIL] RESEND_API_KEY not set. OTP for %s: %s", to_email, otp)
        return False

    # Use the verified sender or Resend's default
    from_email = SMTP_EMAIL or "BridgePoint <onboarding@resend.dev>"
    if SMTP_EMAIL and "@" in SMTP_EMAIL:
        from_email = f"BridgePoint <{SMTP_EMAIL}>"

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

    payload = json.dumps({
        "from": from_email,
        "to": [to_email],
        "subject": "BridgePoint — Your Password Reset Code",
        "html": html_body,
    }).encode("utf-8")

    req = urllib.request.Request(
        RESEND_API_URL,
        data=payload,
        headers={
            "Authorization": f"Bearer {RESEND_API_KEY}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            result = json.loads(resp.read().decode())
            _logger.info("[EMAIL] ✅ OTP sent to %s — Resend ID: %s", to_email, result.get("id"))
            return True
    except urllib.error.HTTPError as e:
        body = e.read().decode() if e.fp else str(e)
        _logger.error("[EMAIL] ❌ Resend API error %d for %s: %s", e.code, to_email, body)
        return False
    except Exception as e:
        _logger.error("[EMAIL] ❌ Failed for %s: %s", to_email, str(e))
        return False
