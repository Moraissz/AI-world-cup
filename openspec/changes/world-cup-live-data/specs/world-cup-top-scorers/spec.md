## ADDED Requirements

### Requirement: Retornar artilharia da Copa 2026
O sistema SHALL expor um endpoint `GET /football/world-cup/top-scorers` que retorna os principais artilheiros da Copa 2026 com gols e assistências.

#### Scenario: Busca bem-sucedida
- **WHEN** uma requisição `GET /football/world-cup/top-scorers` é feita
- **THEN** o sistema retorna HTTP 200 com lista de artilheiros ordenada por gols (decrescente), cada entrada contendo: posição, nome do jogador, seleção, gols, assistências

#### Scenario: Copa ainda sem gols marcados
- **WHEN** a competição ainda não registrou nenhum gol
- **THEN** o sistema retorna HTTP 200 com lista vazia

#### Scenario: API externa indisponível
- **WHEN** a football-data.org retorna erro 5xx ou timeout
- **THEN** o sistema retorna HTTP 502 com mensagem de erro descritiva
