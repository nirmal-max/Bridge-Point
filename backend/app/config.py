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
# SQLite for local dev; swap to PostgreSQL URI for production
DATABASE_URL: str = os.getenv(
    "DATABASE_URL",
    f"sqlite:///{DATABASE_DIR / 'bridgepoint.db'}"
)

# ─── JWT ────────────────────────────────────────────────
JWT_SECRET_KEY: str = os.getenv(
    "JWT_SECRET_KEY",
    "bridgepoint-dev-secret-key-change-in-production-2026"
)
JWT_ALGORITHM: str = "HS256"
JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv(
    "JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "1440"  # 24 hours
))

# ─── Commission ────────────────────────────────────────
# Locked: 3% employer side, 3% labor side, 6% platform total
COMMISSION_RATE_EMPLOYER: float = 0.03
COMMISSION_RATE_LABOR: float = 0.03
COMMISSION_RATE_PLATFORM: float = 0.06

# ─── CORS ───────────────────────────────────────────────
_cors_env = os.getenv("CORS_ORIGINS", "")
CORS_ORIGINS: list[str] = [
    o.strip() for o in _cors_env.split(",") if o.strip()
] if _cors_env else [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

# ─── Application ────────────────────────────────────────
APP_NAME: str = "Bridge Point"
APP_VERSION: str = "1.0.0"
APP_DESCRIPTION: str = "Micro-Employment Platform for India"
DEBUG: bool = os.getenv("DEBUG", "true").lower() == "true"

# ─── WebRTC ICE Servers ────────────────────────────────
# Free STUN servers for NAT traversal.
# Add TURN server credentials for production (e.g., Twilio, Metered).
ICE_SERVERS: list[dict] = [
    {"urls": "stun:stun.l.google.com:19302"},
    {"urls": "stun:stun1.l.google.com:19302"},
    {"urls": "stun:stun2.l.google.com:19302"},
]

# ─── Platform Payment (UPI Custody) ───────────────────
PLATFORM_UPI_ID: str = os.getenv("PLATFORM_UPI_ID", "bridgepoint@upi")
PLATFORM_UPI_NAME: str = os.getenv("PLATFORM_UPI_NAME", "BridgePoint Platform")
