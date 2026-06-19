from unittest.mock import AsyncMock, MagicMock

import pytest

from app.integrations.football_data_client import FootballDataClient
from app.services.football_service import FootballService


def _make_service(fetch_standings=None, fetch_matches=None, fetch_top_scorers=None):
    mock_data_client = MagicMock(spec=FootballDataClient)
    mock_data_client.fetch_standings = AsyncMock(return_value=fetch_standings or {})
    mock_data_client.fetch_matches = AsyncMock(return_value=fetch_matches or {})
    mock_data_client.fetch_top_scorers = AsyncMock(return_value=fetch_top_scorers or {})
    mock_api_client = MagicMock()
    return FootballService(
        football_io_sports_client=mock_api_client,
        football_data_org_client=mock_data_client,
    )


STANDINGS_DATA = {
    "standings": [
        {
            "stage": "GROUP_STAGE",
            "type": "TOTAL",
            "group": "GROUP_A",
            "table": [
                {
                    "position": 1,
                    "team": {"id": 1, "name": "Brazil"},
                    "playedGames": 3,
                    "won": 2,
                    "draw": 1,
                    "lost": 0,
                    "points": 7,
                    "goalsFor": 5,
                    "goalsAgainst": 2,
                    "goalDifference": 3,
                },
                {
                    "position": 2,
                    "team": {"id": 2, "name": "Germany"},
                    "playedGames": 3,
                    "won": 1,
                    "draw": 1,
                    "lost": 1,
                    "points": 4,
                    "goalsFor": 3,
                    "goalsAgainst": 3,
                    "goalDifference": 0,
                },
            ],
        },
        {
            "stage": "GROUP_STAGE",
            "type": "HOME",
            "group": "GROUP_A",
            "table": [],
        },
    ]
}

MATCHES_DATA = {
    "matches": [
        {
            "utcDate": "2026-06-20T18:00:00Z",
            "status": "FINISHED",
            "stage": "GROUP_STAGE",
            "homeTeam": {"id": 1, "name": "Brazil"},
            "awayTeam": {"id": 2, "name": "Argentina"},
            "score": {"fullTime": {"home": 2, "away": 1}},
        },
        {
            "utcDate": "2026-06-22T21:00:00Z",
            "status": "SCHEDULED",
            "stage": "GROUP_STAGE",
            "homeTeam": {"id": 3, "name": "France"},
            "awayTeam": {"id": 4, "name": "Germany"},
            "score": {"fullTime": {"home": None, "away": None}},
        },
    ]
}

TOP_SCORERS_DATA = {
    "scorers": [
        {
            "player": {"name": "Neymar"},
            "team": {"name": "Brazil"},
            "goals": 3,
            "assists": 2,
        },
        {
            "player": {"name": "Mbappe"},
            "team": {"name": "France"},
            "goals": 2,
            "assists": 1,
        },
    ]
}


@pytest.mark.asyncio
async def test_get_standings_filters_total_only():
    service = _make_service(fetch_standings=STANDINGS_DATA)
    result = await service.get_standings()
    assert len(result.groups) == 1
    assert result.groups[0].group == "GROUP_A"
    assert len(result.groups[0].standings) == 2
    first = result.groups[0].standings[0]
    assert first.team == "Brazil"
    assert first.points == 7
    assert first.won == 2
    assert first.goal_difference == 3


@pytest.mark.asyncio
async def test_get_standings_empty():
    service = _make_service(fetch_standings={"standings": []})
    result = await service.get_standings()
    assert result.groups == []


@pytest.mark.asyncio
async def test_get_matches_no_filters():
    service = _make_service(fetch_matches=MATCHES_DATA)
    result = await service.get_matches()
    assert len(result.matches) == 2


@pytest.mark.asyncio
async def test_get_matches_filter_by_team():
    service = _make_service(fetch_matches=MATCHES_DATA)
    result = await service.get_matches(teams=["Brazil"])
    assert len(result.matches) == 1
    assert result.matches[0].home_team == "Brazil"


@pytest.mark.asyncio
async def test_get_matches_team_filter_case_insensitive():
    service = _make_service(fetch_matches=MATCHES_DATA)
    result = await service.get_matches(teams=["brazil"])
    assert len(result.matches) == 1


@pytest.mark.asyncio
async def test_get_matches_no_team_match_returns_empty():
    service = _make_service(fetch_matches=MATCHES_DATA)
    result = await service.get_matches(teams=["Spain"])
    assert result.matches == []


@pytest.mark.asyncio
async def test_get_matches_status_forwarded_to_client():
    from app.models.football_base import MatchStatus

    service = _make_service(fetch_matches={"matches": []})
    await service.get_matches(status=MatchStatus.IN_PLAY)
    service.football_data_org_client.fetch_matches.assert_called_once_with(
        date_from=None, date_to=None, status=MatchStatus.IN_PLAY
    )


@pytest.mark.asyncio
async def test_get_matches_with_date_range():
    from datetime import date

    service = _make_service(fetch_matches={"matches": []})
    d_from, d_to = date(2026, 6, 20), date(2026, 6, 22)
    await service.get_matches(date_from=d_from, date_to=d_to)
    service.football_data_org_client.fetch_matches.assert_called_once_with(
        date_from=d_from, date_to=d_to, status=None
    )


@pytest.mark.asyncio
async def test_get_matches_score_mapping():
    service = _make_service(fetch_matches=MATCHES_DATA)
    result = await service.get_matches()
    finished = result.matches[0]
    assert finished.score.home == 2
    assert finished.score.away == 1
    scheduled = result.matches[1]
    assert scheduled.score.home is None
    assert scheduled.score.away is None


@pytest.mark.asyncio
async def test_get_top_scorers():
    service = _make_service(fetch_top_scorers=TOP_SCORERS_DATA)
    result = await service.get_top_scorers()
    assert len(result.scorers) == 2
    assert result.scorers[0].position == 1
    assert result.scorers[0].player == "Neymar"
    assert result.scorers[0].goals == 3
    assert result.scorers[0].assists == 2
    assert result.scorers[1].position == 2
    assert result.scorers[1].player == "Mbappe"


@pytest.mark.asyncio
async def test_get_top_scorers_empty():
    service = _make_service(fetch_top_scorers={"scorers": []})
    result = await service.get_top_scorers()
    assert result.scorers == []
