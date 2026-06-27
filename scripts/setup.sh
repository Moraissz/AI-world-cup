#!/usr/bin/env bash
# One-time / idempotent install: toolchain checks, submodules, venv, deps, .env.
# Safe to run repeatedly — nothing is recreated if it already exists.
set -euo pipefail
. "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/common.sh"

log "=== AI World Cup — install ==="

# --- required tooling --------------------------------------------------------
command -v python3 >/dev/null 2>&1 || { err "Python 3 é necessário (https://python.org)"; exit 1; }
ok "Python   $(python3 --version 2>&1 | awk '{print $2}')"
[ -x "$GENIE" ] || command -v genie >/dev/null 2>&1 || { err "Genie CLI não encontrado (https://github.com/automagik-dev/genie)"; exit 1; }
ok "Genie    $("$GENIE" --version 2>/dev/null || genie --version 2>/dev/null)"
[ -x "$OMNI" ] || command -v omni >/dev/null 2>&1 || { err "Omni CLI não encontrado (https://github.com/automagik-dev/omni)"; exit 1; }
ok "Omni     $("$OMNI" --version 2>/dev/null || omni --version 2>/dev/null)"

# --- submodules (genie/ omni/ source — best effort, non-fatal) --------------
if [ -f "${REPO_ROOT}/.gitmodules" ] && [ ! -f "${REPO_ROOT}/genie/package.json" ]; then
  log "Inicializando submódulos (genie/, omni/)..."
  git -C "$REPO_ROOT" submodule update --init --recursive >/dev/null 2>&1 \
    && ok "submódulos prontos" || warn "submódulos não inicializados (sem acesso?) — não é bloqueante"
fi

# --- python venv + deps ------------------------------------------------------
if [ ! -d "$VENV" ]; then
  log "Criando virtualenv (.venv)..."
  python3 -m venv "$VENV"
fi
# shellcheck disable=SC1091
. "${VENV}/bin/activate"
pip install -q -r "${REPO_ROOT}/requirements.txt"
[ -f "${REPO_ROOT}/requirements-dev.txt" ] && pip install -q -r "${REPO_ROOT}/requirements-dev.txt"
ok "dependências Python instaladas"

# --- .env --------------------------------------------------------------------
if [ ! -f "${REPO_ROOT}/.env" ]; then
  cp "${REPO_ROOT}/.env.example" "${REPO_ROOT}/.env"
  warn "Criado .env a partir de .env.example — preencha:"
  printf '         %s\n' \
    "FOOTBALL_IO_SPORTS_API_KEY  -> https://api-sports.io" \
    "FOOTBALL_DATA_ORG_API_KEY   -> https://www.football-data.org" \
    "OMNI_API_KEY                -> omni config show" \
    "API_BASE_URL                -> http://localhost:8000"
else
  ok ".env já existe"
fi

mkdir -p "${REPO_ROOT}/.agent-memory"

log ""
log "=== Install completo ==="
log "Próximos passos:"
log "  1. Preencha o .env"
log "  2. make start      # sobe tudo + conecta o agente ao Omni (idempotente)"
log "  3. make status     # confere o que está rodando"
log "  4. make clean      # (opcional) remove registros de agente Omni antigos"
