import json
from functools import wraps
from typing import Callable

import structlog
from redis.exceptions import RedisError

logger = structlog.get_logger(__name__)

_NAMESPACE = "ai-world-cup-agent"


def cache(ttl: int, key_builder: Callable):
    def decorator(func):
        @wraps(func)
        async def wrapper(self, *args, **kwargs):
            redis = getattr(self, "redis", None)

            # No Redis configured → run uncached, silently (expected path).
            if redis is None:
                return await func(self, *args, **kwargs)

            key = f"{_NAMESPACE}:{key_builder(func, self, *args, **kwargs)}"

            try:
                cached = await redis.get(key)
                if cached is not None:
                    return json.loads(cached)
            except RedisError as exc:
                # ConnectionError/TimeoutError are RedisError subclasses.
                logger.warning("cache.read_failed", key=key, error=str(exc))
                return await func(self, *args, **kwargs)

            result = await func(self, *args, **kwargs)

            try:
                await redis.set(key, json.dumps(result), ex=ttl)
            except RedisError as exc:
                logger.warning("cache.write_failed", key=key, error=str(exc))

            return result

        return wrapper

    return decorator
