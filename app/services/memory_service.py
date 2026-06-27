import datetime
import json

import redis.asyncio as aioredis
import structlog
from fastapi import HTTPException
from redis.exceptions import RedisError

from app.models.memory import MemoryTurnRequest

logger = structlog.get_logger(__name__)

_KEY_PREFIX = "ai-world-cup-agent:memory:"
_TTL = 7 * 24 * 60 * 60
_MAX_HISTORY = 10
_UNAVAILABLE_DETAIL = (
    "Memory service unavailable: Redis is required for conversation persistence."
)


class MemoryService:
    def __init__(self, redis_client: aioredis.Redis | None = None):
        self._redis = redis_client

    def _key(self, chat_id: str) -> str:
        return f"{_KEY_PREFIX}{chat_id}"

    def _require_redis(self) -> aioredis.Redis:
        if self._redis is None:
            raise HTTPException(status_code=503, detail=_UNAVAILABLE_DETAIL)
        return self._redis

    async def load(self, chat_id: str) -> dict:
        redis = self._require_redis()
        try:
            raw = await redis.get(self._key(chat_id))
        except RedisError as exc:
            logger.error("memory.load_failed", chat_id=chat_id, error=str(exc))
            raise HTTPException(status_code=503, detail=_UNAVAILABLE_DETAIL)

        if raw is None:
            return {"last_teams": None, "preferred_language": None, "history": []}
        return json.loads(raw)

    async def save_turn(self, chat_id: str, body: MemoryTurnRequest) -> dict:
        redis = self._require_redis()
        memory = await self.load(chat_id)
        ts = datetime.datetime.utcnow().isoformat()
        memory["history"].append({"role": "user", "text": body.user_msg, "ts": ts})
        memory["history"].append({"role": "agent", "text": body.agent_rep, "ts": ts})
        memory["history"] = memory["history"][-_MAX_HISTORY * 2:]

        if body.team_a and body.team_b:
            memory["last_teams"] = [body.team_a, body.team_b]
        if body.preferred_language:
            memory["preferred_language"] = body.preferred_language

        try:
            await redis.set(
                self._key(chat_id),
                json.dumps(memory, ensure_ascii=False),
                ex=_TTL,
            )
        except RedisError as exc:
            logger.error("memory.save_failed", chat_id=chat_id, error=str(exc))
            raise HTTPException(status_code=503, detail=_UNAVAILABLE_DETAIL)

        return memory
