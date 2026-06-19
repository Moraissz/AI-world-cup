## Context

A API atual tem um único endpoint (`/football/head-to-head`) que usa `api-sports.io` com plano free (dados históricos até 2024). O agente `world-cup-specialist` chama esse endpoint para toda pergunta, independente do tipo. Durante a Copa 2026, a maioria das perguntas dos torcedores é sobre classificação, agenda, resultados e artilharia — dados que a API atual não fornece.

A `football-data.org` oferece dados ao vivo da Copa 2026 no plano free (limite: 10 req/min). Ela não tem dados históricos, apenas dados do torneio atual.

Restrições relevantes:
- Ambas as APIs são free tier com rate limiting
- Cache está planejado mas fora do escopo desta mudança
- O agente roda via genie/omni respondendo mensagens WhatsApp (texto plano, sem markdown)

## Goals / Non-Goals

**Goals:**
- Adicionar 3 novos endpoints usando football-data.org: standings, matches, top-scorers
- Encapsular football-data.org em um novo cliente (`FootballDataClient`) isolado do existente
- Expandir `FootballService` com os novos métodos (standings, matches, top-scorers) em vez de criar serviço separado
- Atualizar o agente para rotear perguntas ao endpoint correto e enriquecer predições com form atual

**Non-Goals:**
- Cache de respostas (escopo futuro)
- Autenticação na API interna (escopo futuro)
- Suporte a outras competições além da Copa 2026
- Dados de jogadores individuais (além de artilharia)

## Decisions

### 1. Dois clientes separados, não um unificado

**Decisão**: `FootballDataClient` é uma classe nova e independente de `FootballApiClient`.

**Alternativa considerada**: Estender `FootballApiClient` para suportar as duas APIs.

**Rationale**: As APIs têm autenticação diferente (header `x-rapidapi-key` vs. `X-Auth-Token`), base URLs diferentes e modelos de resposta completamente distintos. Unificar criaria acoplamento desnecessário e dificultaria substituir uma sem afetar a outra. Separar também facilita o cache futuro por cliente.

---

### 2. Um endpoint `/world-cup/matches` versátil com filtros, não três endpoints separados

**Decisão**: Um único `GET /football/world-cup/matches` com query params opcionais (`?team`, `?date`, `?status`).

**Alternativa considerada**: `/world-cup/schedule`, `/world-cup/results`, `/world-cup/live` separados.

**Rationale**: A football-data.org retorna todos os jogos em um endpoint com campos `status` e `utcDate`. Filtrar no backend evita múltiplas chamadas e mantém a API simples. O campo `stage` no response permite que o agente diferencie fase de grupos de mata-mata sem endpoint dedicado.

---

### 3. Roteamento semântico no agente, não na API

**Decisão**: A lógica de "qual endpoint chamar" fica no HEARTBEAT.md do agente, não em um endpoint de roteamento na API.

**Rationale**: O agente já é um LLM — ele consegue classificar a intenção da pergunta sem código adicional. Colocar roteamento na API criaria um endpoint de linguagem natural que não agrega valor além do que o agente já faz. A API permanece RESTful e stateless.

---

### 4. Form atual buscado pelo agente em chamadas separadas, não em endpoint composto

**Decisão**: Para predições, o agente chama `/matches?team=X` para cada time e combina com o resultado do `/head-to-head`. Não há endpoint `/predict` ou `/head-to-head-with-form`.

**Rationale**: Manter endpoints simples e de responsabilidade única. A síntese é trabalho do LLM, não da API.

## Risks / Trade-offs

**Rate limit de 10 req/min na football-data.org** → Predições enriquecidas fazem 3 chamadas (h2h + 2x form). Em uso simultâneo por múltiplos usuários, pode atingir o limite. Mitigação: cache (escopo futuro). Por ora, tratar 429 como erro gracioso no cliente.

**football-data.org pode mudar IDs ou estrutura do response** → O código de parsing ficará no `FootballDataClient`, isolado do serviço. Qualquer mudança na API externa afeta apenas o client.

**Agente pode classificar mal a intenção** → O HEARTBEAT deve ter critérios de classificação bem definidos com exemplos explícitos. Fallback: se nenhum endpoint cabe, pedir esclarecimento ao usuário.

**Dados ao vivo com atraso** → football-data.org free tier pode ter delay de alguns minutos no placar ao vivo. Não há mitigação possível sem upgrade do plano — o agente deve mencionar que dados ao vivo podem ter pequeno atraso.

## Open Questions

- O competition code da Copa 2026 na football-data.org é `WC`? Confirmar na documentação ou com uma chamada de teste antes de implementar.
