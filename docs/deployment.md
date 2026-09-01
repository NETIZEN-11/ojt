# Deployment Guide

## Prerequisites

- Docker & Docker Compose (v2+)
- Kubernetes cluster (for production)
- PostgreSQL 15+
- Redis 7+
- ChromaDB 0.4+
- S3-compatible object storage (MinIO, AWS S3, etc.)
- Domain with TLS certificates (for production)

## Environment Variables

Create `.env` from `.env.example` and configure:

### Required for All Environments
```bash
# Database
DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/redteam

# Redis
REDIS_URL=redis://host:6379/0

# Security
SECRET_KEY=your-32-char-min-secret-key
JWT_PRIVATE_KEY_PATH=/path/to/private.pem
JWT_PUBLIC_KEY_PATH=/path/to/public.pem

# Object Storage
S3_ENDPOINT_URL=https://s3.example.com
S3_ACCESS_KEY=your-access-key
S3_SECRET_KEY=your-secret-key
S3_BUCKET=redteam-artifacts
```

### LLM Providers (Production)
```bash
# Primary Judge
PRIMARY_JUDGE_PROVIDER=openai
PRIMARY_JUDGE_MODEL=gpt-4o-2024-08-06
PRIMARY_JUDGE_API_KEY=sk-...

# Secondary Judge
SECONDARY_JUDGE_PROVIDER=anthropic
SECONDARY_JUDGE_MODEL=claude-3-5-sonnet-20241022
SECONDARY_JUDGE_API_KEY=sk-...

# Generator
GENERATOR_PROVIDER=openai
GENERATOR_MODEL=gpt-4o-2024-08-06
GENERATOR_API_KEY=sk-...

# Embeddings
EMBEDDING_PROVIDER=openai
EMBEDDING_MODEL=text-embedding-3-large
EMBEDDING_API_KEY=sk-...
```

### Development Overrides
```bash
EVAL_MODE=local
DEV_MOCK_TARGET_AGENT=true
DEV_MOCK_JUDGE=true
DEV_SEED_DATA=true
```

## Local Development

### Quick Start
```bash
# 1. Clone and configure
git clone <repo>
cd agent-redteam-framework
cp .env.example .env
# Edit .env with your settings

# 2. Start infrastructure
docker-compose -f docker-compose.dev.yml up -d

# 3. Backend
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
alembic upgrade head
python ../scripts/seed_demo_data.py
uvicorn app.main:app --reload

# 4. Frontend (new terminal)
cd frontend
npm install
npm run dev

# 5. Access
# Frontend: http://localhost:3000
# API: http://localhost:8000/docs
```

### Using Docker Compose (All Services)
```bash
docker-compose -f docker-compose.dev.yml up -d
# Access all services via localhost ports
```

## Staging Deployment

### Kubernetes
```bash
# 1. Apply namespace
kubectl apply -f infra/kubernetes/namespace.yaml

# 2. Create secrets
kubectl create secret generic redteam-secrets \
  --from-literal=database-url="$DATABASE_URL" \
  --from-literal=redis-url="$REDIS_URL" \
  --from-literal=secret-key="$SECRET_KEY" \
  --from-literal=jwt-private-key="$(cat private.pem)" \
  --from-literal=jwt-public-key="$(cat public.pem)" \
  --from-literal=s3-access-key="$S3_ACCESS_KEY" \
  --from-literal=s3-secret-key="$S3_SECRET_KEY" \
  -n redteam-framework

# 3. Create configmap
kubectl create configmap redteam-config \
  --from-literal=EVAL_MODE=production \
  --from-literal=CHROMA_HOST=chromadb \
  --from-literal=CHROMA_PORT=8000 \
  --from-literal=S3_ENDPOINT_URL=$S3_ENDPOINT_URL \
  --from-literal=S3_BUCKET=$S3_BUCKET \
  -n redteam-framework

# 4. Deploy
kubectl apply -f infra/kubernetes/
```

### Verify Deployment
```bash
# Check pods
kubectl get pods -n redteam-framework

# Check logs
kubectl logs -l app=redteam-api -n redteam-framework -f --tail=100
kubectl logs -l app=redteam-worker -n redteam-framework -f --tail=100
kubectl logs -l app=redteam-frontend -n redteam-framework -f --tail=100
```

## Production Deployment

### Infrastructure Requirements

| Component | Specification |
|-----------|---------------|
| PostgreSQL | 16+, 4 vCPU, 16GB RAM, 500GB SSD |
| Redis | 7+, 2 vCPU, 8GB RAM |
| ChromaDB | 0.4+, 4 vCPU, 16GB RAM |
| Object Storage | S3-compatible, versioning enabled |
| Kubernetes | 1.28+, 3+ worker nodes |
| Ingress | NGINX or cloud load balancer |
| TLS | Let's Encrypt or managed certs |

### High Availability
- **API**: 3+ replicas with HPA (CPU > 70%)
- **Workers**: 3+ replicas, scale on queue depth
- **Frontend**: 2+ replicas behind CDN
- **Database**: Primary + replica with auto-failover
- **Redis**: Cluster mode or Sentinel
- **ChromaDB**: Single writer, read replicas

### Deployment Strategy

