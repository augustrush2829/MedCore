from app.core.config import get_settings
from app.core.rate_limit import LoginRateLimiter


def test_login_locks_out_after_repeated_failures(client):
    max_attempts = get_settings().login_rate_limit_max_attempts

    for _ in range(max_attempts):
        response = client.post("/auth/login", json={"email": "doctor@test.mn", "password": "wrong-password"})
        assert response.status_code == 401

    locked_response = client.post("/auth/login", json={"email": "doctor@test.mn", "password": "wrong-password"})
    assert locked_response.status_code == 429
    assert "Retry-After" in locked_response.headers

    locked_with_correct_password = client.post("/auth/login", json={"email": "doctor@test.mn", "password": "password"})
    assert locked_with_correct_password.status_code == 429


def test_rate_limiter_lockout_is_scoped_per_key():
    limiter = LoginRateLimiter(max_attempts=3, window_seconds=60, lockout_seconds=60)

    for _ in range(3):
        limiter.record_failure("email:a@test.mn")

    assert limiter.seconds_until_unlocked("email:a@test.mn") is not None
    assert limiter.seconds_until_unlocked("email:b@test.mn") is None
    assert limiter.seconds_until_unlocked("ip:127.0.0.1") is None


def test_successful_login_resets_failure_count(client):
    max_attempts = get_settings().login_rate_limit_max_attempts

    for _ in range(max_attempts - 1):
        response = client.post("/auth/login", json={"email": "doctor@test.mn", "password": "wrong-password"})
        assert response.status_code == 401

    success_response = client.post("/auth/login", json={"email": "doctor@test.mn", "password": "password"})
    assert success_response.status_code == 200

    retry_response = client.post("/auth/login", json={"email": "doctor@test.mn", "password": "wrong-password"})
    assert retry_response.status_code == 401
