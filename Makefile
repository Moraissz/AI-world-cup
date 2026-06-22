# AI World Cup — reproducible, idempotent setup.
# Each target can be run multiple times without creating duplicates or conflicts.
.PHONY: install start stop restart status register agent-spawn clean sync-agent reload-agent \
        test format lint all start-redis start-omni start-genie start-api wire

GENIE := $(HOME)/.local/bin/genie
OMNI  := $(HOME)/.bun/bin/omni
VENV  := .venv

# ---------------------------------------------------------------------------
# Setup
# ---------------------------------------------------------------------------
install:               ## install deps, venv, .env, submodules (idempotent)
	@bash scripts/setup.sh

# ---------------------------------------------------------------------------
# Lifecycle
# ---------------------------------------------------------------------------
start: start-redis start-omni start-genie start-api wire status  ## bring everything up + wire the agent

stop:                  ## stop every service + kill agent sessions
	@bash scripts/stop.sh

restart: stop start    ## stop then start

status:                ## health snapshot (flags accumulation)
	@bash scripts/status.sh

clean:                 ## purge stale Omni agent records + orphan sessions (destructive)
	@bash scripts/clean.sh

# ---------------------------------------------------------------------------
# Service sub-targets (each idempotent: checks before acting)
# ---------------------------------------------------------------------------
start-redis:
	@docker compose up redis -d --remove-orphans >/dev/null 2>&1 \
	  && echo "  [ok] Redis up" || echo "  [warn] Redis: verifique o Docker"

start-omni:
	@$(OMNI) status --json 2>/dev/null | grep -q '"apiStatus": *"healthy"' \
	  && echo "  [ok] Omni já saudável" \
	  || $(OMNI) start

start-genie:
	@bash scripts/start-genie.sh

start-api:
	@curl -sf -o /dev/null http://localhost:8000/docs \
	  && echo "  [ok] FastAPI já rodando" \
	  || ( nohup $(VENV)/bin/uvicorn main:app --host 0.0.0.0 --port 8000 \
	         >/tmp/world-cup-api.log 2>&1 & echo "  [ok] FastAPI iniciado (log: /tmp/world-cup-api.log)" )

# ---------------------------------------------------------------------------
# Agent wiring
# ---------------------------------------------------------------------------
wire register:         ## idempotent Genie<->Omni connection
	@bash scripts/register-agent.sh

agent-spawn:           ## open a manual debug session (not needed for WhatsApp)
	@bash scripts/register-agent.sh --spawn-only

sync-agent:            ## sync agents/ -> genie (config + prompt p/ conversas NOVAS)
	@GENIE_NO_V1_PROMPT=1 $(GENIE) dir sync
	@echo "  [ok] sincronizado. Conversa NOVA ja usa. P/ chat JA ativo: make reload-agent"

reload-agent:          ## aplica instrucoes editadas a TODOS os chats (reset de sessao)
	@bash scripts/reload-agent.sh

# ---------------------------------------------------------------------------
# Dev
# ---------------------------------------------------------------------------
test:
	@$(VENV)/bin/pytest -v tests/

format:
	@$(VENV)/bin/black .

lint:
	@$(VENV)/bin/black --check .

all: format lint
