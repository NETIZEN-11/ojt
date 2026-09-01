# Runbook

## Service Overview

| Service | Port | Health Check | Replicas (Prod) |
|---------|------|--------------|-----------------|
| API | 8000 | /health, /ready | 3 |
| Worker | - | Celery heartbeat | 3 |
| Frontend | 3000 | / | 2 |
| PostgreSQL | 5432 | pg_isready | 1 (primary) + 1 replica |
| Redis | 6379 | PING | 1 (cluster) |
| ChromaDB | 8000 | /api/v1/heartbeat | 1 |
| MinIO | 9000 | /minio/health/live | 1 |

## Common Operations

### Starting Services

```bash
# Development
docker-compose -f docker-compose.dev.yml up -d

# Production (Kubernetes)
kubectl apply -f infra/kubernetes/
```

### Stopping Services

```bash
# Development
docker-compose -f docker-compose.dev.yml down

# Production
kubectl scale deployment redteam-api redteam-worker redteam-frontend --replicas=0 -n redteam-framework
```

### Restarting Services

```bash
# Development
docker-compose -f docker-compose.dev.yml restart

# Production
kubectl rollout restart deployment/redteam-api -n redteam-framework
kubectl rollout restart deployment/redteam-worker -n redteam-framework
kubectl rollout restart deployment/redteam-frontend -n redteam-framework
```

### Viewing Logs

```bash
# Development
docker-compose -f docker-compose.dev.yml logs -f [service]

# Production
kubectl logs -l app=redteam-api -n redteam-framework -f --tail=100
kubectl logs -l app=redteam-worker -n redteam-framework -f --tail=100
kubectl logs -l app=redteam-frontend -n redteam-framework -f --tail=100
```

## Database Operations

### Connect to Database

```bash
# Development
docker exec -it redteam-postgres-dev psql -U postgres -d redteam

# Production
kubectl exec -it postgres-0 -n redteam-framework -- psql -U postgres -d redteam
```

### Common Queries

```sql
-- Check run status
SELECT id, status, created_at, completed_at 
FROM runs 
ORDER BY created_at DESC LIMIT 10;

-- Check stuck runs
SELECT * FROM runs 
WHERE status IN ('running', 'scoring', 'diffing') 
AND started_at < NOW() - INTERVAL '30 minutes';

-- Check regression counts
SELECT severity, COUNT(*) 
FROM regressions 
GROUP BY severity;

-- Check review queue
SELECT status, COUNT(*) 
FROM review_queue 
GROUP BY status;

-- Check disk usage
SELECT pg_size_pretty(pg_database_size('redteam'));
```

### Backup & Restore

```bash
# Backup
pg_dump -h $HOST -U postgres redteam | gzip > backup_$(date +%Y%m%d_%H%M%S).sql.gz

# Restore
gunzip -c backup_20240115_020000.sql.gz | psql -h $HOST -U postgres redteam
```

### Migrations

```bash
# Check status
alembic current

# Apply
alembic upgrade head

# Create new
alembic revision --autogenerate -m "Description"
```

## Redis Operations

### Connect

```bash
# Development
docker exec -it redteam-redis-dev redis-cli

# Production
kubectl exec -it redis-xxx -n redteam-framework -- redis-cli
```

### Common Commands

```bash
# Check memory
INFO memory

# Check keys
KEYS *

# Clear cache (careful!)
FLUSHDB

# Monitor
MONITOR
```

## Celery/Worker Operations

### Monitor Workers

```bash
# Development
celery -A app.workers.celery_app inspect active

# Production
kubectl exec -it worker-xxx -n redteam-framework -- celery -A app.workers.celery_app inspect active
```

### Queue Management

```bash
# Check queue lengths
celery -A app.workers.celery_app inspect active_queues

# Purge queue (careful!)
celery -A app.workers.celery_app purge

# Revoke task
celery -A app.workers.celery_app control revoke <task_id>
```

### Worker Scaling

```bash
# Scale up
kubectl scale deployment redteam-worker --replicas=5 -n redteam-framework

# Scale down
kubectl scale deployment redteam-worker --replicas=2 -n redteam-framework
```

## API Operations

### Health Checks

```bash
# Basic health
curl https://api.redteam.example.com/health

# Readiness (dependencies)
curl https://api.redteam.example.com/ready

# Metrics
curl https://api.redteam.example.com/metrics
```

### Common API Calls

```bash
# Create run
curl -X POST https://api.redteam.example.com/api/v1/runs \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"target_agent_id": "uuid", "suite_id": "uuid"}'

# Get run status
curl https://api.redteam.example.com/api/v1/runs/$RUN_ID \
  -H "Authorization: Bearer $TOKEN"

# Get regressions
curl https://api.redteam.example.com/api/v1/regressions/run/$RUN_ID \
  -H "Authorization: Bearer $TOKEN"
```

## Troubleshooting Guide

### API Returns 503

