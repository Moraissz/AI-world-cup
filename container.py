from dependency_injector import containers, providers
from app.integrations.football_api_client import FootballApiClient
from app.integrations.football_data_client import FootballDataClient
from app.services.football_service import FootballService
import os


class AppContainer(containers.DeclarativeContainer):

    wiring_config = containers.WiringConfiguration(
        modules=[
            "app.controllers.football_controller",
        ]
    )

    football_io_sports_api_key = os.getenv("FOOTBALL_IO_SPORTS_API_KEY", "API_KEY")
    football_data_org_api_key = os.getenv("FOOTBALL_DATA_ORG_API_KEY", "")

    football_io_sports_client = providers.Singleton(
        FootballApiClient, api_key=football_io_sports_api_key
    )
    football_data_org_client = providers.Singleton(
        FootballDataClient, api_key=football_data_org_api_key
    )

    football_service = providers.Factory(
        FootballService,
        football_io_sports_client=football_io_sports_client,
        football_data_org_client=football_data_org_client,
    )
