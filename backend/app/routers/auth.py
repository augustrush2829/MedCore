from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select

from app.core.security import create_access_token, verify_password
from app.db.models import User
from app.dependencies import DbSession, require_permission
from app.schemas import LoginRequest, LoginResponse, UserRead
from app.services.audit import write_audit

router = APIRouter(prefix="/auth", tags=["auth"])


def to_user_read(user: User) -> UserRead:
    return UserRead(
        id=user.id,
        name=user.name,
        email=user.email,
        role=user.role,
        organization_id=user.organization_id,
        organization_name=user.organization.name if user.organization else None,
    )


@router.post("/login", response_model=LoginResponse)
def login(payload: LoginRequest, db: DbSession) -> LoginResponse:
    user = db.scalar(select(User).where(User.email == payload.email, User.status == "active"))
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")
    user.last_login_at = datetime.now(timezone.utc)
    write_audit(db, user=user, action="auth.login", entity_type="user", entity_id=user.id)
    db.commit()
    token = create_access_token(user.id, {"organization_id": user.organization_id, "role": user.role})
    return LoginResponse(access_token=token, user=to_user_read(user))


@router.get("/me", response_model=UserRead)
def me(user: User = Depends(require_permission("me:read"))) -> UserRead:
    return to_user_read(user)
