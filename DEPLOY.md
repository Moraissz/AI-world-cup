# Estratégia de Deploy — AI World Cup Agent

> **Nota:** Esta estratégia foi planejada como exercício técnico. O deploy não foi executado neste projeto.

## Visão Geral

O sistema tem três camadas lógicas com restrições de deploy distintas:

```
WhatsApp ↔ Omni (bridge WhatsApp, precisa de sessão persistente)
               ↓
         Genie (orquestrador de agentes, precisa de tmux + postgres)
               ↓
         FastAPI (HTTP stateless, deployável em qualquer lugar)
               ↓
         api-sports.io / football-data.org (externos, sem deploy)
```

**Restrição fundamental:** O Omni usa Baileys para conectar ao WhatsApp. Os arquivos de sessão (auth) precisam persistir entre reinicializações. Logo, Omni e Genie **não podem rodar em containers efêmeros** — precisam de uma máquina com storage persistente.

---

## Estratégia Recomendada: Railway + Upstash + VPS

| Componente | Plataforma | Custo |
|---|---|---|
| FastAPI | Railway (free tier) | $0 |
| Redis | Upstash (free tier) | $0 |
| Genie + Omni + agente | VPS própria | ~$4–6/mês |

> A separação Railway/VPS é motivada pela restrição de storage persistente
> do Omni (sessão Baileys). A API FastAPI é stateless e pode rodar em
> qualquer container efêmero; o core não pode.

### Pré-requisitos (antes de qualquer deploy)

**1. Criar `.dockerignore`** na raiz do projeto (evita que `.env` local entre na imagem Railway):

```
.env
.venv/
__pycache__/
*.pyc
.git/
```

**2. Adicionar TLS na conexão Redis** (`container.py`):

```python
client = aioredis.Redis(
    host=host,
    port=port,
    password=password or None,
    decode_responses=True,
    ssl=True,          # obrigatório para Upstash
)
```

### Variáveis de ambiente por plataforma

**Railway (painel ou CLI):**

```env
FOOTBALL_IO_SPORTS_API_KEY=<chave api-sports.io>
FOOTBALL_DATA_ORG_API_KEY=<chave football-data.org>
REDIS_HOST=<endpoint>.upstash.io
REDIS_PORT=6380
REDIS_PASSWORD=<token-upstash>
```

**VPS (`.env`):**

```env
ANTHROPIC_API_KEY=<chave anthropic>
OMNI_API_KEY=<chave omni>
OMNI_API_URL=http://localhost:8882
API_BASE_URL=https://ai-world-cup-xxx.up.railway.app
```

---

## Estimativa de custo

| Opção | Custo mensal | Complexidade |
|---|---|---|
| Railway + Upstash + VPS | ~$4–6 (só VPS) | Média |
| Oracle Always Free (tudo) | $0 | Média |
| VPS única (Hetzner CX11) | ~$4 | Baixa |
| Local + ngrok | $0 | Mínima |
