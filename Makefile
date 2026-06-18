.PHONY: help install install-frontend install-backend dev dev-frontend dev-backend start-frontend db-up db-up-admin db-down db-logs db-psql lint lint-frontend lint-backend typecheck typecheck-frontend typecheck-backend test test-backend format format-check build build-frontend db-check alembic-current validate

NPM ?= npm.cmd
UV ?= uv
DOCKER_COMPOSE ?= docker compose

help:
	@echo Comandos disponibles:
	@echo   make install            Instala dependencias frontend y backend
	@echo   make dev                Levanta PostgreSQL, backend y frontend
	@echo   make dev-frontend       Levanta Next.js en http://localhost:3000
	@echo   make dev-backend        Levanta FastAPI en http://localhost:8000
	@echo   make start-frontend     Sirve el frontend compilado
	@echo   make db-up              Levanta PostgreSQL
	@echo   make db-up-admin        Levanta PostgreSQL y pgAdmin
	@echo   make db-down            Detiene los servicios Docker
	@echo   make db-logs            Muestra logs de PostgreSQL
	@echo   make db-psql            Abre psql dentro del contenedor
	@echo   make db-check           Valida conexion real a PostgreSQL
	@echo   make alembic-current    Verifica el estado actual de Alembic
	@echo   make lint               Ejecuta lint frontend y backend
	@echo   make typecheck          Ejecuta typecheck frontend y backend
	@echo   make test               Ejecuta pruebas disponibles
	@echo   make format             Formatea frontend y backend
	@echo   make format-check       Verifica formato frontend y backend
	@echo   make build              Compila el frontend
	@echo   make validate           Ejecuta validacion base completa

install: install-frontend install-backend

install-frontend:
	$(NPM) install

install-backend:
	cd backend && $(UV) sync --python 3.11

dev: db-up
	$(MAKE) -j2 dev-backend dev-frontend

dev-frontend:
	$(NPM) --workspace frontend run dev

dev-backend:
	cd backend && $(UV) run python -m src.dev_server

start-frontend:
	$(NPM) --workspace frontend run start

db-up:
	$(DOCKER_COMPOSE) up -d postgres

db-up-admin:
	$(DOCKER_COMPOSE) up -d postgres pgadmin

db-down:
	$(DOCKER_COMPOSE) down

db-logs:
	$(DOCKER_COMPOSE) logs -f postgres

db-psql:
	$(DOCKER_COMPOSE) exec postgres psql -U postgres -d sena_guias_db

lint: lint-frontend lint-backend

lint-frontend:
	$(NPM) --workspace frontend run lint

lint-backend:
	cd backend && $(UV) run ruff check .

typecheck: typecheck-frontend typecheck-backend

typecheck-frontend:
	$(NPM) --workspace frontend run typecheck

typecheck-backend:
	cd backend && $(UV) run mypy src

test: test-backend

test-backend:
	cd backend && $(UV) run pytest

format:
	$(NPM) --workspace frontend run format
	cd backend && $(UV) run ruff format .

format-check:
	$(NPM) --workspace frontend run format:check
	cd backend && $(UV) run ruff format --check .

build: build-frontend

build-frontend:
	$(NPM) --workspace frontend run build

db-check:
	cd backend && $(UV) run python scripts/check_database_connection.py

alembic-current:
	cd backend && $(UV) run alembic current

validate: lint typecheck test format-check build alembic-current
