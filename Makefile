.PHONY: format lint all

# Alvo para formatar o código (reescreve os arquivos respeitando o padrão)
format:
	@echo "Formatando o código com Black..."
	black .

# Alvo para lint/verificação (apenas checa se há violações, sem alterar - ideal para CI)
lint:
	@echo "Verificando formatação com Black..."
	black --check .

# Alvo que executa os dois em sequência
all: format lint