from datetime import date
from typing import List, Optional

from fastapi import Query

from app.models.football_base import MatchStatus


class HeadToHeadRequest:
    def __init__(
        self,
        name_team_a: str = Query(
            ..., min_length=1, description="Nome do time A", examples=["Brazil"]
        ),
        name_team_b: str = Query(
            ..., min_length=1, description="Nome do time B", examples=["France"]
        ),
    ):
        self.name_team_a = name_team_a
        self.name_team_b = name_team_b


class MatchRequest:
    def __init__(
        self,
        teams: Optional[List[str]] = Query(
            None,
            description="Filtrar por um ou mais times (ex: `?teams=Brazil&teams=France`)",
            examples=["Brazil", "France"],
        ),
        date_from: Optional[date] = Query(
            None,
            description="Data de início (inclusive). Deve ser usado com `date_to`.",
            examples=["2026-06-14"],
        ),
        date_to: Optional[date] = Query(
            None,
            description="Data de fim (inclusive). Deve ser usado com `date_from`.",
            examples=["2026-06-21"],
        ),
        status: Optional[MatchStatus] = Query(
            None, description="Filtrar pelo status da partida"
        ),
    ):
        self.teams = teams
        self.date_from = date_from
        self.date_to = date_to
        self.status = status
