import datetime
import json

import redis.asyncio as aioredis
from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, HTTPException
from fastapi.params import Depends

from app.models.memory import MemoryResponse, MemoryTurnRequest
from container import AppContainer

memory_router = APIRouter(prefix="/memory", tags=["Conversation Memory"])

_KEY_PREFIX = "ai-world-cup-agent:memory:"
_TTL = 7 * 24 * 60 * 60  # 7 days
_MAX_HISTORY = 10


def _redis_key(chat_id: str) -> str:
    return f"{_KEY_PREFIX}{chat_id}"


async def _load(redis: aioredis.Redis, chat_id: str) -> dict:
    raw = await redis.get(_redis_key(chat_id))
    if raw is None:
        return {"last_teams": None, "preferred_language": None, "history": []}
    return json.loads(raw)


@memory_router.get(
    "/{chat_id}",
    response_model=MemoryResponse,
    summary="Carregar memória da conversa",
    description="Retorna o histórico e contexto persistido para um chat_id. Retorna estrutura vazia se não houver histórico.",
)
@inject
async def get_memory(
    chat_id: str,
    redis: aioredis.Redis = Depends(Provide[AppContainer.redis_client]),
):
    try:
        data = await _load(redis, chat_id)
        return MemoryResponse(chat_id=chat_id, **data)
    except Exception:
        return MemoryResponse(chat_id=chat_id, last_teams=None, preferred_language=None, history=[])


@memory_router.post(
    "/{chat_id}",
    response_model=MemoryResponse,
    summary="Salvar turno na memória da conversa",
    description="Adiciona um par usuário/agente ao histórico e atualiza last_teams e preferred_language se fornecidos. TTL de 7 dias.",
)
@inject
async def save_memory_turn(
    chat_id: str,
    body: MemoryTurnRequest,
    redis: aioredis.Redis = Depends(Provide[AppContainer.redis_client]),
):
    try:
        memory = await _load(redis, chat_id)
        ts = datetime.datetime.utcnow().isoformat()
        memory["history"].append({"role": "user", "text": body.user_msg, "ts": ts})
        memory["history"].append({"role": "agent", "text": body.agent_rep, "ts": ts})
        memory["history"] = memory["history"][-_MAX_HISTORY * 2:]

        if body.team_a and body.team_b:
            memory["last_teams"] = [body.team_a, body.team_b]
        if body.preferred_language:
            memory["preferred_language"] = body.preferred_language

        await redis.set(
            _redis_key(chat_id),
            json.dumps(memory, ensure_ascii=False),
            ex=_TTL,
        )
        return MemoryResponse(chat_id=chat_id, **memory)
    except Exception:
        raise HTTPException(status_code=500, detail="Erro ao salvar memória.")
