from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import select

from app.core.config import get_settings
from app.core.rate_limit import build_login_rate_limiter
from app.core.security import create_access_token, decode_access_token, verify_password
from app.db.models import User
from app.dependencies import BearerToken, CurrentUser, DbSession, require_permission
from app.schemas import LoginRequest, LoginResponse, UserRead
from app.services.audit import write_audit
from app.services.token_revocation import revoke_token

router = APIRouter(prefix="/auth", tags=["auth"])

_settings = get_settings()
login_rate_limiter = build_login_rate_limiter(_settings)


def _client_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"


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
def login(payload: LoginRequest, db: DbSession, request: Request) -> LoginResponse:
    email_key = f"email:{payload.email.lower()}"
    ip_key = f"ip:{_client_ip(request)}"

    for key in (email_key, ip_key):
        retry_after = login_rate_limiter.seconds_until_unlocked(key)
        if retry_after is not None:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many failed login attempts. Try again later.",
                headers={"Retry-After": str(int(retry_after) + 1)},
            )

    user = db.scalar(select(User).where(User.email == payload.email, User.status == "active"))
    if not user or not verify_password(payload.password, user.password_hash):
        login_rate_limiter.record_failure(email_key)
        login_rate_limiter.record_failure(ip_key)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")

    login_rate_limiter.record_success(email_key)
    login_rate_limiter.record_success(ip_key)
    user.last_login_at = datetime.now(timezone.utc)
    write_audit(db, user=user, action="auth.login", entity_type="user", entity_id=user.id)
    db.commit()
    token = create_access_token(user.id, {"organization_id": user.organization_id, "role": user.role})
    return LoginResponse(access_token=token, user=to_user_read(user))


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(user: CurrentUser, token: BearerToken, db: DbSession) -> Response:
    payload = decode_access_token(token)
    if payload and payload.get("jti") and payload.get("exp"):
        revoke_token(db, jti=payload["jti"], expires_at=datetime.fromtimestamp(payload["exp"], tz=timezone.utc))
        write_audit(db, user=user, action="auth.logout", entity_type="user", entity_id=user.id)
        db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/me", response_model=UserRead)
def me(user: User = Depends(require_permission("me:read"))) -> UserRead:
    return to_user_read(user)
