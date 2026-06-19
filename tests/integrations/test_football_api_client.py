from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.integrations.football_api_client import FootballApiClient

SEARCH_TEAM_FIXTURE = {
    "response": [
        {"team": {"id": 6, "name": "Brazil"}},
        {"team": {"id": 7, "name": "Brazil U23"}},
    ]
}

HEAD_TO_HEAD_FIXTURE = {
    "response": [
        {
            "fixture": {"date": "2022-11-24T16:00:00+00:00"},
            "league": {"name": "FIFA World Cup"},
            "teams": {
                "home": {"id": 6, "name": "Brazil"},
                "away": {"id": 2, "name": "Serbia"},
            },
            "goals": {"home": 2, "away": 0},
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
    return FootballApiClient(api_key="test-key")


@pytest.mark.asyncio
async def test_search_team_id_success(client):
    mock_response = _make_mock_response(SEARCH_TEAM_FIXTURE)
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock, return_value=mock_response):
        result = await client.search_team_id("Brazil")
    assert result == SEARCH_TEAM_FIXTURE["response"]
    assert len(result) == 2
    assert result[0]["team"]["id"] == 6


@pytest.mark.asyncio
async def test_search_team_id_empty_response(client):
    mock_response = _make_mock_response({"response": []})
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock, return_value=mock_response):
        result = await client.search_team_id("UnknownTeam")
    assert result == []


@pytest.mark.asyncio
async def test_search_team_id_empty_name_raises_value_error(client):
    with pytest.raises(ValueError, match="obrigatório"):
        await client.search_team_id("")


@pytest.mark.asyncio
async def test_search_team_id_502_on_api_error(client):
    from fastapi import HTTPException

    mock_response = _make_mock_response({}, status_code=503)
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock, return_value=mock_response):
        with pytest.raises(HTTPException) as exc_info:
            await client.search_team_id("Brazil")
    assert exc_info.value.status_code == 502


@pytest.mark.asyncio
async def test_fetch_head_to_head_success(client):
    mock_response = _make_mock_response(HEAD_TO_HEAD_FIXTURE)
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock, return_value=mock_response) as mock_get:
        result = await client.fetch_head_to_head(6, 2)
    assert result == HEAD_TO_HEAD_FIXTURE
    url = mock_get.call_args.args[0]
    assert "h2h=6-2" in url


@pytest.mark.asyncio
async def test_fetch_head_to_head_502_on_api_error(client):
    from fastapi import HTTPException

    mock_response = _make_mock_response({}, status_code=500)
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock, return_value=mock_response):
        with pytest.raises(HTTPException) as exc_info:
            await client.fetch_head_to_head(6, 2)
    assert exc_info.value.status_code == 502


@pytest.mark.asyncio
async def test_fetch_head_to_head_zero_id_raises_value_error(client):
    with pytest.raises(ValueError, match="obrigatórios"):
        await client.fetch_head_to_head(0, 2)
