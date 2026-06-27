"""
Unit tests for the @cache decorator's Redis-optional behavior.
Covers: no Redis (None), Redis present (hit/miss), and Redis failure (RedisError).
"""
from unittest.mock import AsyncMock

import pytest
from redis.exceptions import ConnectionError as RedisConnectionError

from app.utils.cache import cache


def _key_builder(func, self, *args, **kwargs):
    return f"test:{args[0]}"


class Service:
    def __init__(self, redis=None):
        self.redis = redis
        self.calls = 0

    @cache(ttl=60, key_builder=_key_builder)
    async def fetch(self, arg):
        self.calls += 1
        return {"arg": arg}


@pytest.mark.asyncio
async def test_cache_none_runs_uncached():
    """redis is None → function runs every call, nothing cached, no error."""
    svc = Service(redis=None)
    assert await svc.fetch("x") == {"arg": "x"}
    assert await svc.fetch("x") == {"arg": "x"}
    assert svc.calls == 2


@pytest.mark.asyncio
async def test_cache_present_hit_and_miss():
    """redis present → miss populates, hit short-circuits the function."""
    store = {}
    redis = AsyncMock()

    async def get(key):
        return store.get(key)

    async def set(key, value, ex=None):
        store[key] = value

    redis.get = get
    redis.set = set

    svc = Service(redis=redis)
    assert await svc.fetch("y") == {"arg": "y"}  # miss
    assert await svc.fetch("y") == {"arg": "y"}  # hit
    assert svc.calls == 1


@pytest.mark.asyncio
async def test_cache_redis_failure_falls_back():
    """redis present but raising → warning path, function still returns."""
    redis = AsyncMock()

    async def boom(*args, **kwargs):
        raise RedisConnectionError("redis down")

    redis.get = boom
    redis.set = boom

    svc = Service(redis=redis)
    assert await svc.fetch("z") == {"arg": "z"}
    assert svc.calls == 1
