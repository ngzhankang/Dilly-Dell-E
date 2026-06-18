TAG ?= latest

.PHONY: init dev build lint \
        docker-up docker-down \
        build-images push-images \
        k8s-apply k8s-down \
        ml-dev help

# ── Help ───────────────────────────────────────────────────────────────

help:
	@echo "Usage:"
	@echo "  make init           Scaffold backend + prompt for frontend (run once)"
	@echo "  make dev            Start backend + frontend dev server"
	@echo "  make build          Production build (backend)"
	@echo "  make lint           TypeScript type-check (backend)"
	@echo ""
	@echo "  make docker-up      Start Mongo + Redis + ML service"
	@echo "  make docker-down    Stop all Docker services"
	@echo ""
	@echo "  make build-images   Build Docker images for backend + ml-service"
	@echo "  make push-images    Tag and push images to \$$REGISTRY:\$$TAG"
	@echo ""
	@echo "  make k8s-apply      Apply all Kubernetes manifests"
	@echo "  make k8s-down       Delete all Kubernetes resources"
	@echo ""
	@echo "  make ml-dev         Run ML service locally with uvicorn (hot reload)"

# ── Setup ──────────────────────────────────────────────────────────────

init:
	@bash scripts/init.sh

# ── Local dev ──────────────────────────────────────────────────────────

dev:
	@if [ -d mobile ]; then \
		cd mobile && npx expo start & \
	elif [ -d frontend ]; then \
		cd frontend && npm run dev & \
	else \
		echo "No frontend scaffolded — run: make init"; \
	fi
	@cd backend && npm run dev

build:
	@cd backend && npm run build

lint:
	@cd backend && npm run lint

# ── Docker Compose ─────────────────────────────────────────────────────

docker-up:
	@docker compose up -d

docker-down:
	@docker compose down

# ── Docker image build / push ──────────────────────────────────────────

build-images:
	docker build -t dilly-dell-e/backend:$(TAG) ./backend
	docker build -t dilly-dell-e/ml-service:$(TAG) ./ml

push-images:
	docker tag dilly-dell-e/backend:$(TAG) $(REGISTRY)/backend:$(TAG)
	docker push $(REGISTRY)/backend:$(TAG)
	docker tag dilly-dell-e/ml-service:$(TAG) $(REGISTRY)/ml-service:$(TAG)
	docker push $(REGISTRY)/ml-service:$(TAG)

# ── Kubernetes ─────────────────────────────────────────────────────────

k8s-apply:
	kubectl apply -f k8s/namespace.yaml
	kubectl apply -f k8s/ollama/
	kubectl apply -f k8s/ml-service/
	kubectl apply -f k8s/backend/

k8s-down:
	kubectl delete -f k8s/backend/ --ignore-not-found
	kubectl delete -f k8s/ml-service/ --ignore-not-found
	kubectl delete -f k8s/ollama/ --ignore-not-found
	kubectl delete -f k8s/namespace.yaml --ignore-not-found

# ── ML service (local Python, no Docker) ──────────────────────────────

ml-dev:
	@if [ "$(OS)" = "Windows_NT" ]; then \
		choco install ffmpeg; \
		cd ml && .venv/Scripts/uvicorn app.main:app --reload --port 8000; \
	elif [ "$$(uname)" = "Darwin" ]; then \
		brew install ffmpeg; \
		cd ml && .venv/bin/uvicorn app.main:app --reload --port 8000; \
	else \
		sudo apt update && sudo apt install ffmpeg -y; \
		cd ml && .venv/bin/uvicorn app.main:app --reload --port 8000; \
	fi
