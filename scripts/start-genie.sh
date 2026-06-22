#!/usr/bin/env bash
# Sobe genie serve (bridge) + garante o postgres do genie (:5432). Idempotente.
# Necessário porque `genie serve start --headless` nem sempre sobe o pgserve.
set -uo pipefail
. "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/common.sh"

if genie_serve_running; then
  ok "genie serve já rodando"
else
  log "Subindo genie serve..."
  "$GENIE" serve start --headless --daemon >/dev/null 2>&1 && ok "genie serve iniciado" || warn "falha no genie serve"
fi

ensure_pg   # postgres :5432 — sobe via pg_ctl se estiver fora

if genie_bridge_running; then ok "omni-bridge ativo"; else warn "omni-bridge fora (Omni precisa estar de pé)"; fi
