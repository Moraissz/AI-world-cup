from unittest.mock import AsyncMock, MagicMock

import pytest
from dependency_injector import providers
from fastapi.testclient import TestClient

from app.exceptions import TeamNotFoundError
from main import app

H2H_RESPONSE = {
    "matchup": "Brazil vs France",
    "total_matches": 14,
    "historical_stats": {
        "team_a_wins": 6,
        "team_b_wins": 4,
        "draws": 4,
        "team_a_goals_scored": 18,
        "team_b_goals_scored": 14,
    },
    "recent_encounters": [
        {
            "date": "2022-12-10",
            "competition": "FIFA World Cup",
            "score": "France 1 - 0 Brazil",
        }
    ],
}


@pytest.fixture
def service_mock():
    mock = MagicMock()
    mock.generate_summary = AsyncMock(return_value=H2H_RESPONSE)
    return mock


@pytest.fixture
def client(service_mock):
    with app.container.football_service.override(providers.Object(service_mock)):
        yield TestClient(app)


def test_head_to_head_200(client):
    r = client.get("/football/head-to-head?name_team_a=Brazil&name_team_b=France")
    assert r.status_code == 200
    data = r.json()
    assert data["matchup"] == "Brazil vs France"
    assert data["total_matches"] == 14
    assert data["historical_stats"]["team_a_wins"] == 6
    assert len(data["recent_encounters"]) == 1


def test_head_to_head_missing_team_a_returns_422(client):
    r = client.get("/football/head-to-head?name_team_b=France")
    assert r.status_code == 422


def test_head_to_head_missing_team_b_returns_422(client):
    r = client.get("/football/head-to-head?name_team_a=Brazil")
    assert r.status_code == 422


def test_head_to_head_missing_both_returns_422(client):
    r = client.get("/football/head-to-head?name_team_a=&name_team_b=")
    assert r.status_code == 422


def test_head_to_head_team_not_found_returns_400(service_mock):
    service_mock.generate_summary = AsyncMock(side_effect=TeamNotFoundError("XYZ"))
    with app.container.football_service.override(providers.Object(service_mock)):
        r = TestClient(app).get("/football/head-to-head?name_team_a=XYZ&name_team_b=France")
    assert r.status_code == 400


def test_head_to_head_propagates_http_exception(service_mock):
    from fastapi import HTTPException

    service_mock.generate_summary = AsyncMock(
        side_effect=HTTPException(status_code=502, detail="upstream error")
    )
    with app.container.football_service.override(providers.Object(service_mock)):
        r = TestClient(app).get("/football/head-to-head?name_team_a=Brazil&name_team_b=France")
    assert r.status_code == 502


def test_head_to_head_unexpected_error_returns_500(service_mock):
    service_mock.generate_summary = AsyncMock(side_effect=RuntimeError("unexpected"))
    with app.container.football_service.override(providers.Object(service_mock)):
        r = TestClient(app, raise_server_exceptions=False).get(
            "/football/head-to-head?name_team_a=Brazil&name_team_b=France"
        )
    assert r.status_code == 500


def test_head_to_head_service_called_with_correct_names(client, service_mock):
    client.get("/football/head-to-head?name_team_a=Brazil&name_team_b=France")
    service_mock.generate_summary.assert_called_once_with("Brazil", "France")
