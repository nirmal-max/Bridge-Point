"""
Bridge Point — State Machine Service
IMMUTABLE LIFECYCLE CONTRACT — 9 stages.
No skipping. No manual overrides. All transitions timestamped.

LIFECYCLE:
  posted → labour_allotted → work_started → work_in_progress → work_completed
  → payment_in_process → verification_pending → payout_released → payment_completed

PAYMENT FLOW (Platform Custody Model):
  Employer pays Platform → Admin verifies → Admin releases 97% to worker.
"""

from enum import Enum


class JobStatus(str, Enum):
    """Immutable 10-stage lifecycle. DO NOT ADD or REMOVE states."""
    POSTED = "posted"
    LABOUR_ALLOTTED = "labour_allotted"
    WORK_STARTED = "work_started"
    WORK_IN_PROGRESS = "work_in_progress"
    WORK_COMPLETED = "work_completed"
    # ─── Platform Custody Payment States ─────────────────
    PAYMENT_IN_PROCESS = "payment_in_process"
    VERIFICATION_PENDING = "verification_pending"
    VERIFIED = "verified"
    PAYOUT_RELEASED = "payout_released"
    PAYMENT_COMPLETED = "payment_completed"


# ─── Allowed Transitions (strict forward-only, NO skipping) ─────
ALLOWED_TRANSITIONS: dict[JobStatus, list[JobStatus]] = {
    JobStatus.POSTED:                [JobStatus.LABOUR_ALLOTTED],
    JobStatus.LABOUR_ALLOTTED:       [JobStatus.WORK_STARTED],
    JobStatus.WORK_STARTED:          [JobStatus.WORK_IN_PROGRESS],
    JobStatus.WORK_IN_PROGRESS:      [JobStatus.WORK_COMPLETED],
    JobStatus.WORK_COMPLETED:        [JobStatus.PAYMENT_IN_PROCESS],
    JobStatus.PAYMENT_IN_PROCESS:    [JobStatus.VERIFICATION_PENDING],
    JobStatus.VERIFICATION_PENDING:  [JobStatus.VERIFIED],
    JobStatus.VERIFIED:              [JobStatus.PAYOUT_RELEASED],
    JobStatus.PAYOUT_RELEASED:       [JobStatus.PAYMENT_COMPLETED],
    JobStatus.PAYMENT_COMPLETED:     [],  # Terminal state
}


# ─── Progress bar percentages ──────────────────────────
STATUS_PROGRESS: dict[JobStatus, int] = {
    JobStatus.POSTED: 0,
    JobStatus.LABOUR_ALLOTTED: 15,
    JobStatus.WORK_STARTED: 30,
    JobStatus.WORK_IN_PROGRESS: 55,
    JobStatus.WORK_COMPLETED: 70,
    JobStatus.PAYMENT_IN_PROCESS: 78,
    JobStatus.VERIFICATION_PENDING: 85,
    JobStatus.VERIFIED: 90,
    JobStatus.PAYOUT_RELEASED: 95,
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
    JobStatus.PAYMENT_IN_PROCESS,
    JobStatus.VERIFICATION_PENDING,
    JobStatus.VERIFIED,
}
HISTORY_STATUSES = {JobStatus.PAYOUT_RELEASED, JobStatus.PAYMENT_COMPLETED}


def validate_transition(current: JobStatus, target: JobStatus) -> bool:
    """Returns True only if the transition from current → target is allowed."""
    allowed = ALLOWED_TRANSITIONS.get(current, [])
    return target in allowed


def get_next_status(current: JobStatus) -> JobStatus | None:
    """Returns the single valid next status, or None if at terminal state."""
    allowed = ALLOWED_TRANSITIONS.get(current, [])
    return allowed[0] if allowed else None


def get_status_display(status: JobStatus) -> str:
    """Human-readable label for a status."""
    labels = {
        JobStatus.POSTED: "Posted",
        JobStatus.LABOUR_ALLOTTED: "Worker Assigned",
        JobStatus.WORK_STARTED: "Work Started",
        JobStatus.WORK_IN_PROGRESS: "Work in Progress",
        JobStatus.WORK_COMPLETED: "Work Completed",
        JobStatus.PAYMENT_IN_PROCESS: "Payment in Process",
        JobStatus.VERIFICATION_PENDING: "Verification Pending",
        JobStatus.VERIFIED: "Payment Verified",
        JobStatus.PAYOUT_RELEASED: "Payout Released",
        JobStatus.PAYMENT_COMPLETED: "Payment Completed",
    }
    return labels.get(status, status.value)
