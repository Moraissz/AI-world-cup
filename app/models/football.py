from typing import List, Optional
from pydantic import BaseModel


class HistoricalStats(BaseModel):
    team_a_wins: int
    team_b_wins: int
    draws: int
    team_a_goals_scored: int
    team_b_goals_scored: int


class RecentEncounter(BaseModel):
    date: Optional[str] = None
    competition: str
    score: str


class HeadToHeadResponse(BaseModel):
    matchup: str
    total_matches: int
    historical_stats: HistoricalStats
    recent_encounters: List[RecentEncounter]
