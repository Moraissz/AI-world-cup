from dependency_injector import containers, providers
from app.integrations.football_api_client import FootballApiClient
from app.services.head_to_head_analyzer import HeadToHeadAnalyzer
import os


class AppContainer(containers.DeclarativeContainer):

    wiring_config = containers.WiringConfiguration(
        modules=[
            "app.controllers.football_controller",
        ]
    )

    api_key = os.getenv("FOOTBALL_API_KEY", "API_KEY")

    football_api_client = providers.Singleton(FootballApiClient, api_key=api_key)

    head_to_head_analyzer = providers.Factory(
        HeadToHeadAnalyzer, api_client=football_api_client
    )
