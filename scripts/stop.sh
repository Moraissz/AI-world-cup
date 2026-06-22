#!/usr/bin/env bash
# Stop the whole stack cleanly. Idempotent: safe to run when already stopped.
set -uo pipefail
. "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/common.sh"

log "=== Parando AI World Cup ==="

# Genie agent sessions (master + per-chat) under the genie tmux server.
for s in $(genie_sessions); do
  tmux -L genie kill-session -t "$s" 2>/dev/null && ok "sessão genie '${s}' encerrada" || true
done
# Manual debug launcher + legacy session names on the default tmux server.
for s in "wc-${AGENT_NAME}" "world-cup" "world-cup-agent"; do
  tmux has-session -t "$s" 2>/dev/null && { tmux kill-session -t "$s" 2>/dev/null && ok "sessão '${s}' encerrada"; } || true
done

# FastAPI
pkill -f "uvicorn main:app" 2>/dev/null && ok "FastAPI parado" || true

# Genie serve (bridge)
"$GENIE" serve stop >/dev/null 2>&1 && ok "genie serve parado" || true

# Postgres do genie (subido via pg_ctl) — serve stop nem sempre o derruba
if [ -n "$PG_CTL" ] && [ -x "$PG_CTL" ] && [ -d "$PG_DATA" ]; then
  "$PG_CTL" -D "$PG_DATA" -m fast stop >/dev/null 2>&1 && ok "pgserve parado" || true
fi

# Omni
"$OMNI" stop >/dev/null 2>&1 && ok "Omni parado" || true

# Redis
docker compose stop redis >/dev/null 2>&1 && ok "Redis parado" || true

log "=== Stop completo ==="
