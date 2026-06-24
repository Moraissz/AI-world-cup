import time
from datetime import date

import httpx
import structlog
from tenacity import retry, retry_if_not_exception_type, stop_after_attempt, wait_fixed
from fastapi import HTTPException

from app.models.football_base import MatchStatus
from app.utils.cache import cache

logger = structlog.get_logger(__name__)


def _log_retry_fdo(retry_state):
    logger.warning(
        "http.retry",
        provider="football-data.org",
        attempt=retry_state.attempt_number,
    )


_retry = retry(
    stop=stop_after_attempt(3),
    wait=wait_fixed(1),
    retry=retry_if_not_exception_type(HTTPException),
    reraise=True,
    before_sleep=_log_retry_fdo,
)


def _matches_key(f, self, date_from=None, date_to=None, status=None):
    status_val = status.value if hasattr(status, "value") else status
    return f"matches:{date_from}:{date_to}:{status_val}"


def _matches_ttl(status=None) -> int:
    # Live matches get a 60s TTL; everything else 5 minutes
    if status in (MatchStatus.IN_PLAY, MatchStatus.PAUSED, "IN_PLAY", "PAUSED"):
        return 60
    return 300


class FootballDataClient:
    def __init__(self, api_key: str, redis_client=None):
        self.redis = redis_client
        self.base_url = "https://api.football-data.org/v4"
        self.headers = {"X-Auth-Token": api_key}

    def _handle_error(self, status_code: int) -> None:
        if status_code == 429:
            raise HTTPException(
                status_code=429,
                detail="Limite de requisições atingido na API de futebol.",
            )
        if status_code >= 500:
            raise HTTPException(
                status_code=502,
                detail=f"Erro na API football-data.org. Status: {status_code}",
            )
        if status_code in (401, 403):
            logger.error(
                "http.auth_error",
                provider="football-data.org",
                upstream_status=status_code,
                detail="invalid API key or plan insufficient",
            )
        if status_code != 200:
            raise HTTPException(
                status_code=502,
                detail=f"Erro na API football-data.org. Status: {status_code}",
            )

    @cache(
        ttl=300,  # 5 min — standings update after each match
        key_builder=lambda f, self: "standings",
    )
    @_retry
    async def fetch_standings(self) -> dict:
        url = f"{self.base_url}/competitions/WC/standings"
        logger.debug("http.request", provider="football-data.org", url=url)
        t0 = time.perf_counter()

        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=self.headers, timeout=10.0)

        latency_ms = round((time.perf_counter() - t0) * 1000, 1)

        if response.status_code != 200:
            logger.error("http.error", provider="football-data.org", upstream_status=response.status_code, latency_ms=latency_ms)
        else:
            logger.info("http.response", provider="football-data.org", upstream_status=response.status_code, latency_ms=latency_ms)

        self._handle_error(response.status_code)
        return response.json()

    @cache(
        ttl=300,  # 5 min default; live matches handled by _matches_ttl
        key_builder=_matches_key,
    )
    @_retry
    async def fetch_matches(
        self, date_from: date = None, date_to: date = None, status: MatchStatus = None
    ) -> dict:
        params = {}
        if date_from and date_to:
            params["dateFrom"] = date_from.isoformat()
            params["dateTo"] = date_to.isoformat()
        if status:
            params["status"] = status.value if hasattr(status, "value") else status

        url = f"{self.base_url}/competitions/WC/matches"
        logger.debug("http.request", provider="football-data.org", url=url, params=params)
        t0 = time.perf_counter()

        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=self.headers, params=params, timeout=10.0)

        latency_ms = round((time.perf_counter() - t0) * 1000, 1)

        if response.status_code != 200:
            logger.error("http.error", provider="football-data.org", upstream_status=response.status_code, latency_ms=latency_ms)
        else:
            logger.info("http.response", provider="football-data.org", upstream_status=response.status_code, latency_ms=latency_ms)

        self._handle_error(response.status_code)
        return response.json()

    @cache(
        ttl=600,  # 10 min — scorers update after goals
        key_builder=lambda f, self: "top_scorers",
    )
    @_retry
    async def fetch_top_scorers(self) -> dict:
        url = f"{self.base_url}/competitions/WC/scorers"
        logger.debug("http.request", provider="football-data.org", url=url)
        t0 = time.perf_counter()

        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=self.headers, timeout=10.0)

        latency_ms = round((time.perf_counter() - t0) * 1000, 1)

        if response.status_code != 200:
            logger.error("http.error", provider="football-data.org", upstream_status=response.status_code, latency_ms=latency_ms)
        else:
            logger.info("http.response", provider="football-data.org", upstream_status=response.status_code, latency_ms=latency_ms)

        self._handle_error(response.status_code)
        return response.json()
