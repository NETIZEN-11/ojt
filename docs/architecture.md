# Architecture Documentation

## System Overview

The Agent Red-Teaming & Evaluation Framework is a continuous assurance platform that evaluates AI/LLM agents against deterministic and adversarial test cases. The system follows a modular, layered architecture with clear separation of concerns.

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Frontend (Next.js)                       │
│  Dashboard │ Run Details │ Reviews │ Suites │ Baselines │ ...  │
└────────────────────────────┬────────────────────────────────────┘
                             │ REST API / WebSocket
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                      API Layer (FastAPI)                        │
│  Auth │ Agents │ Suites │ Runs │ Results │ Regressions │ ...  │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                   Application / Service Layer                   │
│  SuiteService │ ExecutionService │ ScoringService │ ...        │
└────────────────────────────┬────────────────────────────────────┘
                             │
              ┌──────────────┼──────────────┐
              ▼              ▼              ▼
       ┌─────────────┐ ┌─────────────┐ ┌─────────────┐
       │ PostgreSQL  │ │ Redis       │ │ ChromaDB    │
       │ (Primary DB)│ │ (Cache/Queue)│ │ (Vector DB) │
       └─────────────┘ └─────────────┘ └─────────────┘
              │              │              │
              └──────────────┼──────────────┘
                             ▼
                    ┌─────────────────┐
                    │ Object Storage  │
                    │ (S3/MinIO)      │
                    └─────────────────┘
```

## Component Details

### Frontend (Next.js 14)
- **App Router** for modern React patterns
- **TanStack Query** for server state management
- **Zustand** for client state
- **shadcn/ui** + Tailwind CSS for components
- **TypeScript** for type safety

### API Layer (FastAPI)
- **RESTful endpoints** under `/api/v1/`
- **JWT Authentication** with RS256
- **RBAC** with role-based permissions
- **Rate limiting** with Redis
- **OpenAPI/Swagger** documentation

### Application Services
- **SuiteService**: Test suite CRUD, validation, versioning
- **ExecutionService**: Target agent communication, retries
- **ScoringService**: Deterministic matchers + LLM judges
- **RegressionService**: Baseline comparison, diffing
- **SeverityService**: Deterministic + LLM-assisted classification
- **GateService**: CI gate logic (PASS/WARN/BLOCK/FAIL)
- **ReviewService**: Human review queue management
- **BaselineService**: Approval workflow, versioning

### Evaluation Engine
- **Matchers**: Exact, Regex, Keyword, Refusal (deterministic)
- **Judges**: LLM-based evaluation with structured output validation
- **Regression Detector**: Deterministic baseline comparison
- **Severity Classifier**: Rule-based with critical overrides
- **Gate Evaluator**: Deterministic CI decision logic
- **RedTeam Agent**: LangGraph bounded state machine

### Data Layer
- **PostgreSQL**: Primary relational database with full ACID
- **Redis**: Caching, rate limiting, Celery broker
- **ChromaDB**: Vector embeddings for RAG and novelty filtering
- **S3/MinIO**: Object storage for transcripts, reports, artifacts

### Background Processing (Celery)
- **Evaluation Workers**: Long-running test execution
- **RedTeam Workers**: Adversarial generation, multi-turn attacks
- **Maintenance Workers**: Cleanup, health checks, cost monitoring

## Key Design Principles

### Deterministic First
- All safety-critical logic uses deterministic code
- LLMs only used where deterministic logic is insufficient
- Structured output validation for all LLM calls

### Fail-Closed Security
- Missing baselines, judge disagreements, infrastructure failures → FAIL/BLOCK
- Never silently convert errors to PASS

### Modularity & Extensibility
- Provider pattern for LLMs, embeddings, target agents, storage
- Feature flags for experimental functionality
- Independent versioning of suites, prompts, models, baselines

### Observability
- Structured logs with correlation IDs
- Prometheus metrics for all critical paths
- OpenTelemetry distributed tracing
- Alerting on critical findings, gate failures, SLA breaches

## Data Flow

### Test Execution Flow
```
1. API: POST /runs → Creates Run (QUEUED)
2. Queue: Celery task → run_evaluation
3. ExecutionService: Parallel test execution
   ├─ Call target agent (with retries/circuit breaker)
   ├─ Capture response + tool calls
   └─ Store Execution record
4. ScoringService: Per-test scoring
   ├─ Try deterministic matchers first
   ├─ Fall back to LLM judge with rubric
   ├─ Double-score with fallback judge
   └─ Store Result record
5. RegressionDetector: Compare with baseline
6. SeverityClassifier: Classify findings
7. GateEvaluator: Final CI decision
8. ReviewQueue: Create review items for BLOCK/FAIL
9. Results stored, metrics emitted
```

### Adversarial Generation Flow
```
1. Generator: LLM + taxonomy + previous failures
2. Embedding: Vector embeddings for each candidate
3. Novelty Filter: ChromaDB similarity search
4. Accept/Reject: Threshold-based filtering
5. Store: Accepted candidates → test suite (pending review)
```

## Security Considerations

- **SSRF Protection**: Target agent URL allowlisting, private IP blocking
- **PII Redaction**: Automatic detection and redaction before storage
- **Audit Logging**: All security-relevant actions logged immutably
- **Secrets Management**: Environment variables + secret files, never in code
- **RBAC**: Fine-grained permissions per resource and action
- **Rate Limiting**: Per-endpoint and global limits
- **CORS**: Configured allowlist only

## Deployment Architecture

### Development
- Docker Compose with all services
- Hot reload for frontend and backend
- Mock providers for LLM/target agents

### Staging
- Kubernetes namespace
- Canary deployments
- Full integration test suite

### Production
- Multi-replica deployments
- Horizontal pod autoscaling
- Blue/green or canary deployments
- Comprehensive monitoring and alerting
- Automated rollback on metric degradation