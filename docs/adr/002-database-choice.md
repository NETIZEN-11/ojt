# ADR 002: Database Choice - PostgreSQL

## Status
Accepted

## Context
We need a primary relational database for the Agent Red-Teaming Framework. Requirements:
- ACID transactions for run execution, scoring, baseline approval
- Complex queries (joins across runs, results, regressions, baselines)
- JSONB support for flexible schemas (test cases, results, configs)
- UUID primary keys
- Horizontal scaling not required (single writer)
- Point-in-time recovery for compliance
- Mature ecosystem and tooling

## Decision
Use **PostgreSQL 16+** as the primary database.

## Rationale

### Why PostgreSQL?
1. **ACID Compliance**: Full transaction support for critical operations
2. **JSONB**: First-class JSON support with indexing for flexible schemas
3. **UUID Support**: Native UUID type with gen_random_uuid()
4. **Advanced Indexing**: Partial, expression, GIN/GiST indexes for JSONB
5. **Point-in-Time Recovery**: WAL archiving for RPO < 1 hour
6. **Extensions**: pg_trgm, pg_stat_statements, uuid-ossp
7. **Ecosystem**: Excellent ORM support (SQLAlchemy 2.x), migration tools (Alembic)
8. **Maturity**: 25+ years, battle-tested at scale

### Why Not Alternatives?

| Database | Reason for Rejection |
|----------|---------------------|
| MySQL | Weaker JSON support, no partial indexes, less mature GIS |
| MongoDB | No ACID transactions across collections, eventual consistency |
| SQLite | No concurrent writes, no horizontal scaling, no JSONB indexing |
| CockroachDB | Overkill for single-writer, adds latency, complex ops |
| DynamoDB | No SQL, limited queries, vendor lock-in |

## Consequences

### Positive
- Strong consistency for safety-critical operations
- Rich query capabilities for analytics/reporting
- Mature tooling for migrations, backups, monitoring
- Team familiarity reduces onboarding

### Negative
- Vertical scaling only (but sufficient for workload)
- Operational overhead (backups, vacuum, monitoring)
- Single writer bottleneck (mitigated by read replicas)

## Implementation

### Extensions
```sql
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";
CREATE EXTENSION IF NOT EXISTS "pg_stat_statements";
```

### Connection Pooling
- PgBouncer in transaction mode
- Pool size: 20, max overflow: 10
- Application-level pooling via SQLAlchemy

### Monitoring
- pg_stat_statements for slow queries
- pg_stat_activity for active connections
- Custom metrics: connection pool usage, replication lag

## Migration Strategy
- Alembic for schema migrations
- All migrations reviewed before apply
- Test upgrade/downgrade on staging
- Zero-downtime migrations where possible
- Separate data migrations from schema changes