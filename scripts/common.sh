#!/usr/bin/env bash
# Shared constants + helpers for the AI World Cup setup scripts.
# Sourced by setup.sh / register-agent.sh / status.sh / stop.sh / clean.sh.
#
# Every helper here is read-only and idempotent. The goal: each `make` target
# can "check then act" instead of blindly creating/deleting things.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

GENIE="${GENIE:-$HOME/.local/bin/genie}"
OMNI="${OMNI:-$HOME/.bun/bin/omni}"
VENV="${REPO_ROOT}/.venv"
AGENT_NAME="world-cup-specialist"
AGENT_DIR="${REPO_ROOT}/agents/${AGENT_NAME}"
API_PORT="8000"
API_URL="http://localhost:${API_PORT}"

# genie postgres (autopg). `genie serve` nem sempre sobe o pg nesta máquina, então
# garantimos via pg_ctl direto na porta 5432.
# autopg >= v3 instala em ~/.local/share/autopg/<version>/postgres/bin/pg_ctl.
PG_DATA="${HOME}/.autopg/data"
PG_CTL="$(ls -d "${HOME}"/.local/share/autopg/*/postgres/bin/pg_ctl 2>/dev/null | head -1)" || PG_CTL=""
PG_SOCK="/run/user/$(id -u)/pgserve"

# Where we remember the Omni agent id we wired the instance to. This makes
# `omni connect` idempotent without deleting anything: we only re-connect when
# the instance no longer points at the agent we last wired.
STATE_DIR="${XDG_CACHE_HOME:-$HOME/.cache}/ai-world-cup"
WIRED_MARKER="${STATE_DIR}/omni-wired-agent"

# Load OMNI_API_URL (and friends) from .env — genie omni handshake/connect read it.
if [ -f "${REPO_ROOT}/.env" ]; then
  set -a; . "${REPO_ROOT}/.env"; set +a
fi
export OMNI_API_URL="${OMNI_API_URL:-http://localhost:8882}"
export GENIE_NO_V1_PROMPT=1   # silence the legacy-v1 migration nag in script output

log()  { printf '%s\n' "$*"; }
ok()   { printf '  [ok] %s\n' "$*"; }
warn() { printf '  [warn] %s\n' "$*"; }
err()  { printf '  [ERRO] %s\n' "$*" >&2; }

# ---- service health probes (idempotency gates) ----------------------------

omni_healthy() { "$OMNI" status --json 2>/dev/null | grep -q '"apiStatus": *"healthy"'; }

genie_serve_running() {
  "$GENIE" serve status 2>/dev/null | grep -qE '^[[:space:]]*Status:[[:space:]]+running'
}

genie_bridge_running() {
  "$GENIE" serve status 2>/dev/null | grep -qiE 'omni-bridge:[[:space:]]+running'
}

api_up() { curl -sf -o /dev/null "${API_URL}/docs" 2>/dev/null; }

# pg up = genie consegue ler o diretório/registrar. `genie dir ls` retorna exit 0
# mesmo quando falha, então checamos o texto.
genie_db_running() { "$GENIE" db status 2>/dev/null | grep -qiE 'Status:[[:space:]]+running'; }

# Sobe o postgres do genie (5432) se estiver fora. Idempotente.
ensure_pg() {
  if genie_db_running; then ok "pgserve já rodando (5432)"; return 0; fi
  if [ -z "$PG_CTL" ] || [ ! -x "$PG_CTL" ] || [ ! -d "$PG_DATA" ]; then
    warn "pgserve fora e pg_ctl/data não encontrados (${PG_DATA})"; return 1
  fi
  mkdir -p "$PG_SOCK" "${HOME}/.autopg/logs"
  "$PG_CTL" -D "$PG_DATA" -l "${HOME}/.autopg/logs/manual-pg.log" \
    -o "-p 5432 -k ${PG_SOCK}" -w -t 30 start >/dev/null 2>&1 \
    && ok "pgserve iniciado (postgres 5432)" || warn "falha ao subir pgserve"
}

# registrado = `genie dir ls` NÃO diz "not found" (robusto a exit-code 0 enganoso).
agent_registered() { ! "$GENIE" dir ls "$AGENT_NAME" 2>&1 | grep -qi "not found"; }

# ---- Omni state readers (JSON, robust) ------------------------------------

# First ACTIVE instance id (the connected WhatsApp channel).
omni_instance_id() {
  "$OMNI" instances list --json 2>/dev/null | python3 -c "
import sys, json
try: d = json.load(sys.stdin)
except Exception: sys.exit(0)
for i in d:
    if i.get('isActive'):
        print(i['id']); break
"
}

# The agent id the active instance is currently bound to.
omni_bound_agent_id() {
  "$OMNI" instances list --json 2>/dev/null | python3 -c "
import sys, json
try: d = json.load(sys.stdin)
except Exception: sys.exit(0)
for i in d:
    if i.get('isActive'):
        print(i.get('agentId') or ''); break
"
}

# ACTIVE agent records (active=='yes'). Real gauge — soft-deleted tombstones
# linger in `omni agents list` by design but don't count as live duplicates.
omni_active_agent_count() {
  "$OMNI" agents list --json 2>/dev/null | python3 -c "
import sys, json
try: d = json.load(sys.stdin)
except Exception: print(0); sys.exit(0)
print(len([a for a in d if a.get('name') == '${AGENT_NAME}' and a.get('active') == 'yes']))
"
}

# Total records (active + inactive tombstones) — display only.
omni_total_agent_count() {
  "$OMNI" agents list --json 2>/dev/null | python3 -c "
import sys, json
try: d = json.load(sys.stdin)
except Exception: print(0); sys.exit(0)
print(len([a for a in d if a.get('name') == '${AGENT_NAME}']))
"
}

# Is a specific agent id active (isActive=true)? Uses `agents get` (reliable field).
omni_agent_active() {
  [ -n "${1:-}" ] || return 1
  "$OMNI" agents get "$1" --json 2>/dev/null | python3 -c "
import sys, json
try: d = json.load(sys.stdin)
except Exception: sys.exit(1)
sys.exit(0 if d.get('isActive') is True else 1)
"
}

# Live genie tmux sessions for this agent (master + per-chat). Echoes session names.
genie_sessions() { tmux -L genie ls 2>/dev/null | grep -E "^${AGENT_NAME}(:|@)" | cut -d: -f1; }

# Poll until Omni is healthy or timeout (seconds). Used by register-agent.sh to
# survive the cold-start window where `omni start` exits 0 before the API is ready.
wait_for_omni_healthy() {
  local max_wait="${1:-30}" elapsed=0 interval=2
  if omni_healthy; then return 0; fi
  log "Aguardando Omni ficar saudável (max ${max_wait}s)..."
  while ! omni_healthy; do
    if [ "$elapsed" -ge "$max_wait" ]; then return 1; fi
    sleep "$interval"
    elapsed=$((elapsed + interval))
  done
  ok "Omni saudável após ${elapsed}s"
}
