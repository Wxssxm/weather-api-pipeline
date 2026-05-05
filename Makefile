.PHONY: help install run test test-unit lint format clean docker-up docker-down logs migrate ingest seed

help:
	@echo "Available targets:"
	@echo "  install        Create venv and install package with dev extras"
	@echo "  docker-up      Start postgres + grafana + scheduler"
	@echo "  docker-down    Stop and remove all containers + volumes"
	@echo "  logs           Tail scheduler logs"
	@echo "  migrate        Apply Alembic migrations to the configured DB"
	@echo "  seed           Insert the 10 default cities"
	@echo "  ingest         Run a one-shot ingestion across all cities"
	@echo "  test           Run all tests with coverage"
	@echo "  test-unit      Skip integration tests (no Postgres needed)"
	@echo "  lint           ruff + black checks"
	@echo "  format         Auto-fix lint and format"
	@echo "  clean          Remove venv and caches"

install:
	uv venv --python 3.11
	uv pip install -e ".[dev]"

docker-up:
	docker compose up -d --build

docker-down:
	docker compose down -v

logs:
	docker compose logs -f scheduler

migrate:
	uv run alembic upgrade head

seed:
	uv run weather seed-cities

ingest:
	uv run weather ingest-once

test:
	uv run pytest -m "not integration" --cov=src/weather_pipeline --cov-report=term-missing --cov-fail-under=70

test-unit:
	uv run pytest -m "not integration" -v

lint:
	uv run ruff check .
	uv run black --check .

format:
	uv run ruff check --fix .
	uv run black .

clean:
	rm -rf .venv __pycache__ .pytest_cache .ruff_cache .coverage htmlcov dist build
	find . -type d -name __pycache__ -exec rm -rf {} +
