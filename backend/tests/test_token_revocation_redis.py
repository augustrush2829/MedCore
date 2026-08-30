"""Unit tests for the Redis-backed token revocation store.

Uses the same minimal in-process fake as the rate-limiter tests instead of
a real Redis server: these tests check our key/TTL logic, not redis-py or
Redis itself.
"""

from datetime import datetime, timedelta, timezone

from app.services import token_revocation
from test_redis_backends import FakeRedis


def test_token_revocation_uses_redis_when_configured(monkeypatch):
    fake = FakeRedis()
    monkeypatch.setattr(token_revocation, "_redis_client", lambda: fake)

    jti = "some-jti"
    assert token_revocation.is_token_revoked(None, jti) is False

    token_revocation.revoke_token(None, jti=jti, expires_at=datetime.now(timezone.utc) + timedelta(minutes=5))
    assert token_revocation.is_token_revoked(None, jti) is True


def test_token_revocation_falls_back_to_db_when_redis_not_configured(monkeypatch):
    monkeypatch.setattr(token_revocation, "_redis_client", lambda: None)
    calls = {"db_used": False}

    class _FakeDb:
        def merge(self, obj):
            calls["db_used"] = True

        def execute(self, stmt):
            calls["db_used"] = True

        def get(self, model, jti):
            calls["db_used"] = True
            return None

    db = _FakeDb()
    token_revocation.revoke_token(db, jti="x", expires_at=datetime.now(timezone.utc) + timedelta(minutes=5))
    assert calls["db_used"] is True

    calls["db_used"] = False
    assert token_revocation.is_token_revoked(db, "x") is False
    assert calls["db_used"] is True
