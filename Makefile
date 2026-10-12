# Development commands. `make check` runs what CI runs on a pull request.
.PHONY: help install check plugin-check cli-check

help: ## List the targets
	@grep -E '^[a-z-]+:.*## ' $(MAKEFILE_LIST) | awk -F':.*## ' '{printf "  %-14s %s\n", $$1, $$2}'

install: ## Create the development environment of every package
	cd cli && poetry install

check: plugin-check cli-check ## Run every check

plugin-check: ## Validate the plugin and marketplace, check versions and PyPI names
	python3 -m unittest discover -s .github/scripts -p 'test_*.py'
	python3 .github/scripts/check_release_version.py
	python3 .github/scripts/check_pypi_names.py
	claude plugin validate --strict plugin
	claude plugin validate --strict .
	sh plugin/evals/stub/test_stub.sh
	sh plugin/hooks/test_fde_hook.sh

cli-check: ## Lint, type-check and test the CLI
	cd cli && poetry run ruff check . && poetry run ruff format --check . && poetry run mypy && poetry run pytest

