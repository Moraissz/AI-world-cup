.PHONY: format lint all setup test start start-omni start-api start-genie stop agent-spawn

setup:
	bash setup.sh

test:
	.venv/bin/pytest -v tests/

format:
	@echo "Formatando o código com Black..."
	black .

lint:
	@echo "Verificando formatação com Black..."
	black --check .

all: format lint

start-omni:
	~/.bun/bin/omni start

start-api:
	.venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000 &

start-genie:
	@~/.autopg/bin/linux-x64/bin/pg_ctl -D ~/.autopg/data -l ~/.autopg/logs/autopg-server-out.log start 2>/dev/null || true
	@~/.local/bin/genie serve start --headless --daemon 2>/dev/null || true

start: start-omni start-genie start-api
	@echo "Services started. FastAPI: http://localhost:8000/docs | Omni: http://localhost:8882"

stop:
	-~/.bun/bin/omni stop 2>/dev/null || true
	-pkill -f "uvicorn main:app" 2>/dev/null || true
	-~/.local/bin/genie serve stop 2>/dev/null || true
	-~/.autopg/bin/linux-x64/bin/pg_ctl -D ~/.autopg/data stop 2>/dev/null || true

agent-spawn:
	~/.local/bin/genie spawn world-cup-specialist