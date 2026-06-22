#!/usr/bin/env bash
# Purge historical junk so the system shows "apenas um agente, sem lixo".
# DESTRUCTIVE (deletes stale Omni agent records) — kept out of the start/stop
# hot path on purpose; run explicitly via `make clean`.
#
# Keeps exactly the Omni agent record the active instance is bound to, and
# soft-deletes every other record named world-cup-specialist. Idempotent:
# once only one remains, re-running is a no-op.
set -uo pipefail
. "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/common.sh"

log "=== Limpeza (make clean) ==="

if ! omni_healthy; then
  err "Omni não está de pé — rode 'make start' antes de 'make clean'"
  exit 1
fi

bound="$(omni_bound_agent_id)"
# GUARD: nunca apagar tudo. Sem agente em-uso válido, aborta sem deletar nada.
if [ -z "$bound" ]; then
  err "instância sem agente conectado (bound vazio) — rode 'make wire' antes. ABORTANDO, nada apagado."
  exit 1
fi
if ! omni_agent_active "$bound"; then
  err "agente em-uso ${bound} está INATIVO — rode 'make wire' pra reconectar um ativo. ABORTANDO, nada apagado."
  exit 1
fi
log "Mantendo agente em-uso (ativo): ${bound}"

# Soft-delete só os ATIVOS que não são o em-uso (inativos já são tombstones).
stale_ids="$("$OMNI" agents list --json 2>/dev/null | python3 -c "
import sys, json
keep = '${bound}'
try: d = json.load(sys.stdin)
except Exception: sys.exit(0)
for a in d:
    if a.get('name') == '${AGENT_NAME}' and a.get('active') == 'yes' and a.get('id') != keep:
        print(a['id'])
")"

removed=0
for id in $stale_ids; do
  if "$OMNI" agents delete "$id" >/dev/null 2>&1; then
    removed=$((removed + 1))
  fi
done
ok "${removed} agente(s) Omni ativo(s) duplicado(s) desativado(s) (soft-delete)"

# Kill any orphan genie sessions whose agent isn't actually running.
for s in $(genie_sessions); do
  tmux -L genie kill-session -t "$s" 2>/dev/null && ok "sessão genie órfã '${s}' encerrada" || true
done
for s in "wc-${AGENT_NAME}" "world-cup" "world-cup-agent"; do
  tmux has-session -t "$s" 2>/dev/null && { tmux kill-session -t "$s" 2>/dev/null && ok "sessão órfã '${s}' encerrada"; } || true
done

remaining="$(omni_active_agent_count)"
log "=== Limpeza completa — ${remaining} agente(s) Omni ativo(s) restante(s) ==="
