from __future__ import annotations

import threading
import time
from dataclasses import dataclass


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
