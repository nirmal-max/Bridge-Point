"""
Bridge Point — Matching Service
Matches jobs to labors based on skill overlap.
"""

import json
from sqlalchemy.orm import Session

from app.models.user import User, UserRole
from app.models.job import Job


def find_matching_labors(job: Job, db: Session) -> list[User]:
    """
    Find labors whose skills match the job's work_description.
    Returns a list of matching labor users.
    """
    work_desc = str(job.work_description)

    labors = db.query(User).filter(User.role == UserRole.LABOR).all()

    matching = []
    for labor in labors:
        if not labor.skills:
            continue
        try:
            skills = json.loads(labor.skills)
        except (json.JSONDecodeError, TypeError):
            continue

        # Normalize for comparison
        normalized_skills = [s.lower().strip().replace(" ", "_") for s in skills]

        if work_desc.lower() in normalized_skills:
            matching.append(labor)

    return matching


def find_matching_jobs(labor: User, db: Session) -> list[Job]:
    """
    Find jobs that match a labor's skills.
    Only returns jobs in 'posted' or 'waiting' status.
    """
    if not labor.skills:
        return []

    try:
        skills = json.loads(labor.skills)
    except (json.JSONDecodeError, TypeError):
        return []

    normalized_skills = [s.lower().strip().replace(" ", "_") for s in skills]

    # Get open jobs
    jobs = (
        db.query(Job)
        .filter(Job.status.in_(["posted", "waiting"]))
        .all()
    )

    matching = []
    for job in jobs:
        work_desc = str(job.work_description)
        if work_desc.lower() in normalized_skills:
            matching.append(job)

    return matching
