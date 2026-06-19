## ADDED Requirements

### Requirement: Classificar intenção da pergunta antes de responder
O agente MUST classificar a intenção de cada mensagem recebida e rotear para o endpoint correto antes de formular a resposta.

#### Scenario: Pergunta de predição com dois times
- **WHEN** a mensagem contém dois times identificáveis e palavras como "quem ganha", "predição", "vai ganhar", "who wins", "predict"
- **THEN** o agente executa o fluxo de predição enriquecida (h2h + form atual)

#### Scenario: Pergunta de classificação ou grupo
- **WHEN** a mensagem contém palavras como "classificação", "grupo", "tabela", "pontos", "classificado", "eliminou", "standings", "group"
- **THEN** o agente chama `/football/world-cup/standings` e responde com a informação do grupo relevante

#### Scenario: Pergunta de agenda ou resultado
- **WHEN** a mensagem contém palavras como "quando joga", "resultado", "placar", "hoje", "ontem", "schedule", "score", "result"
- **THEN** o agente chama `/football/world-cup/matches` com filtros adequados e responde com os jogos encontrados

#### Scenario: Pergunta sobre jogos ao vivo
- **WHEN** a mensagem contém palavras como "ao vivo", "agora", "live", "jogo agora", "está jogando"
- **THEN** o agente chama `/football/world-cup/matches?status=live` e informa se há jogos em andamento e o placar atual

#### Scenario: Pergunta de artilharia
- **WHEN** a mensagem contém palavras como "artilheiro", "artilharia", "gols", "top scorer", "who scored most"
- **THEN** o agente chama `/football/world-cup/top-scorers` e responde com a lista de artilheiros

#### Scenario: Intenção ambígua
- **WHEN** a mensagem não se encaixa em nenhuma categoria acima
- **THEN** o agente pede esclarecimento ao usuário no mesmo idioma da mensagem

### Requirement: Predição enriquecida com form atual
Para perguntas de predição com dois times, o agente MUST combinar dados históricos (h2h) com a performance atual de cada time na Copa 2026.

#### Scenario: Predição com form disponível
- **WHEN** o agente identifica dois times em uma pergunta de predição
- **THEN** chama `/head-to-head`, `/matches?team=TeamA` e `/matches?team=TeamB` e combina os três resultados na resposta, mencionando explicitamente a forma atual de cada time na Copa

#### Scenario: Predição sem jogos na Copa ainda
- **WHEN** um dos times ainda não jogou na Copa 2026 (sem matches retornados)
- **THEN** o agente usa apenas o h2h histórico e menciona que o time ainda não jogou na Copa
