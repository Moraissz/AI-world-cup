#!/usr/bin/env bash
# Idempotent Genie <-> Omni wiring for the world-cup-specialist agent.
#
# Replaces the old destructive "delete everything then recreate" flow. Running
# this many times converges to the same state (no duplicate agents, no rebind
# churn). The WhatsApp round-trip is served by the genie omni-bridge, which
# spawns a per-chat agent (session strategy = per_chat) using the inbound
# message as its prompt — so no standing/idle master is needed.
#
# Usage:
#   register-agent.sh              # idempotent wiring (default; called by `make start`)
#   register-agent.sh --spawn-only # open a manual debug session (`make agent-spawn`)
set -euo pipefail
. "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/common.sh"

# --- idempotent Omni connection (omni connect mints a NEW record each call, so
#     we only call it when the instance no longer points at our wired agent) ---
wire_omni() {
  local instance bound last n
  instance="$(omni_instance_id)"
  if [ -z "$instance" ]; then
    log "Nenhuma instância Omni encontrada. Criando instância WhatsApp-Baileys..."
    instance="$("$OMNI" instances create --channel whatsapp-baileys --name "world-cup" --json 2>/dev/null \
      | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['data']['id'])" 2>/dev/null || true)"
    if [ -z "$instance" ]; then
      err "Falha ao criar instância Omni."
      err "Crie manualmente: omni instances create --channel whatsapp-baileys --name world-cup"
      return 1
    fi
    ok "Instância criada: ${instance}"
    # Bind agent before QR so the instance is wired as soon as WhatsApp connects.
    "$OMNI" connect "$instance" "$AGENT_NAME" --mode turn-based --reply-filter all >/dev/null 2>&1 || true
    mkdir -p "$STATE_DIR"
    bound="$(omni_bound_agent_id)"
    [ -n "$bound" ] && printf '%s\n' "$bound" > "$WIRED_MARKER"
    log ""
    log "Escaneie o QR code abaixo com o WhatsApp (Dispositivos Vinculados → Vincular dispositivo):"
    log ""
    "$OMNI" instances qr "$instance" --no-watch 2>/dev/null || warn "QR indisponível — tente: omni instances qr ${instance}"
    log ""
    warn "QR exibido acima. Após escanear, rode 'make start' (ou 'make status') para confirmar a conexão."
    return 0
  fi
  bound="$(omni_bound_agent_id)"
  mkdir -p "$STATE_DIR"
  last="$(cat "$WIRED_MARKER" 2>/dev/null || true)"
  # Idempotente só se a instância aponta pro agente gravado E ele ainda está ATIVO.
  # (Se o agente em-uso virou inativo — ex: soft-delete — reconecta um novo ativo.)
  if [ -n "$bound" ] && [ "$bound" = "$last" ] && omni_agent_active "$bound"; then
    ok "Omni já conectado ao agente ativo ${bound} (idempotente — sem rebind)"
  else
    log "Atualizando conexão Omni: instância ${instance} -> ${AGENT_NAME}..."
    "$OMNI" connect "$instance" "$AGENT_NAME" --mode turn-based --reply-filter all >/dev/null 2>&1
    bound="$(omni_bound_agent_id)"
    printf '%s\n' "$bound" > "$WIRED_MARKER"
    ok "instância (re)conectada ao agente ativo ${bound}"
  fi
  n="$(omni_active_agent_count)"
  if [ "${n:-0}" -gt 1 ]; then
    warn "${n} agentes Omni ATIVOS (acúmulo) — rode 'make clean' para deixar só 1"
  fi
}

# --- the omni-bridge is the thing that actually answers WhatsApp messages ---
ensure_bridge() {
  if genie_bridge_running; then
    ok "omni-bridge ativo — atende WhatsApp (spawn por-chat sob demanda)"
  else
    warn "omni-bridge NÃO está ativo — confira 'genie serve status' (Omni precisa estar de pé antes do genie serve)"
  fi
}

# --- optional manual debug session (NOT used by the happy path) ---
ensure_master() {
  if tmux -L genie has-session -t "$AGENT_NAME" 2>/dev/null; then
    ok "sessão master '${AGENT_NAME}' já existe — reutilizada (nada criado)"
    return 0
  fi
  log "Abrindo sessão master de debug (detached)..."
  tmux kill-session -t "wc-${AGENT_NAME}" 2>/dev/null || true
  tmux new-session -d -s "wc-${AGENT_NAME}" \
    "exec env GENIE_NO_V1_PROMPT=1 '${GENIE}' spawn '${AGENT_NAME}'" 2>/dev/null \
    && ok "sessão aberta — attach com: tmux attach -t wc-${AGENT_NAME}" \
    || warn "não foi possível abrir a sessão de debug"
}

case "${1:-wire}" in
  --spawn-only|spawn-only)
    genie_serve_running || { err "genie serve não está rodando — rode 'make start'"; exit 1; }
    ensure_master
    exit 0
    ;;
esac

# ---- wiring (happy path) ----
genie_serve_running || { err "genie serve não está rodando — rode 'make start' primeiro"; exit 1; }
genie_db_running    || { err "pgserve (postgres :5432) fora — rode 'make start' (ou 'make start-genie')"; exit 1; }
wait_for_omni_healthy 30 || { err "Omni não ficou saudável em 30s — verifique com 'omni status'"; exit 1; }

log "=== Conectando ${AGENT_NAME} ao Omni (idempotente) ==="
"$GENIE" omni handshake >/dev/null 2>&1 && ok "handshake Genie<->Omni" || ok "handshake já estabelecido"

# Empurra as instruções do disco (SOUL/HEARTBEAT/AGENTS/agent.yaml) -> PG do genie.
# Também (re)registra o agente. O prompt novo vale pra spawns frescos e conversas novas;
# chat já ativo (sessionReset=None) só recarrega com 'make sync-agent'.
log "Sincronizando instruções (agents/ -> genie)..."
"$GENIE" dir sync >/dev/null 2>&1 && ok "instruções sincronizadas (dir sync)" || warn "genie dir sync falhou"
if agent_registered; then
  ok "agente registrado no Genie"
else
  "$GENIE" agent register "$AGENT_NAME" --dir "$AGENT_DIR" --skip-omni >/dev/null 2>&1
  agent_registered && ok "agente registrado" || warn "falha ao registrar agente"
fi

wire_omni
ensure_bridge
log "=== Pronto — mande uma mensagem no WhatsApp para testar ==="
