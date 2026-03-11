"""
Bridge Point — Main Application
FastAPI application entry point.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import logging
from app.config import APP_NAME, APP_VERSION, APP_DESCRIPTION, CORS_ORIGINS, JWT_SECRET_KEY
from app.database import engine, Base

_logger = logging.getLogger(__name__)

# ─── Security check: warn if using default JWT secret ───
_DEFAULT_SECRET = "bridgepoint-dev-secret-key-change-in-production-2026"
if JWT_SECRET_KEY == _DEFAULT_SECRET:
    _logger.warning(
        "⚠️  JWT_SECRET_KEY is set to the default dev value! "
        "Set the JWT_SECRET_KEY environment variable to a secure random string for production."
    )

# Import all models so they register with Base.metadata
from app.models.user import User
from app.models.job import Job
from app.models.application import Application
from app.models.review import Review
from app.models.favorite import Favorite
from app.models.commission import CommissionLedger
from app.models.status_transition import StatusTransition
from app.models.call import CallLog
from app.models.message import Message
from app.models.private_request import PrivateRequest
from app.models.password_reset import PasswordReset
from app.models.payment import Payment

# Import routers
from app.routers import auth, jobs, applications, reviews, favorites, payments, websocket, calls, messages, private_requests, password_reset, cashfree_webhook

# ─── Create tables ──────────────────────────────────────
try:
    Base.metadata.create_all(bind=engine)
except Exception as _db_err:
    _logger.error(f"⚠️  Could not connect to database at startup: {_db_err}")
    _logger.error("Tables will be created on first successful connection.")

# ─── Application ────────────────────────────────────────
app = FastAPI(
    title=APP_NAME,
    version=APP_VERSION,
    description=APP_DESCRIPTION,
    docs_url="/docs",
    redoc_url="/redoc",
)

# ─── CORS Middleware ────────────────────────────────────
# In a real production app, you'd want to restrict origins,
# but for testing and Vercel preview URLs, we allow all for now.
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Register Routers ──────────────────────────────────
app.include_router(auth.router)
app.include_router(password_reset.router)
app.include_router(jobs.router)
app.include_router(applications.router)
app.include_router(reviews.router)
app.include_router(favorites.router)
app.include_router(payments.router)
app.include_router(cashfree_webhook.router)
app.include_router(websocket.router)
app.include_router(calls.router)
app.include_router(messages.router)
app.include_router(private_requests.router)


# ─── Health Check ───────────────────────────────────────
@app.get("/")
def root():
    return {
        "name": APP_NAME,
        "version": APP_VERSION,
        "status": "running",
        "docs": "/docs",
    }


@app.get("/health")
def health():
    return {"status": "healthy"}
