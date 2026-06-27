import os

import redis.asyncio as aioredis
from dependency_injector import containers, providers

from app.integrations.football_api_client import FootballApiClient
from app.integrations.football_data_client import FootballDataClient
from app.services.football_service import FootballService
from app.services.memory_service import MemoryService


async def _create_redis(host: str, port: int, password: str):
    # Redis is optional: when REDIS_HOST is unset, no client is created and
    # None is injected. Downstream (cache, memory_service) degrade gracefully.
    if not host:
        yield None
        return
    client = aioredis.Redis(
        host=host,
        port=port,
        password=password or None,
        decode_responses=True,
    )
    try:
        yield client
    finally:
        await client.aclose()


class AppContainer(containers.DeclarativeContainer):

    wiring_config = containers.WiringConfiguration(
        modules=[
            "app.controllers.football_controller",
            "app.controllers.memory_controller",
        ]
    )

    redis_client = providers.Resource(
        _create_redis,
        host=os.getenv("REDIS_HOST"),
        port=int(os.getenv("REDIS_PORT", 6379)),
        password=os.getenv("REDIS_PASSWORD", ""),
    )

    football_io_sports_client = providers.Singleton(
        FootballApiClient,
        api_key=os.getenv("FOOTBALL_IO_SPORTS_API_KEY", ""),
        redis_client=redis_client,
    )
    football_data_org_client = providers.Singleton(
        FootballDataClient,
        api_key=os.getenv("FOOTBALL_DATA_ORG_API_KEY", ""),
        redis_client=redis_client,
    )

    memory_service = providers.Singleton(
        MemoryService,
        redis_client=redis_client,
    )

    football_service = providers.Factory(
        FootballService,
        football_io_sports_client=football_io_sports_client,
        football_data_org_client=football_data_org_client,
    )
