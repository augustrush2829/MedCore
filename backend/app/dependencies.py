from typing import Annotated

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from app.core.rbac import has_permission
from app.core.security import decode_access_token
from app.db.models import PatientPortalAccount, User
from app.db.session import get_db
from app.services.token_revocation import is_token_revoked


DbSession = Annotated[Session, Depends(get_db)]


def get_bearer_token(authorization: Annotated[str | None, Header()] = None) -> str:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing bearer token")
    return authorization.removeprefix("Bearer ").strip()


BearerToken = Annotated[str, Depends(get_bearer_token)]


def get_current_user(db: DbSession, token: BearerToken) -> User:
    payload = decode_access_token(token)
    if not payload or not payload.get("sub"):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    if payload.get("jti") and is_token_revoked(db, payload["jti"]):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token revoked")
    user = db.get(User, payload["sub"])
    if not user or user.status != "active":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Inactive user")
    return user


def get_current_patient_account(db: DbSession, token: BearerToken) -> PatientPortalAccount:
    payload = decode_access_token(token)
    if not payload or not payload.get("sub") or payload.get("actor_type") != "patient":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid patient token")
    if payload.get("jti") and is_token_revoked(db, payload["jti"]):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token revoked")
    account = db.get(PatientPortalAccount, payload["sub"])
    if not account or account.status != "active":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Inactive patient account")
    return account


CurrentUser = Annotated[User, Depends(get_current_user)]
CurrentPatientAccount = Annotated[PatientPortalAccount, Depends(get_current_patient_account)]


def require_permission(permission: str):
    def dependency(user: CurrentUser) -> User:
        try:
            allowed = has_permission(user.role, permission)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Unknown role") from exc
        if not allowed:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permission")
        return user

    return dependency
