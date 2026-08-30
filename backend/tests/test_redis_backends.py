"""Unit tests for the Redis-backed login rate limiter.

Uses a minimal in-process fake instead of a real Redis server: these tests
check our key/TTL logic, not redis-py or Redis itself.
"""

import time

from app.core.rate_limit import RedisLoginRateLimiter


class FakeRedis:
    def __init__(self):
        self._values: dict[str, str] = {}
        self._expires_at: dict[str, float] = {}

    def _expired(self, key: str) -> bool:
        expires_at = self._expires_at.get(key)
        return expires_at is not None and expires_at <= time.monotonic()

    def _purge_if_expired(self, key: str) -> None:
        if key in self._values and self._expired(key):
            del self._values[key]
            self._expires_at.pop(key, None)

    def incr(self, key: str) -> int:
        self._purge_if_expired(key)
        value = int(self._values.get(key, "0")) + 1
        self._values[key] = str(value)
        return value

    def expire(self, key: str, seconds: int) -> None:
        self._expires_at[key] = time.monotonic() + seconds

    def set(self, key: str, value: str, ex: int | None = None) -> None:
        self._values[key] = value
        if ex is not None:
            self._expires_at[key] = time.monotonic() + ex
        else:
            self._expires_at.pop(key, None)

    def ttl(self, key: str) -> int:
        self._purge_if_expired(key)
        if key not in self._values:
            return -2
        expires_at = self._expires_at.get(key)
        if expires_at is None:
            return -1
        return max(int(expires_at - time.monotonic()), 0)

    def exists(self, key: str) -> int:
        self._purge_if_expired(key)
        return 1 if key in self._values else 0

    def delete(self, *keys: str) -> None:
        for key in keys:
            self._values.pop(key, None)
            self._expires_at.pop(key, None)

    def scan(self, cursor: int = 0, match: str = "*", count: int = 500):
        prefix = match.rstrip("*")
        matching = [key for key in self._values if key.startswith(prefix)]
        return 0, matching


def test_redis_rate_limiter_locks_out_after_max_attempts():
    limiter = RedisLoginRateLimiter(FakeRedis(), max_attempts=3, window_seconds=60, lockout_seconds=60)

    for _ in range(2):
        limiter.record_failure("email:a@test.mn")
    assert limiter.seconds_until_unlocked("email:a@test.mn") is None

    limiter.record_failure("email:a@test.mn")
    remaining = limiter.seconds_until_unlocked("email:a@test.mn")
    assert remaining is not None and remaining > 0


def test_redis_rate_limiter_lockout_is_scoped_per_key():
    limiter = RedisLoginRateLimiter(FakeRedis(), max_attempts=3, window_seconds=60, lockout_seconds=60)

    for _ in range(3):
        limiter.record_failure("email:a@test.mn")

    assert limiter.seconds_until_unlocked("email:a@test.mn") is not None
    assert limiter.seconds_until_unlocked("email:b@test.mn") is None


def test_redis_rate_limiter_success_clears_failures():
    limiter = RedisLoginRateLimiter(FakeRedis(), max_attempts=3, window_seconds=60, lockout_seconds=60)

    limiter.record_failure("email:a@test.mn")
    limiter.record_failure("email:a@test.mn")
    limiter.record_success("email:a@test.mn")

    for _ in range(2):
        limiter.record_failure("email:a@test.mn")
    assert limiter.seconds_until_unlocked("email:a@test.mn") is None


def test_redis_rate_limiter_reset_all_clears_every_key():
    limiter = RedisLoginRateLimiter(FakeRedis(), max_attempts=1, window_seconds=60, lockout_seconds=60)

    limiter.record_failure("email:a@test.mn")
    limiter.record_failure("ip:127.0.0.1")
    limiter.reset_all()

    assert limiter.seconds_until_unlocked("email:a@test.mn") is None
    assert limiter.seconds_until_unlocked("ip:127.0.0.1") is None
