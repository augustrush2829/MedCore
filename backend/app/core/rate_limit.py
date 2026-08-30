from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol


if TYPE_CHECKING:
    from app.core.config import Settings


class RateLimiterBackend(Protocol):
    def seconds_until_unlocked(self, key: str) -> float | None: ...
    def record_failure(self, key: str) -> None: ...
    def record_success(self, key: str) -> None: ...
    def reset_all(self) -> None: ...


@dataclass
class _State:
    failures: int = 0
    window_start: float = 0.0
    locked_until: float = 0.0


class LoginRateLimiter:
    """In-memory failed-attempt counter with lockout, keyed by caller-supplied string.

    Not shared across processes/instances; for multi-instance deployments back
    this with Redis instead. Sufficient for the current single-process MVP.
    """

    def __init__(self, max_attempts: int, window_seconds: float, lockout_seconds: float) -> None:
        self.max_attempts = max_attempts
        self.window_seconds = window_seconds
        self.lockout_seconds = lockout_seconds
        self._states: dict[str, _State] = {}
        self._lock = threading.Lock()

    def _active_state(self, key: str, now: float) -> _State | None:
        state = self._states.get(key)
        if state is None:
            return None
        if state.locked_until and state.locked_until <= now:
            del self._states[key]
            return None
        if not state.locked_until and now - state.window_start > self.window_seconds:
            del self._states[key]
            return None
        return state

    def seconds_until_unlocked(self, key: str) -> float | None:
        now = time.monotonic()
        with self._lock:
            state = self._active_state(key, now)
            if state and state.locked_until:
                return state.locked_until - now
        return None

    def record_failure(self, key: str) -> None:
        now = time.monotonic()
        with self._lock:
            state = self._active_state(key, now)
            if state is None:
                state = _State(window_start=now)
                self._states[key] = state
            state.failures += 1
            if state.failures >= self.max_attempts:
                state.locked_until = now + self.lockout_seconds

    def record_success(self, key: str) -> None:
        with self._lock:
            self._states.pop(key, None)

    def reset_all(self) -> None:
        with self._lock:
            self._states.clear()


class RedisLoginRateLimiter:
    """Same failed-attempt/lockout semantics as LoginRateLimiter, but state
    lives in Redis so the counter and lockout are shared across processes
    and instances instead of being local to one worker.
    """

    def __init__(
        self,
        redis_client,
        max_attempts: int,
        window_seconds: float,
        lockout_seconds: float,
        prefix: str = "medcore:ratelimit",
    ) -> None:
        self._redis = redis_client
        self.max_attempts = max_attempts
        self.window_seconds = window_seconds
        self.lockout_seconds = lockout_seconds
        self._prefix = prefix

    def _count_key(self, key: str) -> str:
        return f"{self._prefix}:count:{key}"

    def _lock_key(self, key: str) -> str:
        return f"{self._prefix}:lock:{key}"

    def seconds_until_unlocked(self, key: str) -> float | None:
        ttl = self._redis.ttl(self._lock_key(key))
        return float(ttl) if ttl and ttl > 0 else None

    def record_failure(self, key: str) -> None:
        count_key = self._count_key(key)
        count = self._redis.incr(count_key)
        if count == 1:
            self._redis.expire(count_key, int(self.window_seconds))
        if count >= self.max_attempts:
            self._redis.set(self._lock_key(key), "1", ex=int(self.lockout_seconds))

    def record_success(self, key: str) -> None:
        self._redis.delete(self._count_key(key), self._lock_key(key))

    def reset_all(self) -> None:
        cursor = 0
        while True:
            cursor, keys = self._redis.scan(cursor=cursor, match=f"{self._prefix}:*", count=500)
            if keys:
                self._redis.delete(*keys)
            if cursor == 0:
                break


def build_login_rate_limiter(settings: "Settings") -> RateLimiterBackend:
    if settings.redis_url:
        from app.core.redis_client import get_redis_client

        return RedisLoginRateLimiter(
            get_redis_client(settings.redis_url),
            max_attempts=settings.login_rate_limit_max_attempts,
            window_seconds=settings.login_rate_limit_window_seconds,
            lockout_seconds=settings.login_rate_limit_lockout_seconds,
        )
    return LoginRateLimiter(
        max_attempts=settings.login_rate_limit_max_attempts,
        window_seconds=settings.login_rate_limit_window_seconds,
        lockout_seconds=settings.login_rate_limit_lockout_seconds,
    )
