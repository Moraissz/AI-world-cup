# AI World Cup — Agente de Previsões de Futebol

Agente para WhatsApp que responde perguntas sobre a Copa do Mundo FIFA 2026.
Recebe mensagens via Omni, processa com Claude via Genie e responde com previsões, classificação, agenda e artilharia baseadas em dados em tempo real.

---

## Arquitetura

```mermaid
flowchart LR
    WA[WhatsApp] -->|mensagem| Omni["Omni\n(bridge Baileys)"]
    Omni -->|NATS :4222| Genie["Genie\n(omni-bridge)"]
    Genie -->|spawn per_chat| Agent["world-cup-specialist\nClaude Sonnet"]
    Agent -->|curl h2h + matches\n+ standings + scorers\n+ memory| API["FastAPI\n:8000"]
    API -->|h2h / busca de time| ASIO["api-sports.io"]
    API -->|standings / matches\n/ top-scorers| FDO["football-data.org"]
    API -->|cache de API\n+ memória de conversa| Redis[("Redis\n:6379")]
    Agent -->|omni done 'texto'| Omni
    Omni -->|resposta| WA
```

### Fluxo de uma mensagem ponta-a-ponta

```mermaid
sequenceDiagram
    participant U as Usuário
    participant WA as WhatsApp
    participant Omni as Omni :8882
    participant Genie as Genie omni-bridge
    participant Agent as world-cup-specialist
    participant API as FastAPI :8000
    participant Redis as Redis :6379
    participant Ext as APIs externas

    U->>WA: mensagem
    WA->>Omni: entrega
    Omni->>Genie: NATS :4222 (turn)
    Genie->>Agent: spawn por chat (per_chat)
    Agent->>API: GET /memory/{chat_id}
    API->>Redis: get ai-world-cup-agent:memory:{id}
    Redis-->>API: histórico ou estrutura vazia
    API-->>Agent: last_teams, history, preferred_language
    Agent->>API: curl endpoints em paralelo
    API->>Redis: verificar cache
    alt cache hit
        Redis-->>API: dados em cache
    else cache miss
        API->>Ext: requisição HTTP
        Ext-->>API: dados
        API->>Redis: set (TTL 5 min – 7 dias)
    end
    API-->>Agent: JSON de resposta
    Agent->>API: POST /memory/{chat_id}
    API->>Redis: set (TTL 7 dias)
    Agent->>Omni: omni done "resposta em texto plano"
    Omni->>WA: entrega resposta
    WA->>U: mensagem
```

### Ciclo de vida do agente (por turn)

```mermaid
flowchart TD
    START([mensagem WhatsApp chega]) --> SPAWN["Genie faz spawn\ndo agente por chat"]
    SPAWN --> S1["Step 1 — GET /memory/{chat_id}\ncarregar histórico e last_teams"]
    S1 --> S2["Step 2 — Quais ferramentas?\n(uma mensagem pode usar várias)"]
    S2 -->|dois times identificados| S3P["Step 3 · Predição\ncurl h2h + matches\nem paralelo"]
    S2 -->|classificação / grupo| S3S["Step 3 · Standings\nGET /world-cup/standings"]
    S2 -->|agenda / ao vivo / resultado| S3M["Step 3 · Matches\nGET /world-cup/matches?filtros"]
    S2 -->|artilharia / gols| S3T["Step 3 · Top-scorers\nGET /world-cup/top-scorers"]
    S2 -->|saudação / ambíguo / erro| S7["Step 4 · sem dados\nboas-vindas ou clarificação"]
    S3P --> S4[Step 4 — Compor resposta\nem texto plano, sem markdown]
    S3S --> S4
    S3M --> S4
    S3T --> S4
    S4 --> MEM["POST /memory/{chat_id}\natualizar histórico, last_teams,\npreferred_language"]
    S7 --> MEM
    MEM --> DONE["omni done 'resposta'"]
    DONE --> END([turn encerrado])
```

### Stack

