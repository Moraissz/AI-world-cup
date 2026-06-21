import httpx
from tenacity import retry, retry_if_not_exception_type, stop_after_attempt, wait_fixed
from fastapi import HTTPException

from app.utils.cache import cache

_retry = retry(
    stop=stop_after_attempt(3),
    wait=wait_fixed(1),
    retry=retry_if_not_exception_type((HTTPException, ValueError)),
    reraise=True,
)


class FootballApiClient:
    def __init__(self, api_key: str, redis_client=None):
        self.redis = redis_client
        self.api_url = "https://v3.football.api-sports.io"
        self.headers = {
            "x-rapidapi-key": api_key,
            "x-rapidapi-host": "v3.football-api-sports.io",
        }

    @cache(
        ttl=604800,  # 7 days — team IDs never change
        key_builder=lambda f, self, team_name: f"team_search:{team_name.lower()}",
    )
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

            if response.status_code == 429:
                raise HTTPException(
                    status_code=429,
                    detail="Limite de requisições atingido.",
                )
            if response.status_code != 200:
                raise HTTPException(
                    status_code=502,
                    detail=f"Erro ao buscar time. Status: {response.status_code}",
                )

            data = response.json()
            return data.get("response", [])

    @cache(
        ttl=86400,  # 24h — historical fixtures don't change during the tournament
        key_builder=lambda f, self, team_a_id, team_b_id: f"h2h:{min(team_a_id, team_b_id)}:{max(team_a_id, team_b_id)}",
    )
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

            if response.status_code == 429:
                raise HTTPException(
                    status_code=429,
                    detail="Limite de requisições atingido.",
                )
            if response.status_code != 200:
                raise HTTPException(
                    status_code=502,
                    detail=f"Erro na API externa de futebol. Status: {response.status_code}",
                )

            return response.json()
