# AI World Cup — Project Context

## What this is

A FastAPI backend + genie agent system that answers football match prediction questions via WhatsApp during the 2026 FIFA World Cup.

The stack:
- **FastAPI** (`main.py`) — REST API exposing head-to-head historical stats
- **Football Stats API** (`app/integrations/football_api_client.py`) — external data source (api-sports.io)
- **world-cup-specialist** (`agents/world-cup-specialist/`) — genie agent that uses the API to answer user messages
- **Omni bridge** — routes WhatsApp messages to the agent and back

## Running locally

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # set FOOTBALL_IO_SPORTS_API_KEY and OMNI_API_KEY
make start            # starts Omni (postgres + NATS), genie serve (autopg), and FastAPI
```

API docs at `http://localhost:8000/docs`.

## Key endpoints

- `GET /football/head-to-head?name_team_a=Brazil&name_team_b=France`

## Tests

```bash
python -m pytest -q tests/
```

## Genie agent

The `world-cup-specialist` agent is managed by genie.

Register (first time only — use `/genie:omni` skill or manually):

```bash
genie omni handshake
genie agent register world-cup-specialist --dir agents/world-cup-specialist
omni instances list                  # get <instance-id>
omni connect <instance-id> world-cup-specialist --mode turn-based --reply-filter all
```

Spawn the agent:

```bash
make agent-spawn
# or: genie spawn world-cup-specialist
```

Check status:

```bash
genie ls
omni agents list
```

## Environment variables

| Variable | Description |
|---|---|
| `FOOTBALL_IO_SPORTS_API_KEY` | API key for api-sports.io |
| `OMNI_API_URL` | Omni API base URL (default: `http://localhost:8882`) |
| `OMNI_API_KEY` | Omni API authentication key |

## Architecture notes

- `FootballService` (`app/services/football_service.py`) is the central service layer. It owns:
  - `generate_summary(team_a, team_b)` — resolves team names to IDs via `FootballApiClient` (api-sports.io), then fetches head-to-head fixture history.
  - `get_standings()`, `get_matches()`, `get_top_scorers()` — delegate to `FootballDataClient` (football-data.org), the primary source for live Copa 2026 data.
- `FootballApiClient` (`app/integrations/football_api_client.py`) — wraps api-sports.io; used only for team-ID lookup and h2h fixtures.
- `FootballDataClient` (`app/integrations/football_data_client.py`) — wraps football-data.org `/v4/competitions/WC/*`; used for standings, match schedule/results, and top scorers.
- `memory_controller.py` exposes `GET/POST /memory/{chat_id}` backed by Redis (TTL 7 days). The agent loads memory at turn start and saves after composing a response.
- The agent's HEARTBEAT loop processes inbox messages: identify teams → call API → predict → respond.
- Responses must be plain text (no markdown) — WhatsApp renders `*` and `#` literally.
- `.claude/agents/world-cup-specialist.md` is a symlink → `agents/world-cup-specialist/AGENTS.md`. Required for `claude --agent world-cup-specialist` to resolve (claude ≥ 2.1.191 validates `--agent` against `.claude/agents/`; it no longer auto-materialises genie team leaders from `--team-name/--agent-id`). Do not delete — the WhatsApp agent goes silent without it.
