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
