.PHONY: help setup lint type test check app migrate

help:
	@echo "setup    - uv sync (install deps + dev extras)"
	@echo "lint     - ruff check"
	@echo "type     - mypy"
	@echo "test     - pytest"
	@echo "check    - lint + type + test"
	@echo "migrate  - apply DB migrations (marc db migrate)"
	@echo "app      - run the Streamlit app"

setup:
	uv sync --extra dev

lint:
	uv run ruff check src tests app

type:
	uv run mypy

test:
	uv run pytest

check: lint type test

migrate:
	uv run marc db migrate

app:
	uv run streamlit run app/Home.py
