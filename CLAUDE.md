# AI World Cup — Project Context

## What this is

A FastAPI backend + genie agent system that answers football match prediction questions via WhatsApp during the 2026 FIFA World Cup.

The stack:
- **FastAPI** (`main.py`) — REST API exposing head-to-head stats and predictions
- **Football Stats API** (`app/integrations/football_api_client.py`) — external data source (api-sports.io)
- **world-cup-specialist** (`agents/world-cup-specialist/`) — genie agent that uses the API to answer user messages
- **Omni bridge** — routes WhatsApp messages to the agent and back

## Running locally

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # set FOOTBALL_API_KEY
uvicorn main:app --reload
```

API docs at `http://localhost:8000/docs`.

## Key endpoints

- `GET /football/head-to-head?name_team_a=Brazil&name_team_b=France`
- `POST /football/predict` — `{"team_a": "Brazil", "team_b": "France"}`

## Tests

```bash
python -m pytest -q tests/
```

## Genie agent

The `world-cup-specialist` agent is managed by genie. To start it:

```bash
genie spawn world-cup-specialist
```

To check status:

```bash
genie ls
```

## Environment variables

| Variable | Description |
|---|---|
| `FOOTBALL_API_KEY` | API key for api-sports.io |

## Architecture notes

- `HeadToHeadAnalyzer` resolves team names to IDs via search, then fetches fixture history.
- The agent's HEARTBEAT loop processes inbox messages: identify teams → call API → predict → respond.
- Responses must be plain text (no markdown) — WhatsApp renders `*` and `#` literally.
