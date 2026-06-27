from unittest.mock import AsyncMock, MagicMock

import pytest
from dependency_injector import providers
from fastapi.testclient import TestClient

from main import app

_H2H = {
    "matchup": "Brazil vs France",
    "total_matches": 1,
    "historical_stats": {
        "team_a_wins": 1,
        "team_b_wins": 0,
        "draws": 0,
        "team_a_goals_scored": 1,
        "team_b_goals_scored": 0,
    },
    "recent_encounters": [],
}


@pytest.fixture
def service_mock():
    mock = MagicMock()
    mock.generate_summary = AsyncMock(return_value=_H2H)
    return mock


@pytest.fixture
def client(service_mock):
    with app.container.football_service.override(providers.Object(service_mock)):
        yield TestClient(app)


def test_response_includes_request_id_header(client):
    r = client.get("/football/head-to-head?name_team_a=Brazil&name_team_b=France")
    assert r.status_code == 200
    assert "x-request-id" in r.headers


def test_response_echoes_provided_request_id(client):
    r = client.get(
        "/football/head-to-head?name_team_a=Brazil&name_team_b=France",
        headers={"X-Request-Id": "test-id-abc123"},
    )
    assert r.status_code == 200
    assert r.headers.get("x-request-id") == "test-id-abc123"


def _make_redis():
    store = {}
    redis = AsyncMock()

    async def get(key):
        return store.get(key)

    async def set(key, value, ex=None):
        store[key] = value

    redis.get = get
    redis.set = set
    return redis


def test_json_post_body_reaches_endpoint_through_middleware():
    """Regression: LoggingMiddleware reads the request body for logging; it must
    re-arm the stream so the downstream route still receives it. Before the fix this
    JSON POST deadlocked under a real server (TestClient won't hang, but a broken
    middleware that consumes the body without replay yields an empty/!=200 body)."""
    with app.container.redis_client.override(providers.Object(_make_redis())):
        r = TestClient(app).post(
            "/memory/mw-regression",
            json={
                "user_msg": "Brasil x Argentina",
                "agent_rep": "Resposta. ⚽",
                "team_a": "Brazil",
                "team_b": "Argentina",
                "preferred_language": "pt",
            },
        )
    assert r.status_code == 200
    body = r.json()
    assert body["last_teams"] == ["Brazil", "Argentina"]
    assert len(body["history"]) == 2