#### Canary (Recommended)
```bash
# 1. Deploy canary (10% traffic)
kubectl set image deployment/redteam-api \
  api=ghcr.io/org/redteam-backend:v1.2.3-canary \
  -n redteam-framework

# 2. Monitor for 30 minutes
# Check: error rates, latency, business metrics

# 3. Promote to 100%
kubectl set image deployment/redteam-api \
  api=ghcr.io/org/redteam-backend:v1.2.3 \
  -n redteam-framework
```

#### Blue/Green
```bash
# 1. Deploy to green namespace
kubectl apply -k overlays/green

# 2. Test green
# Run smoke tests against green

# 3. Switch traffic
kubectl patch ingress redteam-ingress \
  -p '{"spec":{"rules":[{"host":"api.example.com","http":{"paths":[{"path":"/","backend":{"service":{"name":"redteam-api-green"}}}}]}}'}

# 4. Monitor, then decommission blue
```

### Rollback Procedure
```bash
# Quick rollback (last known good)
kubectl rollout undo deployment/redteam-api -n redteam-framework

# Or specific revision
kubectl rollout undo deployment/redteam-api --to-revision=5 -n redteam-framework

# Verify
kubectl rollout status deployment/redteam-api -n redteam-framework
```

## Database Migrations

### Running Migrations
```bash
# Development
cd backend && alembic upgrade head

# Production (with backup)
pg_dump -h $DB_HOST -U postgres redteam > backup_$(date +%Y%m%d).sql
cd backend && alembic upgrade head

# Verify
alembic current
```

### Creating Migrations
```bash
cd backend
alembic revision --autogenerate -m "Description of changes"
# Review generated migration
alembic upgrade head
```

### Migration Best Practices
1. **Always review** auto-generated migrations
2. **Test upgrade/downgrade** on copy of production data
3. **Use transactions** for multi-table changes
4. **Add indexes** in separate migrations for large tables
5. **Backfill data** in separate step after schema change
6. **Never modify** applied migrations

## Backup & Recovery

### Database Backup
```bash
# Daily automated
pg_dump -h $DB_HOST -U postgres redteam | gzip > s3://bucket/backups/redteam_$(date +%Y%m%d).sql.gz

# WAL archiving for PITR
# Configure in postgresql.conf:
# wal_level = replica
# archive_mode = on
# archive_command = 'aws s3 cp %p s3://bucket/wal/%f'
```

### Recovery Procedures

```bash
# Point-in-time recovery (RPO < 1 hour, RTO < 4 hours)
# 1. Restore base backup
# 2. Replay WAL files to target timestamp
# 3. Verify data integrity
# 4. Promote replica

# Full restore from daily backup
gunzip -c redteam_20240115.sql.gz | psql -h $DB_HOST -U postgres redteam
```

## Monitoring & Alerting

### Key Metrics to Watch
- API latency (p50, p95, p99)
- Error rate by endpoint
- Queue depth (Celery)
- Run success/failure rate
- Regression detection rate
- Cost per run / daily
- Review queue SLA

### Alert Rules
```yaml
# Critical
- alert: HighErrorRate
  expr: rate(http_requests_total{status=~"5.."}[5m]) > 0.05
  
- alert: RegressionGateFailure
  expr: redteam_gate_decision{decision="BLOCK"} > 0

# Warning
- alert: QueueBacklog
  expr: celery_queue_length > 100

- alert: HighCost
  expr: redteam_daily_cost_usd > 80
```

## Security Hardening

### Network Policies
```yaml
# Restrict pod-to-pod communication
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: redteam-api-netpol
spec:
  podSelector:
    matchLabels:
      app: redteam-api
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - namespaceSelector:
        matchLabels:
          name: ingress-nginx
    ports:
    - protocol: TCP
      port: 8000
  egress:
  - to:
    - podSelector:
        matchLabels:
          app: postgres
    ports:
    - protocol: TCP
      port: 5432
  - to:
    - podSelector:
        matchLabels:
          app: redis
    ports:
    - protocol: TCP
      port: 6379
```

### Secrets Management
- Use external secrets operator (HashiCorp Vault, AWS Secrets Manager, etc.)
- Rotate JWT keys quarterly
- Rotate database passwords monthly
- Audit secret access

## Cost Optimization

### Right-Sizing
- Monitor CPU/memory utilization
- Adjust requests/limits quarterly
- Use spot instances for workers

### LLM Cost Control
- Set daily/monthly budgets
- Use cheaper models for development
- Cache judge responses where appropriate
- Batch embedding requests

## Troubleshooting

### Common Issues

| Issue | Cause | Solution |
|-------|-------|----------|
| API 503 | DB connection pool exhausted | Increase pool size, check long queries |
| Workers stuck | Celery broker down | Restart Redis, check connectivity |
| High latency | LLM provider slow | Enable fallback, check circuit breakers |
| ChromaDB OOM | Too many embeddings | Reduce batch size, add memory |

### Debug Commands
```bash
# Check API logs
kubectl logs -l app=redteam-api -n redteam-framework --tail=100

# Check worker logs
kubectl logs -l app=redteam-worker -n redteam-framework --tail=100

# Check database connections
kubectl exec -it postgres-0 -n redteam-framework -- psql -U postgres -c "SELECT * FROM pg_stat_activity;"

# Check Redis memory
kubectl exec -it redis-xxx -n redteam-framework -- redis-cli INFO memory
```