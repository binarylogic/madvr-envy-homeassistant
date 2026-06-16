.PHONY: install lock test test-cov test-fast lint format format-check clean check

VENV_PYTHON := .venv/bin/python
RUFF := .venv/bin/ruff
PYTEST := .venv/bin/pytest
MADVR_ENVY_LIB_PATH ?= ../py-madvr-envy
UV_CACHE_DIR ?= .uv-cache

install:
	UV_CACHE_DIR=$(UV_CACHE_DIR) uv sync --locked --no-sources
	@if [ -d "$(MADVR_ENVY_LIB_PATH)" ]; then \
		UV_CACHE_DIR=$(UV_CACHE_DIR) uv pip install -p $(VENV_PYTHON) -e $(MADVR_ENVY_LIB_PATH); \
	fi

lock:
	UV_CACHE_DIR=$(UV_CACHE_DIR) uv lock --no-sources

test:
	$(PYTEST)

test-cov:
	$(PYTEST) --cov-report=term-missing --cov-report=xml

test-fast:
	$(PYTEST) --no-cov

lint:
	$(RUFF) check custom_components tests

format:
	$(RUFF) format custom_components tests

format-check:
	$(RUFF) format --check custom_components tests

clean:
	rm -rf .pytest_cache
	rm -rf .coverage
	rm -rf coverage.xml
	rm -rf htmlcov
	rm -rf .ruff_cache
	rm -rf .uv-cache
	rm -rf .venv
	rm -rf madvr_envy.zip

check:
	@make lint
	@make format-check
	@make test
