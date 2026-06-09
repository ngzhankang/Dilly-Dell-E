.PHONY: init dev build lint docker-up docker-down help

help:
	@echo "Usage:"
	@echo "  make init        Scaffold frontend and backend (run once after cloning)"
	@echo "  make dev         Start frontend and backend in development mode"
	@echo "  make build       Build frontend and backend"
	@echo "  make lint        Lint frontend and backend"
	@echo "  make docker-up   Start Docker services (MongoDB, Redis)"
	@echo "  make docker-down Stop Docker services"

init:
	@bash scripts/init.sh

dev:
	@cd frontend && npm run dev & cd backend && npm run dev

build:
	@cd frontend && npm run build
	@cd backend && npm run build

lint:
	@cd frontend && npm run lint
	@cd backend && npm run lint

docker-up:
	@docker compose up -d

docker-down:
	@docker compose down
