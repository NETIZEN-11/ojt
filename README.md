# Agent Red-Teaming & Evaluation Framework

A continuous-assurance platform that evaluates AI/LLM agents against deterministic and adversarial test cases, detects safety/behavioral regressions against approved historical baselines, classifies severity, produces evidence-rich reports, routes uncertain findings to human reviewers, and provides a deterministic CI gate capable of blocking a merge/deployment.

## Architecture

```
Frontend (Next.js/React) → API Layer (FastAPI) → Application/Services → Domain/Evaluation Engine → Repositories/Adapters → PostgreSQL/Redis/Vector DB/Object Storage
                                    ↓
                              Task Queue (Celery) → Workers → Evaluation Pipeline → Database + Object Storage
```

## Features

- **Test Suite Engine**: YAML/JSON test suites with schema validation, versioning, deterministic matchers
- **Scoring Engine**: Deterministic matchers (exact, regex, keyword, refusal) + LLM Judge with structured output validation
- **Regression Detection**: Deterministic comparison against approved baselines
- **Severity Classification**: Deterministic rules with LLM-assisted rationale
- **CI Gate**: Deterministic PASS/WARN/BLOCK/FAIL with machine-readable output
- **Adversarial Generator**: Taxonomy-grounded, novelty-filtered test generation
- **Red-Team Agent**: Bounded LangGraph state machine with turn caps
- **Human Review Queue**: Priority-sorted queue with evidence viewer and audit trail
- **Baseline Management**: Explicit human approval with immutable history
- **Full Observability**: Structured logs, Prometheus metrics, OpenTelemetry tracing

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 20+
- PostgreSQL 15+
- Redis 7+
- Docker & Docker Compose (optional)

### Local Development

```bash
# Clone and enter project
cd agent-redteam-framework

# Copy environment template
cp .env.example .env

# Start infrastructure
docker-compose -f docker-compose.dev.yml up -d

# Backend setup
cd backend
pip install -e .
alembic upgrade head
python -m app.main

# Frontend setup (new terminal)
cd frontend
npm install
npm run dev
```

### Running Tests

```bash
# Backend tests
cd backend
pytest -xvs

# Frontend tests
cd frontend
npm test

# Seeded regression benchmark
python scripts/run_seeded_regression.py
```

### Docker Production

```bash
docker-compose -f docker-compose.prod.yml up -d
```

## Configuration

See `.env.example` for all configuration options.

Key settings:
- `DATABASE_URL`: PostgreSQL connection string
- `REDIS_URL`: Redis connection string
- `LLM_PROVIDER`: Primary LLM provider (openai, anthropic, etc.)
- `JUDGE_MODEL`: Model for evaluation judging
- `EVAL_MODE`: `local` (mock) or `production` (real providers)

## API Documentation

Start the backend and visit:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
- OpenAPI JSON: http://localhost:8000/openapi.json

## CI/CD

GitHub Actions workflows in `.github/workflows/`:
- `ci.yml`: Full CI pipeline
- `regression-gate.yml`: Seeded regression benchmark gate
- `deploy.yml`: Production deployment

## Project Structure

```
agent-redteam-framework/
├── backend/                 # FastAPI application
│   ├── app/
│   │   ├── core/           # Config, security, logging, telemetry
│   │   ├── api/v1/         # REST API endpoints
│   │   ├── domain/         # Domain entities, enums, policies
│   │   ├── schemas/        # Pydantic request/response models
│   │   ├── models/         # SQLAlchemy ORM models
│   │   ├── repositories/   # Data access layer
│   │   ├── services/       # Business logic services
│   │   ├── evaluation/     # Scoring, regression, severity, gate
│   │   ├── redteam/        # Adversarial generation, red-team agent
│   │   ├── rag/            # Embeddings, retrieval, vector store
│   │   ├── providers/      # LLM, embedding, target agent adapters
│   │   ├── prompts/        # Versioned prompt templates
│   │   └── workers/        # Celery background tasks
│   ├── migrations/         # Alembic database migrations
│   └── tests/              # Test suite
├── frontend/               # Next.js application
│   └── src/
│       ├── app/            # App Router pages
│       ├── components/     # Shared UI components
│       ├── features/       # Feature-specific components
│       ├── hooks/          # Custom React hooks
│       ├── lib/            # API client, auth, utilities
│       └── types/          # TypeScript types
├── evaluation/             # Test suites, benchmarks, taxonomy
├── infra/                  # Docker, K8s, monitoring configs
├── scripts/                # Operational scripts
└── security/               # Threat model, security checklist
```

## License

MIT License - see LICENSE file for details.