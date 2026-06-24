from unittest.mock import AsyncMock, MagicMock

import pytest

from app.exceptions import TeamNotFoundError
from app.integrations.football_api_client import FootballApiClient
from app.services.football_service import FootballService

BRAZIL_SEARCH = [
    {"team": {"id": 6, "name": "Brazil", "national": True}},
    {"team": {"id": 7, "name": "Brazil U23", "national": False}},
]

FRANCE_SEARCH = [
    {"team": {"id": 2, "name": "France", "national": True}},
]

H2H_RAW = {
    "response": [
        {
            "fixture": {"date": "2022-12-10T20:00:00+00:00"},
            "league": {"name": "FIFA World Cup"},
            "teams": {
                "home": {"id": 2, "name": "France"},
                "away": {"id": 6, "name": "Brazil"},
            },
            "score": {"fulltime": {"home": 1, "away": 0}},
        },
        {
            "fixture": {"date": "2019-06-02T21:00:00+00:00"},
            "league": {"name": "International Friendly"},
            "teams": {
                "home": {"id": 6, "name": "Brazil"},
                "away": {"id": 2, "name": "France"},
            },
            "score": {"fulltime": {"home": 3, "away": 1}},
        },
    ]
}

H2H_EMPTY = {"response": []}


def _make_service(search_results=None, h2h_results=None):
    mock_api_client = MagicMock(spec=FootballApiClient)

    search_map = search_results or {}
    call_count = [0]

    async def search_side_effect(team_name):
        call_count[0] += 1
        for key, val in search_map.items():
            if key.lower() == team_name.lower():
                return val
        return []

    mock_api_client.search_team_id = search_side_effect
    mock_api_client.fetch_head_to_head = AsyncMock(return_value=h2h_results or H2H_EMPTY)

    mock_data_client = MagicMock()
    return FootballService(
        football_io_sports_client=mock_api_client,
        football_data_org_client=mock_data_client,
    )


@pytest.mark.asyncio
async def test_generate_summary_returns_correct_structure():
    service = _make_service(
        search_results={"Brazil": BRAZIL_SEARCH, "France": FRANCE_SEARCH},
        h2h_results=H2H_RAW,
    )
    result = await service.generate_summary("Brazil", "France")
    assert result["matchup"] == "Brazil vs France"
    assert result["total_matches"] == 2
    assert "historical_stats" in result
    assert "recent_encounters" in result


@pytest.mark.asyncio
async def test_generate_summary_counts_wins_correctly():
    service = _make_service(
        search_results={"Brazil": BRAZIL_SEARCH, "France": FRANCE_SEARCH},
        h2h_results=H2H_RAW,
    )
    result = await service.generate_summary("Brazil", "France")
    stats = result["historical_stats"]
    # Match 1: France 1-0 Brazil → team_b (France) wins → team_b_wins += 1
    # Match 2: Brazil 3-1 France → team_a (Brazil) wins → team_a_wins += 1
    assert stats["team_a_wins"] == 1
    assert stats["team_b_wins"] == 1
    assert stats["draws"] == 0


@pytest.mark.asyncio
async def test_generate_summary_counts_goals_correctly():
    service = _make_service(
        search_results={"Brazil": BRAZIL_SEARCH, "France": FRANCE_SEARCH},
        h2h_results=H2H_RAW,
    )
    result = await service.generate_summary("Brazil", "France")
    stats = result["historical_stats"]
    # Match 1 (France home): Brazil away→ team_a_goals += away_goals=0, team_b_goals += home_goals=1
    # Match 2 (Brazil home): Brazil home→ team_a_goals += home_goals=3, team_b_goals += away_goals=1
    assert stats["team_a_goals_scored"] == 3
    assert stats["team_b_goals_scored"] == 2


@pytest.mark.asyncio
async def test_generate_summary_empty_history():
    service = _make_service(
        search_results={"Brazil": BRAZIL_SEARCH, "France": FRANCE_SEARCH},
        h2h_results=H2H_EMPTY,
    )
    result = await service.generate_summary("Brazil", "France")
    assert result["total_matches"] == 0
    assert result["historical_stats"]["team_a_wins"] == 0
    assert result["recent_encounters"] == []


@pytest.mark.asyncio
async def test_generate_summary_team_not_found_raises_team_not_found_error():
    service = _make_service(
        search_results={"Brazil": BRAZIL_SEARCH},
    )
    with pytest.raises(TeamNotFoundError) as exc_info:
        await service.generate_summary("Brazil", "Atlantis")
    assert "não encontrada" in exc_info.value.detail


@pytest.mark.asyncio
async def test_generate_summary_only_national_team_selected():
    service = _make_service(
        search_results={"Brazil": BRAZIL_SEARCH, "France": FRANCE_SEARCH},
        h2h_results=H2H_EMPTY,
    )
    # Both teams found; should pick national=True (id=6), not U23 (id=7)
    result = await service.generate_summary("Brazil", "France")
    # fetch_head_to_head should be called with id=6 (Brazil national), not 7 (U23)
    service.football_io_sports_client.fetch_head_to_head.assert_called_once_with(6, 2)


@pytest.mark.asyncio
async def test_generate_summary_recent_encounters_sorted_desc():
    service = _make_service(
        search_results={"Brazil": BRAZIL_SEARCH, "France": FRANCE_SEARCH},
        h2h_results=H2H_RAW,
    )
    result = await service.generate_summary("Brazil", "France")
    dates = [e["date"] for e in result["recent_encounters"]]
    assert dates == sorted(dates, reverse=True)


@pytest.mark.asyncio
async def test_generate_summary_empty_team_names_returns_empty():
    service = _make_service()
    result = await service.generate_summary("", "")
    assert result == {}