| Camada        | Componente               | Função                                           |
| ------------- | ------------------------ | ------------------------------------------------ |
| Canal         | Omni + Baileys           | Bridge WhatsApp, roteamento NATS (:4222)         |
| Orquestração  | Genie v4                 | Ciclo de vida do agente, inbox, turns            |
| IA            | Claude Sonnet            | NLU, geração de previsões e respostas            |
| Dados         | FastAPI + api-sports.io  | Histórico de confrontos diretos (h2h)            |
| Dados (Copa)  | football-data.org        | Classificação, agenda, resultados, artilharia    |
| Memória       | Redis + FastAPI /memory  | Histórico de conversa por chat (TTL 7 dias)      |
| Cache         | Redis (opcional)         | Cache das respostas das APIs externas            |

### Decisões arquiteturais

**1. Agente chama FastAPI via curl, não importação direta**
O agente é um processo Claude Code com acesso ao bash. Chama
`curl http://localhost:8000/...` para buscar dados. Isso mantém agente e API
independentemente reiniciáveis com contrato HTTP limpo.

**2. Sem subscriber NATS no FastAPI**
O Omni + Genie gerenciam o roteamento via NATS nativamente. Adicionar um subscriber
na API criaria dois consumidores concorrentes e acoplaria a camada de dados ao
transporte do agente.

**3. Modo turn-based no Omni**
Cada mensagem WhatsApp é um turn Omni. O agente lê o contexto, processa e fecha com
`omni done "texto"`. Modelo correto para Q&A: uma mensagem entra, uma sai.

**4. Respostas apenas em texto plano**
O WhatsApp renderiza `*`, `**` e `#` como caracteres literais. Todas as respostas
são texto plano sem markdown — enforçado no `AGENTS.md`. O mesmo output contract fixa
ainda: resposta no idioma detectado do usuário (PT/ES/EN), no máximo 3 parágrafos e
sempre encerrando com a assinatura `⚽⚽🏆`.

**5. Memória por conversa no Redis via FastAPI**
Cada remetente WhatsApp tem um registro no Redis com chave
`ai-world-cup-agent:memory:{chatId}` (TTL 7 dias). O agente faz
`GET /memory/{chatId}` no início de cada turn para carregar histórico e
`POST /memory/{chatId}` após responder para persistir. Armazena os últimos 10
turnos (20 entradas), `last_teams` (últimos dois times discutidos) e
`preferred_language`.

A memória persiste em **todas** as intenções (predição, classificação, agenda,
artilharia, saudação, erro) — não só nas predições. O objetivo é manter o **fio da
conversa**: assim o usuário pode perguntar "e o artilheiro deles?" depois de "quando o
Brasil joga?" sem repetir o time, e o idioma sobrevive entre turnos.

O que a memória **não** é: um cache de dados. Standings, placares e artilharia mudam a
cada jogo, então o agente nunca cita um número vindo do `history` — ele guarda o texto da
conversa, mas **sempre rebusca os dados ao vivo** dos endpoints a cada turn. O `history`
serve ao contexto conversacional (resolver "deles", "de novo", o grupo mencionado antes),
não como fonte de verdade numérica.

**6. Cache com decorator próprio e `redis.asyncio`**
`app/utils/cache.py` implementa um decorator `@cache(ttl=..., key_builder=...)`
usando `redis.asyncio` diretamente. TTLs por endpoint: 7 dias (busca de time),
24h (h2h), 5 min (standings e matches), 10 min (top-scorers), 60s (matches
ao vivo). Se o Redis não estiver disponível (`REDIS_HOST` ausente), o decorator
simplesmente não cacheia — sem erro, sem dependência obrigatória.

**7. FastAPI como processo local, não container**
O docker-compose sobe apenas o Redis. O uvicorn roda diretamente no venv via
`make start`. Evita conflito de porta e simplifica o ciclo de debug.

