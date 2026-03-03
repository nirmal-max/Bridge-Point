"""
Bridge Point — Auth Router
Registration and login endpoints.
"""

import json
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.utils.deps import get_current_user
from app.models.user import User, UserRole, LaborCategory
from app.schemas.user import UserRegister, UserLogin, TokenResponse, UserResponse
from app.utils.security import hash_password, verify_password, create_access_token

router = APIRouter(prefix="/api/auth", tags=["Authentication"])


@router.post("/register", response_model=TokenResponse, status_code=201)
def register(payload: UserRegister, db: Session = Depends(get_db)):
    """Register a new employer or labor user."""

    # Check for existing email
    if db.query(User).filter(User.email == payload.email).first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )

    # Check for existing phone
    if db.query(User).filter(User.phone == payload.phone).first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Phone number already registered",
        )

    # Unified user mode: all users get both roles
    roles = [UserRole.EMPLOYER.value, UserRole.LABOR.value]

    # Create user
    user = User(
        email=payload.email,
        phone=payload.phone,
        password_hash=hash_password(payload.password),
        full_name=payload.full_name,
        roles=json.dumps(roles),
        labor_category=LaborCategory(payload.labor_category) if payload.labor_category else None,
        skills=json.dumps(payload.skills) if payload.skills else None,
        city=payload.city,
        bio=payload.bio,
        email_verified=True,   # Auto-verified for MVP; enforce real OTP when provider is integrated
        phone_verified=True,   # Auto-verified for MVP; enforce real OTP when provider is integrated
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    # Generate token
    token = create_access_token(data={"sub": str(user.id), "roles": roles})

    return TokenResponse(
        access_token=token,
        user=_user_to_response(user),
    )


@router.post("/login", response_model=TokenResponse)
def login(payload: UserLogin, db: Session = Depends(get_db)):
    """Authenticate and return JWT token."""
    user = db.query(User).filter(User.email == payload.email).first()

    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    roles = json.loads(user.roles)
    token = create_access_token(data={"sub": str(user.id), "roles": roles})

    return TokenResponse(
        access_token=token,
        user=_user_to_response(user),
    )


@router.get("/me", response_model=UserResponse)
def get_me(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get current authenticated user's profile."""
    return _user_to_response(current_user)


@router.post("/activate-role", response_model=UserResponse)
def activate_role(
    role: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """DEPRECATED — unified mode means all users already have all roles."""
    return _user_to_response(current_user)


def _user_to_response(user: User) -> UserResponse:
    """Convert User ORM model to response schema."""
    skills = None
    if user.skills:
        try:
            skills = json.loads(user.skills)
        except (json.JSONDecodeError, TypeError):
            skills = []

    roles = []
    if user.roles:
        try:
            roles = json.loads(user.roles)
        except (json.JSONDecodeError, TypeError):
            roles = []

    return UserResponse(
        id=user.id,
        email=user.email,
        phone=user.phone,
        full_name=user.full_name,
        roles=roles,
        role=roles[0] if roles else "",
        is_admin=user.is_admin,
        labor_category=user.labor_category.value if user.labor_category else None,
        skills=skills,
        city=user.city,
        bio=user.bio,
        phone_verified=user.phone_verified,
        email_verified=user.email_verified,
        created_at=user.created_at,
    )
