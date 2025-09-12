.PHONY: all build run stop clean logs dev restart status local format lint check

all: check local

build:
	docker compose build

run:
	docker compose up -d

stop:
	docker compose down

clean:
	docker compose down -v
	docker system prune -f

logs:
	docker compose logs -f

dev:
	docker compose up

restart: stop run logs

status:
	docker compose ps

local: build run
	@echo "Jukebox running at http://localhost:5000"

format:
	uv run ruff format .

lint:
	uv run ruff check .

check: lint format
	@echo "Code formatting and linting complete"