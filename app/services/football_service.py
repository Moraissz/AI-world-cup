from datetime import date
from typing import List, Optional

from app.integrations.football_api_client import FootballApiClient
from app.integrations.football_data_client import FootballDataClient
from app.models.football_base import (
    GroupStanding,
    Match,
    MatchScore,
    TeamStanding,
    TopScorer, MatchStatus,
)
from app.models.football_response import (
    MatchesResponse,
    StandingsResponse,
    TopScorersResponse,
)


class FootballService:

    def __init__(
        self,
        football_io_sports_client: FootballApiClient,
        football_data_org_client: FootballDataClient,
    ):
        self.football_io_sports_client = football_io_sports_client
        self.football_data_org_client = football_data_org_client

    async def _get_team_id(self, team_name: str) -> int:

        results = await self.football_io_sports_client.search_team_id(team_name)

        if not results:
            raise ValueError(f"Seleção '{team_name}' não encontrada")

        team_id = None
        for result in results:
            team = result.get("team", {})
            if team.get("national") is True:
                team_id: int = team.get("id")
                break

        if not team_id:
            raise ValueError(f"Seleção '{team_name}' não encontrada")

        return team_id

    async def generate_summary(self, team_a: str, team_b: str) -> dict:
        if not team_a or not team_b:
            return {}

        team_a_id = await self._get_team_id(team_a)
        team_b_id = await self._get_team_id(team_b)

        raw_data = await self.football_io_sports_client.fetch_head_to_head(
            team_a_id, team_b_id
        )
        matches = raw_data.get("response", [])

        if not matches:
            return self._create_empty_summary(team_a, team_b)

        return self._process_match_data(matches, team_a, team_b, team_a_id, team_b_id)

    def _create_empty_summary(self, team_a: str, team_b: str) -> dict:
        return {
            "matchup": f"{team_a} vs {team_b}",
            "total_matches": 0,
            "historical_stats": {
                "team_a_wins": 0,
                "team_b_wins": 0,
                "draws": 0,
                "team_a_goals_scored": 0,
                "team_b_goals_scored": 0,
            },
            "recent_encounters": [],
        }

    def _process_match_data(
        self, matches: list, team_a: str, team_b: str, team_a_id: int, team_b_id: int
    ) -> dict:
        team_a_wins = 0
        team_b_wins = 0
        draws = 0
        team_a_goals_scored = 0
        team_b_goals_scored = 0
        recent_encounters = []

        team_a_lower = team_a.lower()
        team_b_lower = team_b.lower()

        for match in matches:
            fixture = match.get("fixture", {})
            result = match.get("score", {})
            home = match.get("teams", {}).get("home", {})
            away = match.get("teams", {}).get("away", {})
            league = match.get("league", {})

            home_name = home.get("name", "").lower()
            match_date = fixture.get("date")
            home_goals = result.get("fulltime", {}).get("home")
            away_goals = result.get("fulltime", {}).get("away")

            if home_goals is None or away_goals is None:
                continue

            is_a_home = home_name == team_a_lower or home.get("id") == team_a_id
            is_b_home = home_name == team_b_lower or home.get("id") == team_b_id

            if is_a_home:
                team_a_goals_scored += home_goals
                team_b_goals_scored += away_goals
            else:
                team_a_goals_scored += away_goals
                team_b_goals_scored += home_goals

            if home_goals == away_goals:
                draws += 1
            elif home_goals > away_goals:
                if is_a_home:
                    team_a_wins += 1
                elif is_b_home:
                    team_b_wins += 1
            else:
                if not is_a_home and not is_b_home:

                    pass

                if not is_a_home:
                    team_a_wins += 1
                elif not is_b_home:
                    team_b_wins += 1

            recent_encounters.append(
                {
                    "date": self._format_date(match_date),
                    "competition": league.get("name", "Unknown"),
                    "score": f"{home.get('name', 'Unknown')} {home_goals} - {away_goals} {away.get('name', 'Unknown')}",
                }
            )

        recent_encounters.sort(key=lambda item: item["date"], reverse=True)

        return {
            "matchup": f"{team_a} vs {team_b}",
            "total_matches": len(matches),
            "historical_stats": {
                "team_a_wins": team_a_wins,
                "team_b_wins": team_b_wins,
                "draws": draws,
                "team_a_goals_scored": team_a_goals_scored,
                "team_b_goals_scored": team_b_goals_scored,
            },
            "recent_encounters": recent_encounters,
        }

    def _format_date(self, date_string: str) -> str:
        if not date_string:
            return ""
        return date_string.split("T")[0]

    async def get_standings(self) -> StandingsResponse:
        data = await self.football_data_org_client.fetch_standings()
        groups = []
        for entry in data.get("standings", []):
            if entry.get("type") != "TOTAL":
                continue
            group_name = entry.get("group", "")
            team_standings = [
                TeamStanding(
                    position=row["position"],
                    team=row["team"]["name"],
                    played=row["playedGames"],
                    won=row["won"],
                    draw=row["draw"],
                    lost=row["lost"],
                    goals_for=row["goalsFor"],
                    goals_against=row["goalsAgainst"],
                    goal_difference=row["goalDifference"],
                    points=row["points"],
                )
                for row in entry.get("table", [])
            ]
            groups.append(GroupStanding(group=group_name, standings=team_standings))
        return StandingsResponse(groups=groups)

    async def get_matches(
        self,
        teams: Optional[List[str]] = None,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
        status: Optional[MatchStatus] = None,
    ) -> MatchesResponse:

        data = await self.football_data_org_client.fetch_matches(
            date_from=date_from, date_to=date_to, status=status
        )
        matches = []
        for m in data.get("matches", []):
            home_name = m.get("homeTeam", {}).get("name") or ""
            away_name = m.get("awayTeam", {}).get("name") or ""

            if teams and not any(
                t.lower() in (home_name.lower(), away_name.lower()) for t in teams
            ):
                continue

            score_data = m.get("score", {}).get("fullTime", {})
            matches.append(
                Match(
                    utc_date=m.get("utcDate", ""),
                    home_team=home_name,
                    away_team=away_name,
                    score=MatchScore(
                        home=score_data.get("home"), away=score_data.get("away")
                    ),
                    status=m.get("status", ""),
                    stage=m.get("stage", ""),
                )
            )

        return MatchesResponse(matches=matches)

    async def get_top_scorers(self) -> TopScorersResponse:
        data = await self.football_data_org_client.fetch_top_scorers()
        scorers = [
            TopScorer(
                position=i + 1,
                player=entry.get("player", {}).get("name", ""),
                team=entry.get("team", {}).get("name", ""),
                goals=entry.get("goals", 0) or 0,
                assists=entry.get("assists", 0) or 0,
            )
            for i, entry in enumerate(data.get("scorers", []))
        ]
        return TopScorersResponse(scorers=scorers)
