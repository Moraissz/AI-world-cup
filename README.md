# AI World Cup — Football Prediction Agent

WhatsApp agent that answers match prediction questions for the 2026 FIFA World Cup.
Receives messages via Omni, processes with Claude via Genie, responds with data-backed predictions.

## Architecture

```
WhatsApp → Omni (bridge) → NATS (4222) → Genie agent (world-cup-specialist)
                                                   ↓
                                    FastAPI (8000) /football/head-to-head
                                                   ↓
                                    omni done "prediction" → WhatsApp
```

### Stack

| Layer | Component | Purpose |
|---|---|---|
| Channel | Omni + Baileys | WhatsApp bridge, NATS routing |
| Orchestration | Genie v4 | Agent lifecycle, inbox, turn management |
| AI | Claude (Sonnet) | NLU, prediction generation |
| Data | FastAPI + api-sports.io | Head-to-head historical stats |

### Key architectural decisions

**1. curl-to-FastAPI instead of direct Python import**
The agent is a Claude Code process with bash tool access. It calls
`curl http://localhost:8000/football/head-to-head?...` to fetch data. This keeps the
agent and the data API independently restartable with a clean HTTP contract.

**2. No NATS subscriber in the FastAPI app**
An earlier approach proposed an `omni_client.py` with a NATS subscriber inside the
FastAPI process. This was rejected: Omni + Genie already handle message routing via
NATS natively. Adding a subscriber in the API would create two competing consumers
and couple the data layer to the agent transport layer.

**3. Turn-based mode for Omni connect**
Each WhatsApp message is one Omni turn. The agent reads context via `genie agent brief`,
processes it, and closes the turn with `omni done "text"`. This is the correct model
for Q&A: one message in, one message out, no polling.

**4. Plain text responses only**
WhatsApp renders `*`, `**`, and `#` as literal characters. All agent responses are
plain text with no markdown — enforced in SOUL.md and HEARTBEAT.md.

**5. agent.yaml cwd binding**
Setting `cwd` in `agent.yaml` ensures every spawn (manual or Omni-triggered) runs with
the project root as working directory, so `curl localhost:8000` is always reachable.

## Setup

### Prerequisites

- Python 3.10+
- Genie CLI v4: `~/.local/bin/genie`
- Omni CLI v2: `~/.bun/bin/omni`
- Football API key from [api-sports.io](https://api-sports.io)

### Quick start (recommended)

```bash
bash setup.sh   # checks all dependencies, creates venv, installs deps, creates .env
```

Then fill in `.env` (FOOTBALL_API_KEY, OMNI_API_KEY) and follow the printed next steps.

### Manual setup

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # fill in FOOTBALL_API_KEY and OMNI_API_KEY
```

### FastAPI via Docker (no Python setup needed)

```bash
cp .env.example .env   # fill in keys
docker-compose up
```

### 3. Start services

```bash
make start
# Starts Omni (postgres + NATS + API) and FastAPI
```

Verify:

```bash
omni status          # apiStatus: reachable
curl http://localhost:8000/docs
```

### 4. Register the agent (first time only)

Use the genie:omni skill (in Claude Code: `/genie:omni`), or manually:

```bash
genie omni handshake
genie agent register world-cup-specialist --dir agents/world-cup-specialist
omni instances list                    # note the <instance-id>
omni connect <instance-id> world-cup-specialist --mode turn-based --reply-filter all
```

### 5. Spawn the agent

```bash
make agent-spawn
# or: genie spawn world-cup-specialist
```

### 6. Connect WhatsApp

Scan the QR code for the Omni WhatsApp instance if not yet authenticated:

```bash
omni instances list    # check if instance is ACTIVE
```

## API Reference

### `GET /football/head-to-head`

Query: `?name_team_a=Brazil&name_team_b=France`

Response:

```json
{
  "matchup": "Brazil vs France",
  "total_matches": 14,
  "historical_stats": {
    "team_a_wins": 6,
    "team_b_wins": 4,
    "draws": 4,
    "team_a_goals_scored": 18,
    "team_b_goals_scored": 14
  },
  "recent_encounters": [
    {"date": "2022-12-10", "competition": "FIFA World Cup", "score": "France 1 - 0 Brazil"}
  ]
}
```

## Tests

```bash
make test
# or: python -m pytest -v tests/
```

23 tests covering the service layer (unit) and HTTP endpoints (integration), all mocked — no real API calls.

## Agent files

| File | Purpose |
|---|---|
| `agents/world-cup-specialist/SOUL.md` | Persona, principles, tool usage |
| `agents/world-cup-specialist/HEARTBEAT.md` | Autonomous turn loop (executable) |
| `agents/world-cup-specialist/AGENTS.md` | Mission and constraints |
| `agents/world-cup-specialist/agent.yaml` | Genie config (cwd, model, promptMode) |

## Stopping services

```bash
make stop
```

## Deployment

See [DEPLOY.md](DEPLOY.md) for full deployment options: single VPS, split cloud+local, and local+ngrok for quick demos.
