from typing import List

from pydantic import BaseModel, ConfigDict, Field

from app.models.football_base import (
    GroupStanding,
    HistoricalStats,
    Match,
    RecentEncounter,
    TopScorer,
)


class HeadToHeadResponse(BaseModel):
    matchup: str = Field(
        ...,
        examples=["Brazil vs France"],
        description="Rótulo do confronto entre os times",
    )
    total_matches: int = Field(
        ..., examples=[29], description="Total de partidas históricas entre os times"
    )
    historical_stats: HistoricalStats
    recent_encounters: List[RecentEncounter]

    model_config = ConfigDict(
        json_schema_extra={
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
    )


class StandingsResponse(BaseModel):
    groups: List[GroupStanding]

    model_config = ConfigDict(
        json_schema_extra={
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
    )


class MatchesResponse(BaseModel):
    matches: List[Match]

    model_config = ConfigDict(
        json_schema_extra={
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
    )


class TopScorersResponse(BaseModel):
    scorers: List[TopScorer]

    model_config = ConfigDict(
        json_schema_extra={
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
    )