**8. A predição é do agente, sobre dados reais**
A API não tem motor de probabilidade — ela entrega dados; o agente combina e prediz.
As fontes são reais: histórico do confronto (`/head-to-head`, via api-sports.io), forma
recente na Copa 2026 (`/world-cup/matches?teams=X`, via football-data.org) e, quando
fundamenta, posição e saldo de gols no grupo (`/world-cup/standings`). O agente pondera
esses sinais e dá sempre uma inclinação qualitativa fundamentada — nunca um percentual,
nunca dígitos inventados —, com a força do palpite escalada à evidência:

- **Evidência forte** (ambos os times com jogos na Copa, standings e histórico) → uma
  inclinação confiante e justificada ("vantagem clara do Brasil, que fez 5 e sofreu 2 no
  grupo, enquanto a França levou 4 — mas a França tem o ataque mais perigoso").
- **Evidência fraca** (poucos/nenhum jogo, time fora desta Copa como a Itália) → uma
  inclinação mais cautelosa, apoiada no que existe ("histórico curto, mas nos confrontos
  o Brasil levou a melhor").

Sem percentual falso: a API não tem motor de probabilidade, então um "~58%" seria dígito
inventado. O agente raciocina sobre os dados reais e expressa o palpite como um analista
humano, sempre com qualificador de incerteza e nunca afirmando certeza. A lógica vive no
prompt (`AGENTS.md`), não em código — por isso é ajustável sem deploy.

**9. Orquestração: o agente conhece as 4 ferramentas e combina conforme a mensagem**
As ferramentas (head-to-head, matches, standings, top-scorers) são independentes e o
agente escolhe quais usar por mensagem — sem usar todas à força, sem se limitar a uma
quando mais agrega. Uma mensagem pode acionar várias numa só resposta: "Brasil x França,
e como tá o grupo deles?" retorna predição **e** standings do grupo no mesmo turn.
Perguntas diretas sobre jogador ("quantos gols o Mbappé fez?") usam top-scorers e
localizam o jogador no ranking, respondendo com graça se ele não estiver na lista.

**11. `.claude/agents/` — symlink que torna o agente resolvível pelo claude**
O genie omni-bridge faz spawn do agente por chat com `claude --agent world-cup-specialist`.
A partir do claude **2.1.191**, essa flag valida contra `.claude/agents/` (e `~/.claude/agents/`);
o mecanismo anterior — materializar o agente-líder do team via `--team-name/--agent-id` — foi
removido. `.claude/agents/world-cup-specialist.md` é um symlink para
`agents/world-cup-specialist/AGENTS.md`: mantém uma única fonte de verdade para o prompt e
garante que o claude resolve o agente a qualquer versão ≥ 2.1.191. Apagar esse arquivo faz o
spawn falhar silenciosamente (a janela tmux nasce e morre em zsh sem responder).

**10. Normalização de nomes de time na camada de serviço**
O agente traduz nomes para o inglês oficial da FIFA, mas é um LLM e às vezes envia a
grafia nativa ("França", "Coreia do Sul"). Como o filtro de `matches` é igualdade exata e
a busca de time espera inglês, `app/utils/team_names.py::normalize_team_name` é a rede
determinística: mapeia grafias PT/ES/FR comuns (sem acento, idempotente para inglês) e
devolve o original quando não conhece o alias. Só corrige ou não altera — nunca mapeia
para um time diferente, então não cria match errado. O prompt mantém só os poucos casos
clássicos como referência.

---

## Configuração

### Pré-requisitos

- Python 3.10+
- Docker (para o Redis)
- Genie CLI v4: instalado em `~/.local/bin/genie`
- Omni CLI v2: instalado em `~/.bun/bin/omni`
- Chave de API do [api-sports.io](https://api-sports.io) (obrigatória)
- Chave de API do [football-data.org](https://www.football-data.org) (obrigatória)

### Setup (uma vez)

```bash
make install
```

Verifica dependências, inicializa submódulos, cria o venv Python, instala pacotes
e gera o `.env`.

Após o script, preencha o `.env`:

```env
FOOTBALL_IO_SPORTS_API_KEY=sua_chave_api_sports_io
FOOTBALL_DATA_ORG_API_KEY=sua_chave_football_data_org
OMNI_API_KEY=sua_chave_omni          # omni config show
```

### Variáveis de ambiente

| Variável                      | Obrigatória | Descrição                                                          |
| ----------------------------- | ----------- | ------------------------------------------------------------------ |
| `FOOTBALL_IO_SPORTS_API_KEY`  | Sim         | Chave para api-sports.io (h2h e busca de time)                     |
| `FOOTBALL_DATA_ORG_API_KEY`   | Sim         | Chave para football-data.org (standings, matches, scorers)         |
| `OMNI_API_KEY`                | Sim         | Chave de autenticação do Omni (`omni config show`)                 |
| `OMNI_API_URL`                | Sim         | URL base do Omni (padrão: `http://localhost:8882`)                 |
| `API_BASE_URL`                | Sim         | URL da FastAPI usada pelo agente (padrão: `http://localhost:8000`) |
| `REDIS_HOST`                  | Sim         | Host do Redis (cache e memória em memória se ausente)              |
| `REDIS_PORT`                  | Sim         | Porta do Redis (padrão: `6379`)                                    |
| `REDIS_PASSWORD`              | Sim         | Senha do Redis (padrão: vazio para Redis local)                    |

---

## Execução

### Subir tudo (um comando)

```bash
make start
```

Idempotente. Sobe Redis (Docker), Omni, genie serve (+ omni-bridge) e FastAPI
(uvicorn) **e já conecta o agente ao Omni**. Rodar de novo não cria duplicatas —
cada etapa checa o estado antes de agir. Ao final imprime o `make status`.

> **WhatsApp ainda não conectado?** Na primeira vez (nenhuma instância Omni existente),
> `make start` cria automaticamente uma instância e exibe o QR code no terminal.
> Escaneie com o celular (WhatsApp → Dispositivos Vinculados → Vincular dispositivo)
> e rode `make start` novamente para confirmar a conexão.
>
> Se precisar rever o QR de uma instância existente:
> ```bash
> omni instances list          # obter <instance-id>
> omni instances qr <instance-id>
> ```

O agente responde **sob demanda**: quando chega uma mensagem no WhatsApp, o
`omni-bridge` faz spawn de um agente por-chat (`per_chat`) usando a mensagem como
prompt. Não é preciso manter um processo "master" ocioso.

### Conferir o estado

```bash
make status
```

Saúde de cada serviço, o agente conectado e avisos de acúmulo (registros Omni
antigos ou sessões órfãs).

### Limpar lixo acumulado (opcional)

```bash
make clean
```

Colapsa registros de agente Omni duplicados para 1 e encerra sessões órfãs.

### Sessão de debug (opcional)

```bash
make agent-spawn   # sessão manual do agente para inspeção
```

### Parar / reiniciar

```bash
make stop
make restart
```

### Atualizar as instruções do agente

O prompt do agente é o `AGENTS.md` — um único arquivo que contém o loop de turn
completo (Steps 1–4), persona e princípios. Como aplicar uma edição depende do que
mudou:

- **Mudou a FastAPI** (novo endpoint que o agente já chama): o agente faz `curl`
  em runtime a cada turn, então pega automático. Basta `make restart` (ou reiniciar
  a API). O chat atual usa na hora — sem reset.

- **Mudou as instruções** (`AGENTS.md`): uma conversa **nova** já nasce com o prompt
  atual. Mas um chat **já ativo** mantém o prompt velho. Para forçar o reload:

  ```bash
  make reload-agent   # genie dir sync + reset das sessões do bridge
  ```

  A próxima mensagem de cada chat spawna fresh e lê as instruções novas. A memória
  da conversa (Redis) **não** é apagada.

> `make sync-agent` faz só o `dir sync` (vale para conversas novas, sem mexer nas
> ativas). `make reload-agent` é o que aplica a mudança aos chats já em andamento.

---

## Referência de comandos

| Comando             | O que faz                                                          |
| ------------------- | ------------------------------------------------------------------ |
| `make install`      | Verifica deps, submódulos, cria venv, instala pacotes, gera `.env` |
| `make start`        | Sobe todos os serviços **e** conecta o agente (idempotente)        |
| `make status`       | Snapshot de saúde; sinaliza acúmulo                                |
| `make stop`         | Para todos os serviços + encerra sessões do agente                 |
| `make restart`      | `stop` + `start`                                                   |
| `make register`     | Só a conexão Genie ↔ Omni (idempotente; alias `make wire`)         |
| `make clean`        | Remove registros Omni duplicados + sessões órfãs (destrutivo)      |
| `make sync-agent`   | `genie dir sync` (instruções para conversas novas)                 |
| `make reload-agent` | Aplica instruções editadas a TODOS os chats (reset de sessão)      |
| `make agent-spawn`  | Sessão manual de debug (opcional)                                  |
| `make test`         | Roda a suite de testes                                             |

---

## Referência da API

Documentação interativa: `http://localhost:8000/docs`

### `GET /football/head-to-head`

Histórico de confrontos diretos entre dois times.

Query: `?name_team_a=Brazil&name_team_b=France`

```json
{
  "matchup": "Brazil vs France",
  "total_matches": 14,
  "historical_stats": {
    "team_a_wins": 6,
    "team_b_wins": 4,
    "draws": 4,
    "team_a_goals_scored": 18,
    "team_b_goals_scored": 14
  },
  "recent_encounters": [
    { "date": "2022-12-10", "competition": "FIFA World Cup", "score": "France 1 - 0 Brazil" }
  ]
}
```

### `GET /football/world-cup/standings`

Classificação por grupos da Copa 2026 (fonte: football-data.org).

```json
{
  "groups": [
    {
      "group": "A",
      "standings": [
        { "position": 1, "team": "Brazil", "played": 3, "won": 2, "draw": 1,
          "lost": 0, "goals_for": 5, "goals_against": 2, "goal_difference": 3, "points": 7 }
      ]
    }
  ]
}
```

### `GET /football/world-cup/matches`

Agenda, resultados e partidas ao vivo.

Query params (todos opcionais):

| Parâmetro   | Tipo           | Exemplo                 | Descrição                               |
| ----------- | -------------- | ----------------------- | --------------------------------------- |
| `teams`     | string (multi) | `?teams=Brazil`         | Filtra por nome de time (repetível)     |
| `date_from` | date           | `?date_from=2026-06-20` | Data inicial (deve vir com `date_to`)   |
| `date_to`   | date           | `?date_to=2026-06-20`   | Data final (deve vir com `date_from`)   |
| `status`    | enum           | `?status=IN_PLAY`       | `SCHEDULED`, `IN_PLAY`, `PAUSED`, `FINISHED` |

```json
{
  "matches": [
    { "utc_date": "2026-06-20T18:00:00Z", "home_team": "Brazil",
      "away_team": "France", "score": { "home": 2, "away": 1 },
      "status": "FINISHED", "stage": "Group Stage" }
  ]
}
```

### `GET /football/world-cup/top-scorers`

Artilheiros da Copa 2026.

```json
{
  "scorers": [
    { "position": 1, "player": "Vinicius Jr.", "team": "Brazil", "goals": 4, "assists": 2 }
  ]
}
```

### `GET /memory/{chat_id}`

Carrega o histórico de conversa de um chat.

```json
{
  "chat_id": "5511999999999@s.whatsapp.net",
  "last_teams": ["Brazil", "Argentina"],
  "preferred_language": "pt",
  "history": [
    { "role": "user", "text": "Brasil x Argentina quem ganha?", "ts": "2026-06-20T15:00:00" },
    { "role": "agent", "text": "Historicamente...", "ts": "2026-06-20T15:00:01" }
  ]
}
```

### `POST /memory/{chat_id}`

Salva um turno de conversa. Body JSON:

| Campo                | Tipo   | Obrigatório | Descrição                          |
| -------------------- | ------ | ----------- | ---------------------------------- |
| `user_msg`           | string | Sim         | Mensagem do usuário                |
| `agent_rep`          | string | Sim         | Resposta do agente                 |
| `team_a`             | string | Não         | Primeiro time (para `last_teams`)  |
| `team_b`             | string | Não         | Segundo time (para `last_teams`)   |
| `preferred_language` | string | Não         | Idioma detectado (`"pt"`, `"en"`)  |

---

## Testes

```bash
make test
# ou: python -m pytest -v tests/
```

Cobertura em 10 arquivos: serviço h2h, serviço world-cup, controller h2h,
controller world-cup, controller memory, rotas, integração api-sports.io,
integração football-data.org, middleware de correlation ID e sanitização de
headers. Todos os testes usam mocks — nenhuma chamada real à API externa.

---

## Observabilidade

A API emite logs JSON estruturado para stdout via [structlog](https://www.structlog.org/).
Cada linha de log inclui os campos `event`, `request_id`, `chat_id`, `timestamp`,
`level` e campos específicos do contexto (ex.: `provider`, `upstream_status`,
`latency_ms`, `attempt`).

### Variáveis de ambiente

| Variável     | Default | Descrição                                            |
| ------------ | ------- | ---------------------------------------------------- |
| `LOG_LEVEL`  | `INFO`  | Nível de log: `DEBUG`, `INFO`, `WARNING`, `ERROR`    |
| `LOG_FORMAT` | `json`  | `json` (produção) ou `console` (dev, human-readable) |

### Correlation ID

Todo request recebe um `request_id` (UUID4 gerado automaticamente ou lido do
header `X-Request-Id` se enviado). O agente pode enviar `X-Chat-Id` para ligar
o log da API ao chat WhatsApp correspondente. Ambos são propagados
automaticamente a todos os logs do request via contextvars.

- `X-Request-Id`: gerado se ausente; sempre ecoado no header de resposta.
- `X-Chat-Id`: opcional; enviado pelo agente para correlação ponta-a-ponta.

Ao final de cada request é emitida uma linha de log `request.completed` com
`method`, `path`, `status_code` e `latency_ms`.

### Segredos e sanitização

Nenhuma chave de API aparece nos logs. Os headers `x-rapidapi-key`,
`X-Auth-Token`, `Authorization` e `X-Api-Key` são substituídos por
`[REDACTED]` pela função `sanitize_headers` em `app/observability/logging_config.py`.

### Erros de autenticação

Quando a football-data.org retorna 401 ou 403, o log interno emite
`http.auth_error` com `detail: "invalid API key or plan insufficient"` —
útil para diagnosticar chave expirada ou plano insuficiente sem precisar
consultar a API. O status retornado ao usuário continua sendo 502.

---

## Arquivos do agente

| Arquivo                                       | Função                                                                   |
| --------------------------------------------- | ------------------------------------------------------------------------ |
| `agents/world-cup-specialist/AGENTS.md`       | Prompt completo: loop de turn (Steps 1–4), persona, princípios e constraints. Arquivo único, sem imports externos. |
| `agents/world-cup-specialist/agent.yaml`      | Config do Genie: `model: sonnet`, `promptMode: append`                   |
| `scripts/setup.sh`                            | Install idempotente (`make install`)                                     |
| `scripts/register-agent.sh`                   | Conexão Genie ↔ Omni idempotente (`make wire`)                           |
| `scripts/start-genie.sh`                      | Sobe genie serve + garante postgres (:5432)                              |
| `scripts/reload-agent.sh`                     | Reset de sessões (`make reload-agent`)                                   |
| `scripts/status.sh` · `stop.sh` · `clean.sh` | Ciclo de vida (`make status` / `stop` / `clean`)                         |
| `scripts/common.sh`                           | Helpers e probes compartilhados (portas, health checks)                  |
| `.claude/agents/world-cup-specialist.md`      | Symlink → `AGENTS.md`. Torna o agente resolvível por `claude --agent` (≥ 2.1.191). Não apagar. |

---

## Deploy

Consulte [DEPLOY.md](DEPLOY.md) para as opções de implantação: Oracle Cloud
Always Free (recomendado), VPS único, cloud+local separados e local+ngrok para
demos rápidas.