| Cause | Check | Fix |
|-------|-------|-----|
| DB connection pool exhausted | `SELECT * FROM pg_stat_activity` | Increase pool, kill long queries |
| Redis down | `redis-cli ping` | Restart Redis, check connection |
| ChromaDB down | `curl http://chromadb:8000/api/v1/heartbeat` | Restart ChromaDB |
| Circuit breaker open | Check logs for "CIRCUIT_BREAKER_OPEN" | Wait for reset, check upstream |

### Workers Not Processing

| Cause | Check | Fix |
|-------|-------|-----|
| Queue backed up | `celery inspect active_queues` | Scale workers, check task timeouts |
| Workers dead | `kubectl get pods -l app=redteam-worker` | Check logs, restart deployment |
| Broker down | `redis-cli ping` | Restart Redis |
| Task timeout | Check task logs | Increase timeout, optimize code |

### High Latency

| Cause | Check | Fix |
|-------|-------|-----|
| LLM provider slow | Check provider status page | Enable fallback, increase timeout |
| DB slow | `pg_stat_statements` | Add indexes, optimize queries |
| Network | Check pod-to-pod latency | Check CNI, service mesh |
| ChromaDB | Query latency metrics | Reduce batch size, add memory |

### Run Stuck in "running"

```bash
# 1. Check run status
SELECT * FROM runs WHERE id = '$RUN_ID';

# 2. Check executions
SELECT * FROM executions WHERE run_id = '$RUN_ID' AND status = 'running';

# 3. Check worker logs
kubectl logs -l app=redteam-worker -n redteam-framework --since=1h | grep $RUN_ID

# 4. If stuck, mark failed
UPDATE runs SET status = 'failed', error_message = 'Worker timeout', completed_at = NOW() WHERE id = '$RUN_ID';
```

### Regression Gate Failing Unexpectedly

```bash
# 1. Check regressions
SELECT * FROM regressions WHERE run_id = '$RUN_ID';

# 2. Check baseline
SELECT * FROM baselines WHERE id = (SELECT baseline_id FROM runs WHERE id = '$RUN_ID');

# 3. Compare results
SELECT r.test_case_id, r.verdict as current, bi.verdict as baseline
FROM results r
JOIN baseline_items bi ON r.test_case_id = bi.test_case_id AND bi.baseline_id = '$BASELINE_ID'
WHERE r.run_id = '$RUN_ID' AND r.verdict != bi.verdict;

# 4. If false positive, acknowledge
UPDATE regressions SET acknowledged = true, acknowledged_by = '$USER_ID', acknowledged_at = NOW() WHERE id = '$REGRESSION_ID';
```

## Emergency Procedures

### Database Failover

```bash
# 1. Promote replica
kubectl exec -it postgres-replica-0 -n redteam-framework -- pg_ctl promote -D /var/lib/postgresql/data

# 2. Update DNS/connection strings
# 3. Verify application connectivity
# 4. Rebuild replica
```

### Complete Outage Recovery

```bash
# 1. Assess scope
kubectl get pods -n redteam-framework

# 2. Restore from backup (if data loss)
gunzip -c backup_latest.sql.gz | psql -h $NEW_HOST -U postgres redteam

# 3. Run migrations
cd backend && alembic upgrade head

# 4. Restart all services
kubectl rollout restart deployment -n redteam-framework

# 5. Verify health
curl https://api.redteam.example.com/ready
```

### Security Incident

```bash
# 1. Revoke all tokens (force re-login)
# Update JWT signing key in secret manager

# 2. Rotate database passwords
# Update in secret manager, restart pods

# 3. Rotate API keys
# Update in secret manager, restart pods

# 4. Audit recent activity
SELECT * FROM audit_logs WHERE created_at > NOW() - INTERVAL '24 hours' ORDER BY created_at DESC;
```

## Monitoring Alerts

### Critical Alerts (Page Immediately)
- API error rate > 5% for 5 minutes
- Database unavailable
- Regression gate BLOCK on critical severity
- Worker queue > 500 for 10 minutes
- Daily cost > $90 (90% of budget)

### Warning Alerts (Notify Within 1 Hour)
- API latency p99 > 2 seconds
- Database connections > 80%
- Redis memory > 80%
- ChromaDB query latency > 5s
- Review queue > 50 items
- Daily cost > $50

### Info Alerts (Daily Digest)
- New regressions detected
- Baseline approvals
- User login anomalies
- Cost trends

## Contact Information

| Role | Primary | Secondary |
|------|---------|-----------|
| Platform On-Call | +1-XXX-XXX-XXXX | Slack #platform-oncall |
| Security On-Call | +1-XXX-XXX-XXXX | Slack #security-oncall |
| Database Admin | +1-XXX-XXX-XXXX | Slack #dba-oncall |
| Engineering Lead | +1-XXX-XXX-XXXX | Slack #eng-leadership |

## Useful Links

- [API Documentation](https://api.redteam.example.com/docs)
- [Grafana Dashboards](https://grafana.redteam.example.com)
- [Prometheus](https://prometheus.redteam.example.com)
- [Kubernetes Dashboard](https://k8s.redteam.example.com)
- [CI/CD Pipeline](https://github.com/org/redteam-framework/actions)
- [Incident Tracker](https://incidents.redteam.example.com)