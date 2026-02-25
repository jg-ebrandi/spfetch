# Makefile

.PHONY: install install-all test clean clean-data build publish

# Instala a biblioteca em modo de desenvolvimento (editável) com as dependências base
# Installs the library in development (editable) mode with base dependencies
install:
	pip install -e .

# Instala a biblioteca com TODAS as dependências opcionais (Nuvem e Pandas)
# Installs the library with ALL optional dependencies (Cloud and Pandas)
install-all:
	pip install -e ".[pandas,s3,azure,gcs]"

# Executa os testes unitários oficiais da pasta tests/
# Runs the official unit tests from the tests/ folder
test:
	pytest tests/ -v

# Limpa o repositório removendo pastas de build e cache do Python
# Cleans the repository by removing build and Python cache folders
clean:
	rm -rf dist/ build/ *.egg-info src/*/*.egg-info
	find . -type d -name __pycache__ -exec rm -rf {} +

# Limpa os arquivos baixados localmente durante os testes manuais na raiz
# Cleans locally downloaded files during manual tests in the root
clean-data:
	rm -f *.xlsx *.csv *.xls

# Gera os arquivos de distribuição (.tar.gz e .whl) para o PyPI
# Generates the distribution files (.tar.gz and .whl) for PyPI
build: clean
	python -m build

# Faz o upload da versão buildada para o PyPI (requer twine)
# Uploads the built version to PyPI (requires twine)
publish: build
	twine upload dist/*