## Why

O agente atualmente só responde perguntas históricas de confronto (h2h). Durante a Copa 2026, os torcedores também querem saber classificações, agenda, resultados ao vivo e artilharia — dados que a API atual (api-sports.io, plano free, dados até 2024) não fornece. A football-data.org oferece dados ao vivo da Copa 2026 gratuitamente e preenche exatamente esse gap.

## What Changes

- Novo cliente de integração `FootballDataClient` consumindo `https://api.football-data.org/v4`
- Três novos endpoints REST na FastAPI:
  - `GET /football/world-cup/standings` — tabela de classificação de todos os grupos
  - `GET /football/world-cup/matches` — agenda e resultados com filtros opcionais (`?team`, `?date`, `?status`)
  - `GET /football/world-cup/top-scorers` — artilharia da Copa
- Atualização do agente `world-cup-specialist` (SOUL.md + HEARTBEAT.md):
  - Roteamento semântico: classifica a pergunta antes de escolher o endpoint
  - Predições passam a combinar h2h histórico + form atual dos dois times na Copa
- Nova variável de ambiente `FOOTBALL_DATA_API_KEY`

## Capabilities

### New Capabilities

- `world-cup-standings`: Endpoint que retorna a classificação por grupo da Copa 2026 (posição, pontos, saldo de gols, status de classificação)
- `world-cup-matches`: Endpoint que retorna agenda e resultados da Copa 2026 com filtros por time, data e status (inclui jogos ao vivo e fases eliminatórias)
- `world-cup-top-scorers`: Endpoint que retorna a artilharia da Copa 2026
- `agent-routing`: Lógica de roteamento semântico no agente para classificar perguntas e chamar o endpoint correto; predições enriquecidas com form atual

### Modified Capabilities

- `head-to-head`: O comportamento do agente muda — ao fazer predições, passa a combinar h2h com form atual da Copa. O endpoint em si não muda, apenas o fluxo do agente.

## Impact

- **Novo arquivo**: `app/integrations/football_data_client.py`
- **Modificado**: `app/services/football_service.py` — novos métodos para standings, matches e top-scorers
- **Modificado**: `app/models/football.py` — novos models de response
- **Modificado**: `app/controllers/football_controller.py` — novos routes
- **Modificado**: `container.py` — novo cliente injetado
- **Modificado**: `.env.example` — nova variável `FOOTBALL_DATA_API_KEY`
- **Modificado**: `agents/world-cup-specialist/SOUL.md` e `HEARTBEAT.md`
- **Nova dependência**: nenhuma (usa `httpx` já presente)
