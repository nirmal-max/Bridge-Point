"""
Bridge Point — Application Configuration
Centralized settings with environment variable support.
"""

import os
from pathlib import Path


# ─── Paths ──────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent
DATABASE_DIR = BASE_DIR / "data"
DATABASE_DIR.mkdir(parents=True, exist_ok=True)

# ─── Database ───────────────────────────────────────────
# SQLite for local dev; set DATABASE_URL env var for Supabase PostgreSQL
_db_url = os.getenv("DATABASE_URL", f"sqlite:///{DATABASE_DIR / 'bridgepoint.db'}")

# Supabase/Heroku use 'postgres://' but SQLAlchemy requires 'postgresql://'
if _db_url.startswith("postgres://"):
    _db_url = _db_url.replace("postgres://", "postgresql://", 1)

DATABASE_URL: str = _db_url

# ─── JWT ────────────────────────────────────────────────
JWT_SECRET_KEY: str = os.getenv(
    "JWT_SECRET_KEY",
    "bridgepoint-dev-secret-key-change-in-production-2026"
)
JWT_ALGORITHM: str = "HS256"
JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv(
    "JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "1440"  # 24 hours
))

# ─── SMTP (Gmail) ──────────────────────────────────────
SMTP_EMAIL: str = os.getenv("SMTP_EMAIL", "")       # Gmail address
SMTP_PASSWORD: str = os.getenv("SMTP_PASSWORD", "")  # Gmail App Password

# ─── Resend (HTTP email API) ───────────────────────────
RESEND_API_KEY: str = os.getenv("RESEND_API_KEY", "")  # Get from https://resend.com/api-keys

# ─── Commission ────────────────────────────────────────
# Dual-sided model: 4% from employer + 4% from worker = 8% platform revenue
# Employer pays: budget × 1.04
# Worker receives: budget × 0.96
# Platform earns: budget × 0.08
COMMISSION_RATE_EMPLOYER: float = float(os.getenv("COMMISSION_RATE_EMPLOYER", "0.04"))  # 4% employer surcharge
COMMISSION_RATE_LABOR: float = float(os.getenv("COMMISSION_RATE_LABOR", "0.04"))        # 4% worker deduction
COMMISSION_RATE_PLATFORM: float = 0.04   # Each side contributes 4%

# ─── CORS ───────────────────────────────────────────────
_cors_env = os.getenv("CORS_ORIGINS", "")
CORS_ORIGINS: list[str] = [
    o.strip() for o in _cors_env.split(",") if o.strip()
] if _cors_env else [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:3001",
    "http://127.0.0.1:3001",
]

# ─── Application ────────────────────────────────────────
APP_NAME: str = "Bridge Point"
APP_VERSION: str = "1.0.0"
APP_DESCRIPTION: str = "Micro-Employment Platform for India"
DEBUG: bool = os.getenv("DEBUG", "true").lower() == "true"

# ─── WebRTC ICE Servers ────────────────────────────────
# Free STUN servers for NAT traversal.
# Set TURN_URL, TURN_USERNAME, TURN_CREDENTIAL env vars for production
# (e.g., Twilio, Metered) to support calls behind symmetric NATs.
ICE_SERVERS: list[dict] = [
    {"urls": "stun:stun.l.google.com:19302"},
    {"urls": "stun:stun1.l.google.com:19302"},
    {"urls": "stun:stun2.l.google.com:19302"},
]

# Append TURN server if env vars are configured
_turn_url = os.getenv("TURN_URL", "")
_turn_user = os.getenv("TURN_USERNAME", "")
_turn_cred = os.getenv("TURN_CREDENTIAL", "")
if _turn_url and _turn_user and _turn_cred:
    ICE_SERVERS.append({
        "urls": _turn_url,
        "username": _turn_user,
        "credential": _turn_cred,
    })

# ─── Platform Payment (UPI Custody) ────────────────────
PLATFORM_UPI_ID: str = os.getenv("PLATFORM_UPI_ID", "nirmal.2007000-2@okhdfcbank")
PLATFORM_UPI_NAME: str = os.getenv("PLATFORM_UPI_NAME", "Nirmal")

# ─── Admin Emails (auto-granted admin on register) ────
_admin_env = os.getenv("ADMIN_EMAILS", "bridgepoint.team@gmail.com")
ADMIN_EMAILS: set[str] = {e.strip().lower() for e in _admin_env.split(",") if e.strip()}
