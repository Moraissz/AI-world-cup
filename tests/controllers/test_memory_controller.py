"""
Contract tests for GET/POST /memory/{chat_id}.
Verifies the schema SOUL.md depends on: last_teams, preferred_language, history.
Uses an in-process Redis mock — no real Redis required.
"""
import json
from unittest.mock import AsyncMock

import pytest
from dependency_injector import providers
from fastapi.testclient import TestClient

from app.services.memory_service import MemoryService
from main import app


def _make_redis():
    """In-memory Redis stub with get/set."""
    store = {}
    redis = AsyncMock()

    async def get(key):
        return store.get(key)

    async def set(key, value, ex=None):
        store[key] = value

    redis.get = get
    redis.set = set
    return redis


def test_get_memory_empty_returns_defaults():
    """SOUL.md expects GET returns {last_teams: null, history: [], preferred_language: null}."""
    with app.container.redis_client.override(providers.Object(_make_redis())):
        r = TestClient(app).get("/memory/testchat123")
    assert r.status_code == 200
    body = r.json()
    assert body["chat_id"] == "testchat123"
    assert body["last_teams"] is None
    assert body["preferred_language"] is None
    assert body["history"] == []


def test_post_memory_saves_and_returns():
    """SOUL.md POST payload: user_msg, agent_rep, team_a, team_b, preferred_language."""
    redis = _make_redis()
    with app.container.redis_client.override(providers.Object(redis)):
        client = TestClient(app)
        r = client.post(
            "/memory/testchat123",
            json={
                "user_msg": "Brazil vs France",
                "agent_rep": "Brazil leads 6-4 in h2h. ⚽",
                "team_a": "Brazil",
                "team_b": "France",
                "preferred_language": "en",
            },
        )
    assert r.status_code == 200
    body = r.json()
    assert body["last_teams"] == ["Brazil", "France"]
    assert body["preferred_language"] == "en"
    assert len(body["history"]) == 2
    assert body["history"][0]["role"] == "user"
    assert body["history"][1]["role"] == "agent"


def test_post_memory_round_trip():
    """Save then load — GET sees what POST saved."""
    redis = _make_redis()
    with app.container.redis_client.override(providers.Object(redis)):
        client = TestClient(app)
        client.post(
            "/memory/chat-abc",
            json={
                "user_msg": "Brasil x Argentina",
                "agent_rep": "Brasil vence! ⚽",
                "team_a": "Brazil",
                "team_b": "Argentina",
                "preferred_language": "pt",
            },
        )
        r = client.get("/memory/chat-abc")
    assert r.status_code == 200
    body = r.json()
    assert body["last_teams"] == ["Brazil", "Argentina"]
    assert body["preferred_language"] == "pt"


def test_post_memory_no_teams_preserves_last_teams():
    """Empty team_a/team_b must not overwrite existing last_teams."""
    redis = _make_redis()
    with app.container.redis_client.override(providers.Object(redis)):
        client = TestClient(app)
        # First turn sets teams
        client.post(
            "/memory/chat-xyz",
            json={
                "user_msg": "Brazil vs France",
                "agent_rep": "h2h ⚽",
                "team_a": "Brazil",
                "team_b": "France",
                "preferred_language": "en",
            },
        )
        # Second turn is a greeting — no teams
        client.post(
            "/memory/chat-xyz",
            json={
                "user_msg": "oi",
                "agent_rep": "Olá! ⚽",
                "team_a": "",
                "team_b": "",
                "preferred_language": "pt",
            },
        )
        r = client.get("/memory/chat-xyz")
    body = r.json()
    # last_teams should still reflect the last match discussed, not cleared
    assert body["last_teams"] == ["Brazil", "France"]


_UNAVAILABLE_DETAIL = (
    "Memory service unavailable: Redis is required for conversation persistence."
)


def test_get_memory_without_redis_returns_503():
    """REDIS_HOST unset → None injected → GET fails visibly with 503, never empty."""
    with app.container.memory_service.override(providers.Object(MemoryService(None))):
        r = TestClient(app).get("/memory/no-redis-chat")
    assert r.status_code == 503
    assert r.json()["detail"] == _UNAVAILABLE_DETAIL


def test_post_memory_without_redis_returns_503():
    """No Redis → POST must not fake success; returns 503."""
    with app.container.memory_service.override(providers.Object(MemoryService(None))):
        r = TestClient(app).post(
            "/memory/no-redis-chat",
            json={
                "user_msg": "Brazil vs France",
                "agent_rep": "h2h ⚽",
                "team_a": "Brazil",
                "team_b": "France",
                "preferred_language": "en",
            },
        )
    assert r.status_code == 503
    assert r.json()["detail"] == _UNAVAILABLE_DETAIL


def test_memory_redis_failure_returns_503_not_500():
    """Redis present but down → RedisError → 503 (visible), never a generic 500."""
    from redis.exceptions import ConnectionError as RedisConnectionError

    redis = AsyncMock()

    async def boom(*args, **kwargs):
        raise RedisConnectionError("redis down")

    redis.get = boom
    redis.set = boom

    with app.container.memory_service.override(providers.Object(MemoryService(redis))):
        client = TestClient(app)
        r_get = client.get("/memory/down-chat")
        r_post = client.post(
            "/memory/down-chat",
            json={"user_msg": "oi", "agent_rep": "olá ⚽", "team_a": "", "team_b": ""},
        )
    assert r_get.status_code == 503
    assert r_get.json()["detail"] == _UNAVAILABLE_DETAIL
    assert r_post.status_code == 503
    assert r_post.json()["detail"] == _UNAVAILABLE_DETAIL


def test_post_memory_history_capped_at_20_entries():
    """History must not grow beyond 20 entries (10 turns × 2 messages)."""
    redis = _make_redis()
    with app.container.redis_client.override(providers.Object(redis)):
        client = TestClient(app)
        for i in range(15):
            client.post(
                "/memory/chat-cap",
                json={
                    "user_msg": f"msg {i}",
                    "agent_rep": f"rep {i}",
                    "team_a": "",
                    "team_b": "",
                },
            )
        r = client.get("/memory/chat-cap")
    body = r.json()
    assert len(body["history"]) <= 20
