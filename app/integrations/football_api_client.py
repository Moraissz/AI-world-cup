import httpx
from tenacity import retry, retry_if_not_exception_type, stop_after_attempt, wait_fixed
from fastapi import HTTPException

_retry = retry(
    stop=stop_after_attempt(3),
    wait=wait_fixed(2),
    retry=retry_if_not_exception_type((HTTPException, ValueError)),
    reraise=True,
)


class FootballApiClient:
    def __init__(self, api_key: str):
        self.api_url = "https://v3.football.api-sports.io"
        self.headers = {
            "x-rapidapi-key": api_key,
            "x-rapidapi-host": "v3.football-api-sports.io",
        }

    @_retry
    async def search_team_id(self, team_name: str) -> list:
        if not team_name:
            raise ValueError("O nome da seleção é obrigatório.")

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.api_url}/teams?search={team_name}",
                headers=self.headers,
                timeout=10.0,
            )

            if response.status_code != 200:
                raise HTTPException(
                    status_code=502,
                    detail=f"Erro ao buscar time. Status: {response.status_code}",
                )

            data = response.json()
            return data.get("response", [])

    @_retry
    async def fetch_head_to_head(self, team_a_id: int, team_b_id: int) -> dict:

        if not team_a_id or not team_b_id:
            raise ValueError("Nomes das seleções são obrigatórios.")

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.api_url}/fixtures/headtohead?h2h={team_a_id}-{team_b_id}",
                headers=self.headers,
                timeout=10.0,
            )

            # Typed error handling
            if response.status_code != 200:
                raise HTTPException(
                    status_code=502,
                    detail=f"Erro na API externa de futebol. Status: {response.status_code}",
                )

            return response.json()
