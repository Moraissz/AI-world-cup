## 1. Novo cliente de integração

- [x] 1.1 Criar `app/integrations/football_data_client.py` com classe `FootballDataClient` (base URL, header `X-Auth-Token`, retry com tenacity)
- [x] 1.2 Implementar método `fetch_standings()` — chama `/v4/competitions/WC/standings`
- [x] 1.3 Implementar método `fetch_matches(team, date, status)` — chama `/v4/competitions/WC/matches` com filtros opcionais
- [x] 1.4 Implementar método `fetch_top_scorers()` — chama `/v4/competitions/WC/scorers`
- [x] 1.5 Adicionar `FOOTBALL_DATA_API_KEY` ao `.env.example`

## 2. Modelos de resposta

- [x] 2.1 Adicionar modelos Pydantic em `app/models/football.py` para `StandingsResponse`, `MatchesResponse` e `TopScorersResponse`

## 3. Serviço de Copa

- [x] 3.1 Atualizar `app/services/football_service.py`
- [x] 3.2 Implementar `get_standings()` — consome `fetch_standings()` e transforma em `StandingsResponse`
- [x] 3.3 Implementar `get_matches(team, date, status)` — consome `fetch_matches()` com filtros, normaliza status `live` para `IN_PLAY,PAUSED`, normaliza `date=today` para data atual UTC
- [x] 3.4 Implementar `get_top_scorers()` — consome `fetch_top_scorers()` e transforma em `TopScorersResponse`

## 4. Endpoints na API

- [x] 4.1 Adicionar rotas em `app/controllers/football_controller.py`: `GET /football/world-cup/standings`, `GET /football/world-cup/matches`, `GET /football/world-cup/top-scorers`
- [x] 4.2 Registrar `FootballDataClient` no `container.py` com injeção de dependência

## 5. Atualização do agente

- [x] 5.1 Atualizar `agents/world-cup-specialist/SOUL.md` — adicionar descrição dos 3 novos endpoints com exemplos de chamada curl
- [x] 5.2 Atualizar `agents/world-cup-specialist/HEARTBEAT.md` — adicionar árvore de classificação de intenção (predição / standings / matches / top-scorers / ambíguo) com exemplos de palavras-chave por categoria
- [x] 5.3 Atualizar fluxo de predição no HEARTBEAT.md — incluir chamadas adicionais a `/matches?team=X` para os dois times e instrução de combinar form atual com h2h na resposta

## 6. Testes

- [x] 6.1 Adicionar testes unitários para `FootballDataClient` com mock de respostas HTTP
- [x] 6.2 Adicionar testes para novas funções no service (standings, matches com filtros, top-scorers)
- [x] 6.3 Adicionar testes para os novos endpoints no controller
