# AI World Cup - Football Prediction Agent

## Endpoints

- `GET /football/head-to-head?name_team_a=Brazil&name_team_b=France`
- `POST /football/predict`

Exemplo de payload de previsão:

```json
{
  "team_a": "Brazil",
  "team_b": "France"
}
```

## Setup

1. Crie e ative o ambiente virtual:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

2. Instale as dependências:

```bash
pip install -r requirements.txt
```

3. Configure a variável de ambiente:

```bash
cp .env.example .env
export FOOTBALL_API_KEY=your_football_api_key_here
```

4. Execute a aplicação:

```bash
uvicorn main:app --reload
```

## Como usar

- Abra `http://localhost:8000/docs` docs.
- Chame `GET /football/head-to-head` para consultar histórico direto.
- Chame `POST /football/predict` para obter previsão e razões.

## Testes

```bash
python -m pytest -q tests/test_head_to_head_analyzer.py tests/test_match_prediction_service.py
```

## Próximos passos para o teste

- Adicionar webhook Omni para receber mensagens WhatsApp
- Integrar orquestração Genie/Claude para processar o diálogo
- Implementar memória de conversa local ou banco de dados
- Criar adaptador de ferramenta para expor a API ao agente
