import json
from functools import wraps
from typing import Callable

_NAMESPACE = "ai-world-cup-agent"


def cache(ttl: int, key_builder: Callable):
    def decorator(func):
        @wraps(func)
        async def wrapper(self, *args, **kwargs):
            redis = getattr(self, "redis", None)
            key = f"{_NAMESPACE}:{key_builder(func, self, *args, **kwargs)}"

            if redis:
                cached = await redis.get(key)
                if cached is not None:
                    return json.loads(cached)

            result = await func(self, *args, **kwargs)

            if redis:
                await redis.set(key, json.dumps(result), ex=ttl)

            return result

        return wrapper

    return decorator
