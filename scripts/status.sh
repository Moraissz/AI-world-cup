#!/usr/bin/env bash
# Read-only health snapshot of the whole stack. Shows the expected processes and
# flags accumulation (stale Omni agent records / extra genie sessions).
set -uo pipefail
. "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/common.sh"

line() { printf '  %-14s %s\n' "$1" "$2"; }

log "=== AI World Cup — status ==="

# Redis
if docker compose ps redis 2>/dev/null | grep -qiE 'up|running|healthy'; then
  line "Redis" "up (:6379)"
else
  line "Redis" "down"
fi

# Omni
if omni_healthy; then
  line "Omni API" "healthy (${OMNI_API_URL})"
else
  line "Omni API" "down  (rode 'make start')"
fi

# Genie serve + bridge
if genie_serve_running; then
  if genie_bridge_running; then
    line "Genie serve" "running (omni-bridge: up)"
  else
    line "Genie serve" "running (omni-bridge: DOWN)"
  fi
else
  line "Genie serve" "stopped"
fi

# Postgres do genie (gate de register/wire)
if genie_db_running; then line "pgserve" "running (:5432)"; else line "pgserve" "DOWN (:5432) — 'make start'"; fi

# FastAPI
if api_up; then line "FastAPI" "up (${API_URL}/docs)"; else line "FastAPI" "down"; fi

# Agent registration + Omni wiring
if agent_registered; then line "Agent (genie)" "registered"; else line "Agent (genie)" "NOT registered"; fi

bound="$(omni_bound_agent_id)"; active="$(omni_active_agent_count)"; total="$(omni_total_agent_count)"
tomb=$(( ${total:-0} - ${active:-0} ))
if [ -z "$bound" ]; then
  line "Omni wiring" "no agent bound — 'make wire'"
elif omni_agent_active "$bound"; then
  line "Omni wiring" "instance -> ${bound} (ativo)"
else
  line "Omni wiring" "instance -> ${bound} (INATIVO — 'make wire')"
fi
line "Omni agents" "${active:-0} ativo(s) (+${tomb} tombstones inativos)"
if [ "${active:-0}" -gt 1 ]; then
  warn "acúmulo: ${active} agentes ATIVOS — rode 'make clean' para deixar só 1"
fi

# Genie sessions (per-chat agents spawned by the bridge + any manual master)
sessions="$(genie_sessions)"
n_sessions=$(printf '%s' "$sessions" | grep -c . || true)
line "Genie sessions" "${n_sessions:-0}"
if [ "${n_sessions:-0}" -gt 0 ]; then
  printf '%s\n' "$sessions" | sed 's/^/                   - /'
fi

log "============================="
