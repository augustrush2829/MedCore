from datetime import datetime, timezone

from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.db.models import RevokedToken


def revoke_token(db: Session, *, jti: str, expires_at: datetime) -> None:
    db.merge(RevokedToken(jti=jti, expires_at=expires_at))
    db.execute(delete(RevokedToken).where(RevokedToken.expires_at < datetime.now(timezone.utc)))


def is_token_revoked(db: Session, jti: str) -> bool:
    return db.get(RevokedToken, jti) is not None
