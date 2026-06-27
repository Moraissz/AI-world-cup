from datetime import date
from enum import Enum
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class MatchStatus(str, Enum):
    SCHEDULED = "SCHEDULED"
    TIMED = "TIMED"
    IN_PLAY = "IN_PLAY"
    PAUSED = "PAUSED"
    FINISHED = "FINISHED"
    SUSPENDED = "SUSPENDED"
    POSTPONED = "POSTPONED"
    CANCELLED = "CANCELLED"
    AWARDED = "AWARDED"


class HistoricalStats(BaseModel):
    team_a_wins: int = Field(
        ..., examples=[14], description="Vitórias do time A no histórico"
    )
    team_b_wins: int = Field(
        ..., examples=[8], description="Vitórias do time B no histórico"
    )
    draws: int = Field(..., examples=[7], description="Número de empates")
    team_a_goals_scored: int = Field(
        ..., examples=[36], description="Total de gols marcados pelo time A"
    )
    team_b_goals_scored: int = Field(
        ..., examples=[24], description="Total de gols marcados pelo time B"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "team_a_wins": 14,
                "team_b_wins": 8,
                "draws": 7,
                "team_a_goals_scored": 36,
                "team_b_goals_scored": 24,
            }
        }
    )


class RecentEncounter(BaseModel):
    date: Optional[str] = Field(
        None, examples=["2022-11-24"], description="Data da partida (ISO 8601)"
    )
    competition: str = Field(
        ..., examples=["FIFA World Cup 2022"], description="Nome da competição"
    )
    score: str = Field(
        ...,
        examples=["France 1 - 0 Brazil"],
        description="Placar com nomes: 'Casa G - G Visitante'",
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "date": "2022-11-24",
                "competition": "FIFA World Cup 2022",
                "score": "2-0",
            }
        }
    )


class TeamStanding(BaseModel):
    position: int = Field(..., examples=[1], description="Posição no grupo")
    team: str = Field(..., examples=["Brazil"], description="Nome do time")
    played: int = Field(..., examples=[3], description="Partidas disputadas")
    won: int = Field(..., examples=[2], description="Partidas vencidas")
    draw: int = Field(..., examples=[1], description="Partidas empatadas")
    lost: int = Field(..., examples=[0], description="Partidas perdidas")
    goals_for: int = Field(..., examples=[5], description="Gols marcados")
    goals_against: int = Field(..., examples=[2], description="Gols sofridos")
    goal_difference: int = Field(..., examples=[3], description="Saldo de gols")
    points: int = Field(..., examples=[7], description="Pontos acumulados")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
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
            }
        }
    )


class GroupStanding(BaseModel):
    group: str = Field(..., examples=["Group A"], description="Identificador do grupo")
    standings: list[TeamStanding]

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
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
                    }
                ],
            }
        }
    )


class MatchScore(BaseModel):
    home: Optional[int] = Field(
        None, examples=[2], description="Gols do time da casa (null se não iniciado)"
    )
    away: Optional[int] = Field(
        None, examples=[1], description="Gols do time visitante (null se não iniciado)"
    )

    model_config = ConfigDict(json_schema_extra={"example": {"home": 2, "away": 1}})


class Match(BaseModel):
    utc_date: str = Field(
        ...,
        examples=["2026-06-14T18:00:00Z"],
        description="Data e hora da partida em UTC (ISO 8601)",
    )
    home_team: str = Field(..., examples=["Brazil"], description="Nome do time da casa")
    away_team: str = Field(
        ..., examples=["Germany"], description="Nome do time visitante"
    )
    score: MatchScore
    status: MatchStatus = Field(
        ..., examples=["FINISHED"], description="Status atual da partida"
    )
    stage: str = Field(..., examples=["GROUP_STAGE"], description="Fase do torneio")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "utc_date": "2026-06-14T18:00:00Z",
                "home_team": "Brazil",
                "away_team": "Germany",
                "score": {"home": 2, "away": 1},
                "status": "FINISHED",
                "stage": "GROUP_STAGE",
            }
        }
    )


class TopScorer(BaseModel):
    position: int = Field(
        ..., examples=[1], description="Posição no ranking de artilheiros"
    )
    player: str = Field(
        ..., examples=["Kylian Mbappé"], description="Nome completo do jogador"
    )
    team: str = Field(..., examples=["France"], description="Time do jogador")
    goals: int = Field(..., examples=[6], description="Número de gols marcados")
    assists: int = Field(..., examples=[3], description="Número de assistências")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "position": 1,
                "player": "Kylian Mbappé",
                "team": "France",
                "goals": 6,
                "assists": 3,
            }
        }
    )
