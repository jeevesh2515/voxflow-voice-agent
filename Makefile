.PHONY: help install api-install web-install seed dev-api dev-web dev docker-up docker-down clean

help:
	@echo "VoxFlow Voice Agent — common commands"
	@echo ""
	@echo "  make install      Install all deps (api + web)"
	@echo "  make seed         Seed demo data into the SQLite DB"
	@echo "  make dev-api      Run the FastAPI server (port 8000)"
	@echo "  make dev-web      Run the Next.js dashboard (port 3000)"
	@echo "  make docker-up    Bring up the full stack via docker-compose"
	@echo "  make docker-down  Tear it down"
	@echo "  make clean        Remove venv, node_modules, .db files"

install: api-install web-install

api-install:
	cd apps/api && python3.12 -m venv .venv && . .venv/bin/activate && pip install -U pip && pip install -r requirements.txt

web-install:
	cd apps/web && npm install

seed:
	cd apps/api && . .venv/bin/activate && python -m voxflow_api.seed

dev-api:
	cd apps/api && . .venv/bin/activate && uvicorn voxflow_api.main:app --reload --port 8000

dev-web:
	cd apps/web && npm run dev

docker-up:
	docker compose up --build

docker-down:
	docker compose down

clean:
	rm -rf apps/api/.venv apps/web/node_modules apps/web/.next
	find . -name "*.db" -not -path "*/node_modules/*" -not -path "*/.venv/*" -delete
