## ADDED Requirements

### Requirement: Retornar classificação dos grupos da Copa 2026
O sistema SHALL expor um endpoint `GET /football/world-cup/standings` que retorna a classificação de todos os grupos da Copa 2026 com posição, estatísticas e status de cada seleção.

#### Scenario: Busca bem-sucedida
- **WHEN** uma requisição `GET /football/world-cup/standings` é feita
- **THEN** o sistema retorna HTTP 200 com lista de grupos, cada grupo contendo: nome do grupo, e lista de seleções com posição, nome, pontos, jogos, vitórias, empates, derrotas, gols pró, gols contra, saldo de gols

#### Scenario: API externa indisponível
- **WHEN** a football-data.org retorna erro 5xx ou timeout
- **THEN** o sistema retorna HTTP 502 com mensagem de erro descritiva

#### Scenario: Rate limit atingido
- **WHEN** a football-data.org retorna HTTP 429
- **THEN** o sistema retorna HTTP 429 com mensagem indicando limite de requisições atingido
