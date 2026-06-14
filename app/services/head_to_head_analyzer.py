from app.integrations.football_api_client import FootballApiClient


class HeadToHeadAnalyzer:

    def __init__(self, api_client: FootballApiClient):
        self.api_client = api_client

    async def _get_team_id(self, team_name: str) -> int:

        results = await self.api_client.search_team_id(team_name)

        if not results:
            raise ValueError(f"Seleção '{team_name}' não encontrada")

        team_id = None
        for result in results:
            team = result.get("team", {})
            if team.get("national") is True:
                team_id = team.get("id")
                break

        if not team_id:
            raise ValueError(f"Seleção '{team_name}' não encontrada")

        return team_id

    async def generate_summary(self, team_a: str, team_b: str) -> dict:
        if not team_a or not team_b:
            return {}

        team_a_id = await self._get_team_id(team_a)
        team_b_id = await self._get_team_id(team_b)

        raw_data = await self.api_client.fetch_head_to_head(team_a_id, team_b_id)
        matches = raw_data.get("response", [])

        if not matches:
            return self._create_empty_summary(team_a, team_b)

        return self._process_match_data(matches, team_a, team_b)

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

    def _process_match_data(self, matches: list, team_a: str, team_b: str) -> dict:
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

            is_a_home = home_name == team_a_lower or (
                home.get("id") == self._get_team_id(team_a)
            )
            is_b_home = home_name == team_b_lower or (
                home.get("id") == self._get_team_id(team_b)
            )

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
