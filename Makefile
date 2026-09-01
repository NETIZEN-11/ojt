.PHONY: help install dev test lint typecheck build docker-build docker-up docker-down clean migrate seed benchmark

# Default target
help:
	@echo "Agent Red-Teaming Framework - Make Commands"
	@echo ""
	@echo "Setup:"
	@echo "  install       Install all dependencies"
	@echo "  dev           Start development environment"
	@echo ""
	@echo "Database:"
	@echo "  migrate       Run database migrations"
	@echo "  seed          Seed development data"
	@echo ""
	@echo "Testing:"
	@echo "  test          Run all tests"
	@echo "  test-unit     Run unit tests"
	@echo "  test-integration  Run integration tests"
	@echo "  test-api      Run API tests"
	@echo "  test-evaluation  Run evaluation tests"
	@echo "  test-security Run security tests"
	@echo "  test-regression Run regression tests"
	@echo "  benchmark     Run seeded regression benchmark"
	@echo ""
	@echo "Code Quality:"
	@echo "  lint          Run linters (ruff, eslint)"
	@echo "  typecheck     Run type checkers (mypy, tsc)"
	@echo "  format        Format code (ruff, prettier)"
	@echo ""
	@echo "Building:"
	@echo "  build         Build all containers"
	@echo "  build-backend Build backend container"
	@echo "  build-frontend Build frontend container"
	@echo ""
	@echo "Docker:"
	@echo "  docker-up     Start all services with docker-compose"
	@echo "  docker-down   Stop all services"
	@echo "  docker-logs   View docker logs"
	@echo ""
	@echo "Utilities:"
	@echo "  clean         Clean build artifacts"
	@echo "  verify        Verify environment setup"
	@echo "  health        Run health checks"

# Installation
install:
	cd backend && pip install -e ".[dev]"
	cd frontend && npm ci

# Development
dev:
	docker-compose -f docker-compose.dev.yml up -d
	@echo "Waiting for services..."
	@sleep 10
	cd backend && source .venv/bin/activate && uvicorn app.main:app --reload &
	cd frontend && npm run dev

# Database
migrate:
	cd backend && source .venv/bin/activate && alembic upgrade head

seed:
	cd backend && source .venv/bin/activate && python ../scripts/seed_demo_data.py

# Testing
test: test-unit test-integration test-api test-evaluation test-security test-regression

test-unit:
	cd backend && source .venv/bin/activate && pytest tests/unit -v --tb=short

test-integration:
	cd backend && source .venv/bin/activate && pytest tests/integration -v --tb=short

test-api:
	cd backend && source .venv/bin/activate && pytest tests/api -v --tb=short

test-evaluation:
	cd backend && source .venv/bin/activate && pytest tests/evaluation -v --tb=short

test-security:
	cd backend && source .venv/bin/activate && pytest tests/security -v --tb=short

test-regression:
	cd backend && source .venv/bin/activate && pytest tests/regression -v --tb=short

test-frontend:
	cd frontend && npm test -- --coverage

benchmark:
	cd backend && source .venv/bin/activate && python ../scripts/run_seeded_regression.py

# Code Quality
lint:
	cd backend && source .venv/bin/activate && ruff check .
	cd frontend && npm run lint

typecheck:
	cd backend && source .venv/bin/activate && mypy app
	cd frontend && npm run typecheck

format:
	cd backend && source .venv/bin/activate && ruff check --fix . && ruff format .
	cd frontend && npm run format

# Building
build: build-backend build-frontend

build-backend:
	docker build -t redteam-backend:latest ./backend

build-frontend:
	docker build -t redteam-frontend:latest ./frontend

# Docker
docker-up:
	docker-compose -f docker-compose.dev.yml up -d

docker-down:
	docker-compose -f docker-compose.dev.yml down -v

docker-logs:
	docker-compose -f docker-compose.dev.yml logs -f

# Utilities
clean:
	rm -rf backend/.venv backend/__pycache__ backend/.pytest_cache backend/.mypy_cache backend/.ruff_cache backend/htmlcov backend/coverage.xml
	rm -rf frontend/node_modules frontend/.next frontend/out frontend/build frontend/.turbo
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true

verify:
	python scripts/verify_environment.py

health:
	python scripts/health_check.py

# Evaluation
eval:
	cd backend && source .venv/bin/activate && python ../scripts/run_evaluation.py --agent "$(AGENT)" --suite "$(SUITE)" --baseline "$(BASELINE)"

# Security
security-scan:
	cd backend && source .venv/bin/activate && bandit -r app -f json -o bandit-report.json
	cd backend && source .venv/bin/activate && pip-audit --format=json --output=pip-audit-report.json
	cd frontend && npm audit --json > npm-audit-report.json