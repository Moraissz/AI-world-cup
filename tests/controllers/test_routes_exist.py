"""
Contract tests: verify that all four agent-called routes exist and that
?status=live (invalid enum) returns 422 while ?status=IN_PLAY returns 200.
These tests fail immediately if a route is removed or the enum value regresses.
"""
from unittest.mock import AsyncMock, MagicMock

from dependency_injector import providers
from fastapi.testclient import TestClient

from app.models.football_base import GroupStanding, Match, MatchScore, TopScorer
from app.models.football_response import MatchesResponse, StandingsResponse, TopScorersResponse
from main import app


def _stub_service():
    mock = MagicMock()
    mock.get_standings = AsyncMock(return_value=StandingsResponse(groups=[]))
    mock.get_matches = AsyncMock(return_value=MatchesResponse(matches=[]))
    mock.get_top_scorers = AsyncMock(return_value=TopScorersResponse(scorers=[]))
    mock.generate_summary = AsyncMock(
        return_value={
            "matchup": "A vs B",
            "total_matches": 0,
            "historical_stats": {
                "team_a_wins": 0,
                "team_b_wins": 0,
                "draws": 0,
                "team_a_goals_scored": 0,
                "team_b_goals_scored": 0,
            },
            "recent_encounters": [],
        }
    )
    return mock


def test_head_to_head_route_exists():
    with app.container.football_service.override(providers.Object(_stub_service())):
        r = TestClient(app).get("/football/head-to-head?name_team_a=A&name_team_b=B")
    assert r.status_code == 200


def test_standings_route_exists():
    with app.container.football_service.override(providers.Object(_stub_service())):
        r = TestClient(app).get("/football/world-cup/standings")
    assert r.status_code == 200


def test_matches_route_exists():
    with app.container.football_service.override(providers.Object(_stub_service())):
        r = TestClient(app).get("/football/world-cup/matches")
    assert r.status_code == 200


def test_top_scorers_route_exists():
    with app.container.football_service.override(providers.Object(_stub_service())):
        r = TestClient(app).get("/football/world-cup/top-scorers")
    assert r.status_code == 200


def test_status_live_returns_422():
    """Regression guard: ?status=live is invalid; agent prompt must use IN_PLAY."""
    with app.container.football_service.override(providers.Object(_stub_service())):
        r = TestClient(app).get("/football/world-cup/matches?status=live")
    assert r.status_code == 422


def test_status_in_play_accepted():
    with app.container.football_service.override(providers.Object(_stub_service())):
        r = TestClient(app).get("/football/world-cup/matches?status=IN_PLAY")
    assert r.status_code == 200
