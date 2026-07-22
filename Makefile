.PHONY: up down test lint typecheck migrate

up:
	cp -n .env.example .env || true
	docker compose up --build

down:
	docker compose down

test:
	pytest

lint:
	ruff check .

typecheck:
	mypy src

migrate:
	alembic upgrade head
