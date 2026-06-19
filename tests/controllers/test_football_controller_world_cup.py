from unittest.mock import AsyncMock, MagicMock

import pytest
from dependency_injector import providers
from fastapi.testclient import TestClient

from app.models.football_base import (
    GroupStanding,
    Match,
    MatchScore,
    TeamStanding,
    TopScorer,
)
from app.models.football_response import (
    MatchesResponse,
    StandingsResponse,
    TopScorersResponse,
)
from main import app

STANDINGS_RESPONSE = StandingsResponse(
    groups=[
        GroupStanding(
            group="GROUP_A",
            standings=[
                TeamStanding(
                    position=1,
                    team="Brazil",
                    played=3,
                    won=2,
                    draw=1,
                    lost=0,
                    goals_for=5,
                    goals_against=2,
                    goal_difference=3,
                    points=7,
                )
            ],
        )
    ]
)

MATCHES_RESPONSE = MatchesResponse(
    matches=[
        Match(
            utc_date="2026-06-20T18:00:00Z",
            home_team="Brazil",
            away_team="Argentina",
            score=MatchScore(home=2, away=1),
            status="FINISHED",
            stage="GROUP_STAGE",
        )
    ]
)

TOP_SCORERS_RESPONSE = TopScorersResponse(
    scorers=[TopScorer(position=1, player="Neymar", team="Brazil", goals=3, assists=2)]
)


@pytest.fixture
def service_mock():
    mock = MagicMock()
    mock.get_standings = AsyncMock(return_value=STANDINGS_RESPONSE)
    mock.get_matches = AsyncMock(return_value=MATCHES_RESPONSE)
    mock.get_top_scorers = AsyncMock(return_value=TOP_SCORERS_RESPONSE)
    return mock


@pytest.fixture
def client(service_mock):
    with app.container.football_service.override(providers.Object(service_mock)):
        yield TestClient(app)


def test_get_standings_200(client):
    response = client.get("/football/world-cup/standings")
    assert response.status_code == 200
    data = response.json()
    assert "groups" in data
    assert data["groups"][0]["group"] == "GROUP_A"
    assert data["groups"][0]["standings"][0]["team"] == "Brazil"
    assert data["groups"][0]["standings"][0]["points"] == 7


def test_get_matches_200_no_filters(client, service_mock):
    response = client.get("/football/world-cup/matches")
    assert response.status_code == 200
    data = response.json()
    assert "matches" in data
    assert len(data["matches"]) == 1
    service_mock.get_matches.assert_called_once_with(
        teams=None, date_from=None, date_to=None, status=None
    )


def test_get_matches_with_team_filter(client, service_mock):
    response = client.get("/football/world-cup/matches?teams=Brazil")
    assert response.status_code == 200
    service_mock.get_matches.assert_called_once_with(
        teams=["Brazil"], date_from=None, date_to=None, status=None
    )


def test_get_matches_with_multiple_teams_filter(client, service_mock):
    response = client.get("/football/world-cup/matches?teams=Brazil&teams=France")
    assert response.status_code == 200
    service_mock.get_matches.assert_called_once_with(
        teams=["Brazil", "France"], date_from=None, date_to=None, status=None
    )


def test_get_matches_with_date_range(client, service_mock):
    from datetime import date

    response = client.get(
        "/football/world-cup/matches?date_from=2026-06-20&date_to=2026-06-22"
    )
    assert response.status_code == 200
    service_mock.get_matches.assert_called_once_with(
        teams=None, date_from=date(2026, 6, 20), date_to=date(2026, 6, 22), status=None
    )


def test_get_matches_only_date_from_returns_400(client):
    response = client.get("/football/world-cup/matches?date_from=2026-06-20")
    assert response.status_code == 400


def test_get_matches_only_date_to_returns_400(client):
    response = client.get("/football/world-cup/matches?date_to=2026-06-20")
    assert response.status_code == 400


def test_get_matches_invalid_date_returns_422(client):
    response = client.get("/football/world-cup/matches?date_from=hoje&date_to=hoje")
    assert response.status_code == 422


def test_get_matches_with_status_filter(client, service_mock):
    response = client.get("/football/world-cup/matches?status=IN_PLAY")
    assert response.status_code == 200
    service_mock.get_matches.assert_called_once_with(
        teams=None, date_from=None, date_to=None, status="IN_PLAY"
    )


def test_get_matches_combined_filters(client, service_mock):
    from datetime import date

    response = client.get(
        "/football/world-cup/matches?teams=France&teams=Brazil&date_from=2026-06-22&date_to=2026-06-22&status=IN_PLAY"
    )
    assert response.status_code == 200
    service_mock.get_matches.assert_called_once_with(
        teams=["France", "Brazil"],
        date_from=date(2026, 6, 22),
        date_to=date(2026, 6, 22),
        status="IN_PLAY",
    )


def test_get_top_scorers_200(client):
    response = client.get("/football/world-cup/top-scorers")
    assert response.status_code == 200
    data = response.json()
    assert "scorers" in data
    assert data["scorers"][0]["player"] == "Neymar"
    assert data["scorers"][0]["goals"] == 3


def test_get_standings_500_on_unexpected_error(service_mock):
    service_mock.get_standings = AsyncMock(side_effect=RuntimeError("unexpected"))
    with app.container.football_service.override(providers.Object(service_mock)):
        c = TestClient(app)
        response = c.get("/football/world-cup/standings")
    assert response.status_code == 500


def test_get_standings_propagates_http_exception(service_mock):
    from fastapi import HTTPException

    service_mock.get_standings = AsyncMock(
        side_effect=HTTPException(status_code=429, detail="rate limited")
    )
    with app.container.football_service.override(providers.Object(service_mock)):
        c = TestClient(app)
        response = c.get("/football/world-cup/standings")
    assert response.status_code == 429


def test_get_top_scorers_propagates_http_exception(service_mock):
    from fastapi import HTTPException

    service_mock.get_top_scorers = AsyncMock(
        side_effect=HTTPException(status_code=502, detail="upstream error")
    )
    with app.container.football_service.override(providers.Object(service_mock)):
        c = TestClient(app)
        response = c.get("/football/world-cup/top-scorers")
    assert response.status_code == 502
