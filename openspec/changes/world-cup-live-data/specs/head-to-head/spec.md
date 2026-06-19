## MODIFIED Requirements

### Requirement: Predição combinada com form atual da Copa
Para predições, o agente MUST enriquecer a resposta do `/head-to-head` com a performance atual dos dois times na Copa 2026, obtida via `/world-cup/matches?team=X`.

#### Scenario: Resposta de predição enriquecida
- **WHEN** o agente chama `/head-to-head` para predição
- **THEN** o agente DEVE TAMBÉM chamar `/world-cup/matches?team=TeamA` e `/world-cup/matches?team=TeamB` e incluir na resposta: histórico de confrontos (via h2h) E performance atual na Copa (últimos resultados de cada time)

#### Scenario: Um time ainda não jogou na Copa
- **WHEN** `/world-cup/matches?team=X` retorna lista vazia para um dos times
- **THEN** o agente menciona que o time ainda não disputou jogos na Copa 2026 e baseia a predição apenas no histórico

#### Scenario: Endpoint h2h indisponível
- **WHEN** `/head-to-head` retorna erro
- **THEN** o agente responde com mensagem de desculpa e não faz predição sem dados
