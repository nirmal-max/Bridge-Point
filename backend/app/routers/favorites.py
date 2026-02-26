"""
Bridge Point — Favorites Router
Employer saves labor for rebooking later.
"""

import json
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.models.favorite import Favorite
from app.schemas.common import FavoriteCreate, FavoriteResponse
from app.utils.deps import require_employer

router = APIRouter(prefix="/api/favorites", tags=["Favorites"])


@router.post("", response_model=FavoriteResponse, status_code=201)
def add_favorite(
    payload: FavoriteCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_employer),
):
    # Verify target user exists
    labor = db.query(User).filter(User.id == payload.labor_id).first()
    if not labor:
        raise HTTPException(status_code=404, detail="User not found")

    # Check duplicate
    existing = (
        db.query(Favorite)
        .filter(Favorite.employer_id == current_user.id, Favorite.labor_id == payload.labor_id)
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Already in favorites",
        )

    fav = Favorite(
        employer_id=current_user.id,
        labor_id=payload.labor_id,
    )
    db.add(fav)
    db.commit()
    db.refresh(fav)

    return _favorite_to_response(fav)


@router.get("", response_model=list[FavoriteResponse])
def get_favorites(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_employer),
):
    """Employer: list saved favorites."""
    favs = (
        db.query(Favorite)
        .filter(Favorite.employer_id == current_user.id)
        .order_by(Favorite.created_at.desc())
        .all()
    )
    return [_favorite_to_response(f) for f in favs]


@router.delete("/{favorite_id}", status_code=204)
def remove_favorite(
    favorite_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_employer),
):
    """Employer: remove a favorite."""
    fav = (
        db.query(Favorite)
        .filter(Favorite.id == favorite_id, Favorite.employer_id == current_user.id)
        .first()
    )
    if not fav:
        raise HTTPException(status_code=404, detail="Favorite not found")

    db.delete(fav)
    db.commit()


def _favorite_to_response(fav: Favorite) -> FavoriteResponse:
    """Convert Favorite ORM to response."""
    labor = fav.labor
    skills = None
    if labor and labor.skills:
        try:
            skills = json.loads(labor.skills)
        except (json.JSONDecodeError, TypeError):
            skills = []

    return FavoriteResponse(
        id=fav.id,
        employer_id=fav.employer_id,
        labor_id=fav.labor_id,
        labor_name=labor.full_name if labor else None,
        labor_skills=skills,
        labor_phone=labor.phone if labor else None,
        created_at=fav.created_at,
    )
