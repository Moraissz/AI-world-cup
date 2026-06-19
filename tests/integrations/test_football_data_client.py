from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.integrations.football_data_client import FootballDataClient

STANDINGS_FIXTURE = {
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
                }
            ],
        }
    ]
}

MATCHES_FIXTURE = {
    "matches": [
        {
            "utcDate": "2026-06-20T18:00:00Z",
            "status": "SCHEDULED",
            "stage": "GROUP_STAGE",
            "homeTeam": {"id": 1, "name": "Brazil"},
            "awayTeam": {"id": 2, "name": "Argentina"},
            "score": {"fullTime": {"home": None, "away": None}},
        }
    ]
}

TOP_SCORERS_FIXTURE = {
    "scorers": [
        {
            "player": {"id": 10, "name": "Neymar"},
            "team": {"id": 1, "name": "Brazil"},
            "goals": 3,
            "assists": 2,
        }
    ]
}


def _make_mock_response(data: dict, status_code: int = 200):
    response = MagicMock()
    response.status_code = status_code
    response.json.return_value = data
    return response


@pytest.fixture
def client():
    return FootballDataClient(api_key="test-key")


@pytest.mark.asyncio
async def test_fetch_standings_success(client):
    mock_response = _make_mock_response(STANDINGS_FIXTURE)
    with patch(
        "httpx.AsyncClient.get", new_callable=AsyncMock, return_value=mock_response
    ):
        result = await client.fetch_standings()
    assert result == STANDINGS_FIXTURE


@pytest.mark.asyncio
async def test_fetch_standings_502_on_server_error(client):
    from fastapi import HTTPException

    mock_response = _make_mock_response({}, status_code=503)
    with patch(
        "httpx.AsyncClient.get", new_callable=AsyncMock, return_value=mock_response
    ):
        with pytest.raises(HTTPException) as exc_info:
            await client.fetch_standings()
    assert exc_info.value.status_code == 502


@pytest.mark.asyncio
async def test_fetch_standings_429_on_rate_limit(client):
    from fastapi import HTTPException

    mock_response = _make_mock_response({}, status_code=429)
    with patch(
        "httpx.AsyncClient.get", new_callable=AsyncMock, return_value=mock_response
    ):
        with pytest.raises(HTTPException) as exc_info:
            await client.fetch_standings()
    assert exc_info.value.status_code == 429


@pytest.mark.asyncio
async def test_fetch_matches_success_no_filters(client):
    mock_response = _make_mock_response(MATCHES_FIXTURE)
    with patch(
        "httpx.AsyncClient.get", new_callable=AsyncMock, return_value=mock_response
    ) as mock_get:
        result = await client.fetch_matches()
    assert result == MATCHES_FIXTURE
    call_kwargs = mock_get.call_args.kwargs
    assert "dateFrom" not in call_kwargs.get("params", {})
    assert "status" not in call_kwargs.get("params", {})


@pytest.mark.asyncio
async def test_fetch_matches_with_date_range_and_status(client):
    from datetime import date

    mock_response = _make_mock_response(MATCHES_FIXTURE)
    with patch(
        "httpx.AsyncClient.get", new_callable=AsyncMock, return_value=mock_response
    ) as mock_get:
        result = await client.fetch_matches(
            date_from=date(2026, 6, 20), date_to=date(2026, 6, 22), status="FINISHED"
        )
    assert result == MATCHES_FIXTURE
    params = mock_get.call_args.kwargs["params"]
    assert params["dateFrom"] == "2026-06-20"
    assert params["dateTo"] == "2026-06-22"
    assert params["status"] == "FINISHED"


@pytest.mark.asyncio
async def test_fetch_matches_no_date_params_sent_when_missing(client):
    mock_response = _make_mock_response(MATCHES_FIXTURE)
    with patch(
        "httpx.AsyncClient.get", new_callable=AsyncMock, return_value=mock_response
    ) as mock_get:
        await client.fetch_matches(date_from=None, date_to=None)
    params = mock_get.call_args.kwargs.get("params", {})
    assert "dateFrom" not in params
    assert "dateTo" not in params


@pytest.mark.asyncio
async def test_fetch_top_scorers_success(client):
    mock_response = _make_mock_response(TOP_SCORERS_FIXTURE)
    with patch(
        "httpx.AsyncClient.get", new_callable=AsyncMock, return_value=mock_response
    ):
        result = await client.fetch_top_scorers()
    assert result == TOP_SCORERS_FIXTURE


@pytest.mark.asyncio
async def test_fetch_top_scorers_502_on_error(client):
    from fastapi import HTTPException

    mock_response = _make_mock_response({}, status_code=500)
    with patch(
        "httpx.AsyncClient.get", new_callable=AsyncMock, return_value=mock_response
    ):
        with pytest.raises(HTTPException) as exc_info:
            await client.fetch_top_scorers()
    assert exc_info.value.status_code == 502
