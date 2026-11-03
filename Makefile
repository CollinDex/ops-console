ARGS ?=

.PHONY: dev db api-install web-install install lint fmt test web-check web-test migrate seed

dev:
	docker compose up --build

db:
	docker compose up -d db

api-install:
	cd api && uv sync

web-install:
	cd web && pnpm install

install: api-install web-install
	uvx pre-commit install

lint:
	cd api && uv run ruff check . && uv run ruff format --check . && uv run mypy app
	cd web && pnpm lint && pnpm format:check

fmt:
	cd api && uv run ruff format . && uv run ruff check --fix .
	cd web && pnpm format

test:
	cd api && uv run pytest

web-check:
	cd web && pnpm typecheck && pnpm build

migrate:
	cd api && uv run alembic upgrade head

seed:
	cd api && uv run python -m scripts.seed $(ARGS)

web-test:
	cd web && pnpm test
