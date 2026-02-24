# Makefile

.PHONY: install test clean

# Instala a biblioteca em modo de desenvolvimento (editável) com todas as dependências
# Installs the library in development (editable) mode with all dependencies
install:
	pip install -e .[pandas,s3,azure,gcs]

# Executa os testes unitários da pasta tests/
# Runs the unit tests from the tests/ folder
test:
	pytest tests/ -v

# Limpa o repositório removendo pastas de build e cache do Python
# Cleans the repository by removing build and Python cache folders
clean:
	rm -rf dist/ build/ *.egg-info src/*/*.egg-info
	find . -type d -name __pycache__ -exec rm -rf {} +