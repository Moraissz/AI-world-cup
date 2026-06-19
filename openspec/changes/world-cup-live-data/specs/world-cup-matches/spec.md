## ADDED Requirements

### Requirement: Retornar agenda e resultados da Copa 2026
O sistema SHALL expor um endpoint `GET /football/world-cup/matches` que retorna jogos da Copa 2026 com suporte a filtros opcionais por time, data e status.

#### Scenario: Busca sem filtros retorna todos os jogos
- **WHEN** uma requisição `GET /football/world-cup/matches` é feita sem parâmetros
- **THEN** o sistema retorna HTTP 200 com lista de todos os jogos da Copa, cada jogo contendo: data/hora UTC, mandante, visitante, placar (se disponível), status (SCHEDULED, IN_PLAY, PAUSED, FINISHED), fase (stage)

#### Scenario: Filtro por time
- **WHEN** uma requisição `GET /football/world-cup/matches?team=Brazil` é feita
- **THEN** o sistema retorna apenas jogos onde Brazil é mandante ou visitante

#### Scenario: Filtro por data
- **WHEN** uma requisição `GET /football/world-cup/matches?date=today` é feita
- **THEN** o sistema retorna apenas jogos com data igual ao dia atual (UTC)

#### Scenario: Filtro por status ao vivo
- **WHEN** uma requisição `GET /football/world-cup/matches?status=live` é feita
- **THEN** o sistema retorna apenas jogos com status IN_PLAY ou PAUSED

#### Scenario: Nenhum jogo encontrado com os filtros
- **WHEN** os filtros aplicados não retornam nenhum jogo
- **THEN** o sistema retorna HTTP 200 com lista vazia

#### Scenario: API externa indisponível
- **WHEN** a football-data.org retorna erro 5xx ou timeout
- **THEN** o sistema retorna HTTP 502 com mensagem de erro descritiva
