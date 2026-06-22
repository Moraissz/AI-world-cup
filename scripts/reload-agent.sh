#!/usr/bin/env bash
# Aplica instruções editadas (AGENTS.md / HEARTBEAT.md / SOUL.md) a TODOS os chats,
# inclusive os já ativos.
#
# Por que é preciso: o genie carrega o prompt (AGENTS.md, que importa HEARTBEAT/SOUL)
# do disco no spawn. Um chat já ativo dá `--resume` na sessão antiga e mantém o prompt
# velho. Resetar a sessão do bridge força a próxima mensagem a spawnar fresh e ler o
# prompt atual. A memória da conversa fica em arquivo (.agent-memory/), então o reset
# NÃO apaga o histórico.
set -uo pipefail
. "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/common.sh"

genie_db_running || { err "pgserve (postgres :5432) fora — rode 'make start' primeiro"; exit 1; }

log "=== reload-agent: aplicando instruções novas ==="

# 1. Empurra config (agent.yaml) pro PG e (re)registra.
log "Sincronizando agents/ -> genie..."
"$GENIE" dir sync 2>&1 | grep -iE "Updated|Synced" || true

# 2. Reseta as sessões do bridge -> próxima msg de cada chat = spawn fresh = prompt novo.
out="$("$GENIE" db query "DELETE FROM genie_bridge_sessions WHERE agent_name='${AGENT_NAME}'" 2>/dev/null | grep -oiE '[0-9]+ rows affected' | head -1)"
ok "sessões do bridge resetadas (${out:-nenhuma})"

# 3. Encerra panes órfãos do agente (sessões claude presas).
for s in $(genie_sessions); do
  tmux -L genie kill-session -t "$s" 2>/dev/null && ok "pane '${s}' encerrado" || true
done

log "=== Pronto — a próxima mensagem de cada chat usa as instruções novas ==="
