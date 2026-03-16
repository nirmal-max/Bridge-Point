"""
Bridge Point — Database Engine & Session Management
Uses SQLAlchemy with SQLite for local development.
Swap DATABASE_URL to PostgreSQL for production.
"""

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, DeclarativeBase

from app.config import DATABASE_URL


# ─── Engine Setup ───────────────────────────────────────
connect_args = {}
engine_kwargs = {"echo": False}

if DATABASE_URL.startswith("sqlite"):
    connect_args["check_same_thread"] = False
else:
    # PostgreSQL connection pool settings
    engine_kwargs.update({
        "pool_size": 5,
        "max_overflow": 10,
        "pool_pre_ping": True,      # Auto-reconnect stale connections
        "pool_recycle": 300,         # Recycle connections every 5 minutes
    })

engine = create_engine(
    DATABASE_URL,
    connect_args=connect_args,
    **engine_kwargs,
)

# Enable WAL mode and foreign keys for SQLite
if DATABASE_URL.startswith("sqlite"):
    @event.listens_for(engine, "connect")
    def _set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL;")
        cursor.execute("PRAGMA foreign_keys=ON;")
        cursor.close()


# ─── Session Factory ───────────────────────────────────
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)


# ─── Base Model ────────────────────────────────────────
class Base(DeclarativeBase):
    pass


# ─── Dependency ────────────────────────────────────────
def get_db():
    """FastAPI dependency that yields a DB session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
