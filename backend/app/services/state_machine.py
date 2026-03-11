"""
Bridge Point — State Machine Service
IMMUTABLE LIFECYCLE CONTRACT — 9 stages.
No skipping. No manual overrides. All transitions timestamped.

LIFECYCLE:
  posted → labour_allotted → work_started → work_in_progress → work_completed
  → payment_pending → payment_paid → payout_transferred → payment_completed

PAYMENT FLOW (Razorpay):
  Employer pays via Razorpay Checkout → Server verifies signature
  → Admin initiates transfer → Worker receives payout via Route.
"""

from enum import Enum


class JobStatus(str, Enum):
    """Immutable 9-stage lifecycle. DO NOT ADD or REMOVE states."""
    POSTED = "posted"
    LABOUR_ALLOTTED = "labour_allotted"
    WORK_STARTED = "work_started"
    WORK_IN_PROGRESS = "work_in_progress"
    WORK_COMPLETED = "work_completed"
    # ─── Razorpay Payment States ─────────────────────────
    PAYMENT_PENDING = "payment_pending"
    PAYMENT_PAID = "payment_paid"
    PAYOUT_TRANSFERRED = "payout_transferred"
    PAYMENT_COMPLETED = "payment_completed"


# ─── Legacy status aliases (for backward compat with existing DB rows) ───
LEGACY_STATUS_MAP: dict[str, str] = {
    "payment_in_process": "payment_pending",
    "verification_pending": "payment_pending",
    "verified": "payment_paid",
    "payout_released": "payout_transferred",
}


# ─── Allowed Transitions (strict forward-only, NO skipping) ─────
ALLOWED_TRANSITIONS: dict[JobStatus, list[JobStatus]] = {
    JobStatus.POSTED:                [JobStatus.LABOUR_ALLOTTED],
    JobStatus.LABOUR_ALLOTTED:       [JobStatus.WORK_STARTED],
    JobStatus.WORK_STARTED:          [JobStatus.WORK_IN_PROGRESS],
    JobStatus.WORK_IN_PROGRESS:      [JobStatus.WORK_COMPLETED],
    JobStatus.WORK_COMPLETED:        [JobStatus.PAYMENT_PENDING],
    JobStatus.PAYMENT_PENDING:       [JobStatus.PAYMENT_PAID],
    JobStatus.PAYMENT_PAID:          [JobStatus.PAYOUT_TRANSFERRED],
    JobStatus.PAYOUT_TRANSFERRED:    [JobStatus.PAYMENT_COMPLETED],
    JobStatus.PAYMENT_COMPLETED:     [],  # Terminal state
}


# ─── Progress bar percentages ──────────────────────────
STATUS_PROGRESS: dict[JobStatus, int] = {
    JobStatus.POSTED: 0,
    JobStatus.LABOUR_ALLOTTED: 15,
    JobStatus.WORK_STARTED: 30,
    JobStatus.WORK_IN_PROGRESS: 55,
    JobStatus.WORK_COMPLETED: 70,
    JobStatus.PAYMENT_PENDING: 80,
    JobStatus.PAYMENT_PAID: 90,
    JobStatus.PAYOUT_TRANSFERRED: 95,
    JobStatus.PAYMENT_COMPLETED: 100,
}

# ─── Feed visibility ───────────────────────────────────
FEED_VISIBLE_STATUSES = {JobStatus.POSTED, JobStatus.LABOUR_ALLOTTED}

# ─── Dashboard visibility ──────────────────────────────
ACTIVE_WORK_STATUSES = {
    JobStatus.LABOUR_ALLOTTED,
    JobStatus.WORK_STARTED,
    JobStatus.WORK_IN_PROGRESS,
    JobStatus.WORK_COMPLETED,
    JobStatus.PAYMENT_PENDING,
    JobStatus.PAYMENT_PAID,
}
HISTORY_STATUSES = {JobStatus.PAYOUT_TRANSFERRED, JobStatus.PAYMENT_COMPLETED}


def validate_transition(current: JobStatus, target: JobStatus) -> bool:
    """Returns True only if the transition from current → target is allowed."""
    allowed = ALLOWED_TRANSITIONS.get(current, [])
    return target in allowed


def get_next_status(current: JobStatus) -> JobStatus | None:
    """Returns the single valid next status, or None if at terminal state."""
    allowed = ALLOWED_TRANSITIONS.get(current, [])
    return allowed[0] if allowed else None


def normalize_status(raw: str) -> str:
    """Map legacy status values to current status values."""
    return LEGACY_STATUS_MAP.get(raw, raw)


def get_status_display(status: JobStatus) -> str:
    """Human-readable label for a status."""
    labels = {
        JobStatus.POSTED: "Posted",
        JobStatus.LABOUR_ALLOTTED: "Worker Assigned",
        JobStatus.WORK_STARTED: "Work Started",
        JobStatus.WORK_IN_PROGRESS: "Work in Progress",
        JobStatus.WORK_COMPLETED: "Work Completed",
        JobStatus.PAYMENT_PENDING: "Payment Pending",
        JobStatus.PAYMENT_PAID: "Payment Received",
        JobStatus.PAYOUT_TRANSFERRED: "Payout Transferred",
        JobStatus.PAYMENT_COMPLETED: "Payment Completed",
    }
    return labels.get(status, status.value)
