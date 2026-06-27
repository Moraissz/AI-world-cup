import datetime
import json

import redis.asyncio as aioredis

from app.models.memory import MemoryTurnRequest

_KEY_PREFIX = "ai-world-cup-agent:memory:"
_TTL = 7 * 24 * 60 * 60
_MAX_HISTORY = 10


class MemoryService:
    def __init__(self, redis_client: aioredis.Redis):
        self._redis = redis_client

    def _key(self, chat_id: str) -> str:
        return f"{_KEY_PREFIX}{chat_id}"

    async def load(self, chat_id: str) -> dict:
        raw = await self._redis.get(self._key(chat_id))
        if raw is None:
            return {"last_teams": None, "preferred_language": None, "history": []}
        return json.loads(raw)

    async def save_turn(self, chat_id: str, body: MemoryTurnRequest) -> dict:
        memory = await self.load(chat_id)
        ts = datetime.datetime.utcnow().isoformat()
        memory["history"].append({"role": "user", "text": body.user_msg, "ts": ts})
        memory["history"].append({"role": "agent", "text": body.agent_rep, "ts": ts})
        memory["history"] = memory["history"][-_MAX_HISTORY * 2:]

        if body.team_a and body.team_b:
            memory["last_teams"] = [body.team_a, body.team_b]
        if body.preferred_language:
            memory["preferred_language"] = body.preferred_language

        await self._redis.set(
            self._key(chat_id),
            json.dumps(memory, ensure_ascii=False),
            ex=_TTL,
        )
        return memory
