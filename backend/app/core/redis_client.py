from __future__ import annotations

from functools import lru_cache

import redis


@lru_cache
def get_redis_client(redis_url: str) -> redis.Redis:
    """Cached per-URL client. redis-py pools connections internally, so one
    client instance is safe to share across requests/threads."""
    return redis.Redis.from_url(redis_url, decode_responses=True)
