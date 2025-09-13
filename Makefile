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

local: build
	HOST_IP=$(shell ip route get 1.1.1.1 | grep -oP 'src \K\S+') docker compose up -d
	@echo "Jukebox running at http://localhost:5000"
	@echo "Network access: http://$(shell ip route get 1.1.1.1 | grep -oP 'src \K\S+'):5000"

format:
	uv run ruff format .

lint:
	uv run ruff check .

check: lint format
	@echo "Code formatting and linting complete"

# Termux/Android commands
termux-setup:
	bash scripts/setup_termux.sh

termux-boot:
	bash scripts/setup_boot.sh

termux-start:
	bash scripts/start_termux.sh

termux-all: termux-setup termux-boot termux-start