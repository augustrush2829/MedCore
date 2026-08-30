from datetime import datetime, timezone

from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.models import RevokedToken

_REDIS_KEY_PREFIX = "medcore:revoked:"


def _redis_client():
    """None in dev/test (no REDIS_URL); a shared client once REDIS_URL is set,
    so revocation is visible to every instance instead of just the one that
    handled the logout request.
    """
    settings = get_settings()
    if not settings.redis_url:
        return None
    from app.core.redis_client import get_redis_client

    return get_redis_client(settings.redis_url)


def revoke_token(db: Session, *, jti: str, expires_at: datetime) -> None:
    client = _redis_client()
    if client is not None:
        ttl_seconds = max(int((expires_at - datetime.now(timezone.utc)).total_seconds()), 1)
        client.set(f"{_REDIS_KEY_PREFIX}{jti}", "1", ex=ttl_seconds)
        return
    db.merge(RevokedToken(jti=jti, expires_at=expires_at))
    db.execute(delete(RevokedToken).where(RevokedToken.expires_at < datetime.now(timezone.utc)))


def is_token_revoked(db: Session, jti: str) -> bool:
    client = _redis_client()
    if client is not None:
        return bool(client.exists(f"{_REDIS_KEY_PREFIX}{jti}"))
    return db.get(RevokedToken, jti) is not None
