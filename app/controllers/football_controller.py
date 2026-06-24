from fastapi import APIRouter, Depends
from dependency_injector.wiring import inject, Provide
from container import AppContainer
from app.exceptions import InvalidDateRangeError
from app.models.football_request import HeadToHeadRequest, MatchRequest
from app.models.football_response import (
    HeadToHeadResponse,
    MatchesResponse,
    StandingsResponse,
    TopScorersResponse,
)
from app.services.football_service import FootballService

football_router = APIRouter(prefix="/football", tags=["Football API"])


@football_router.get(
    "/head-to-head",
    response_model=HeadToHeadResponse,
    summary="Confronto histórico entre dois times",
    description="Retorna estatísticas históricas e confrontos recentes entre dois times nacionais.",
    responses={
        200: {
            "description": "Estatísticas retornadas com sucesso",
            "content": {
                "application/json": {
                    "example": {
                        "matchup": "Brazil vs France",
                        "total_matches": 29,
                        "historical_stats": {
                            "team_a_wins": 14,
                            "team_b_wins": 8,
                            "draws": 7,
                            "team_a_goals_scored": 36,
                            "team_b_goals_scored": 24,
                        },
                        "recent_encounters": [
                            {
                                "date": "2022-11-24",
                                "competition": "FIFA World Cup 2022",
                                "score": "2-0",
                            },
                            {
                                "date": "2019-06-02",
                                "competition": "International Friendly",
                                "score": "1-3",
                            },
                        ],
                    }
                }
            },
        },
        400: {"description": "Parâmetros ausentes ou inválidos"},
        500: {"description": "Erro interno do servidor"},
    },
)
@inject
async def check_head_to_head(
    params: HeadToHeadRequest = Depends(),
    service: FootballService = Depends(Provide[AppContainer.football_service]),
):
    return await service.generate_summary(params.name_team_a, params.name_team_b)


@football_router.get(
    "/world-cup/standings",
    response_model=StandingsResponse,
    summary="Classificação dos grupos da Copa do Mundo",
    description="Retorna a classificação atual de todos os grupos da fase de grupos da Copa do Mundo FIFA 2026.",
    responses={
        200: {
            "description": "Classificação retornada com sucesso",
            "content": {
                "application/json": {
                    "example": {
                        "groups": [
                            {
                                "group": "Group A",
                                "standings": [
                                    {
                                        "position": 1,
                                        "team": "Brazil",
                                        "played": 3,
                                        "won": 2,
                                        "draw": 1,
                                        "lost": 0,
                                        "goals_for": 5,
                                        "goals_against": 2,
                                        "goal_difference": 3,
                                        "points": 7,
                                    },
                                    {
                                        "position": 2,
                                        "team": "France",
                                        "played": 3,
                                        "won": 1,
                                        "draw": 1,
                                        "lost": 1,
                                        "goals_for": 3,
                                        "goals_against": 4,
                                        "goal_difference": -1,
                                        "points": 4,
                                    },
                                ],
                            }
                        ]
                    }
                }
            },
        },
        500: {"description": "Erro interno do servidor"},
    },
)
@inject
async def get_standings(
    service: FootballService = Depends(Provide[AppContainer.football_service]),
):
    return await service.get_standings()


@football_router.get(
    "/world-cup/matches",
    response_model=MatchesResponse,
    summary="Partidas da Copa do Mundo",
    description=(
        "Retorna uma lista de partidas da Copa do Mundo. "
        "Todos os parâmetros são opcionais e podem ser combinados para filtrar os resultados. "
        "Se `date_from` for informado, `date_to` também deve ser (e vice-versa)."
    ),
    responses={
        200: {
            "description": "Partidas retornadas com sucesso",
            "content": {
                "application/json": {
                    "example": {
                        "matches": [
                            {
                                "utc_date": "2026-06-14T18:00:00Z",
                                "home_team": "Brazil",
                                "away_team": "Germany",
                                "score": {"home": 2, "away": 1},
                                "status": "FINISHED",
                                "stage": "GROUP_STAGE",
                            },
                            {
                                "utc_date": "2026-06-18T21:00:00Z",
                                "home_team": "Argentina",
                                "away_team": "France",
                                "score": {"home": None, "away": None},
                                "status": "SCHEDULED",
                                "stage": "GROUP_STAGE",
                            },
                        ]
                    }
                }
            },
        },
        400: {"description": "date_from e date_to devem ser informados juntos"},
        500: {"description": "Erro interno do servidor"},
    },
)
@inject
async def get_matches(
    params: MatchRequest = Depends(),
    service: FootballService = Depends(Provide[AppContainer.football_service]),
):
    if (params.date_from is None) != (params.date_to is None):
        raise InvalidDateRangeError()
    return await service.get_matches(
        teams=params.teams,
        date_from=params.date_from,
        date_to=params.date_to,
        status=params.status,
    )


@football_router.get(
    "/world-cup/top-scorers",
    response_model=TopScorersResponse,
    summary="Artilheiros da Copa do Mundo",
    description="Retorna o ranking atualizado de artilheiros da Copa do Mundo FIFA 2026.",
    responses={
        200: {
            "description": "Artilheiros retornados com sucesso",
            "content": {
                "application/json": {
                    "example": {
                        "scorers": [
                            {
                                "position": 1,
                                "player": "Kylian Mbappé",
                                "team": "France",
                                "goals": 6,
                                "assists": 3,
                            },
                            {
                                "position": 2,
                                "player": "Erling Haaland",
                                "team": "Norway",
                                "goals": 5,
                                "assists": 1,
                            },
                        ]
                    }
                }
            },
        },
        500: {"description": "Erro interno do servidor"},
    },
)
@inject
async def get_top_scorers(
    service: FootballService = Depends(Provide[AppContainer.football_service]),
):
    return await service.get_top_scorers()
