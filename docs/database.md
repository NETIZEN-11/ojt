# Database Documentation

## Schema Overview

The database uses PostgreSQL with SQLAlchemy 2.x ORM. All tables use UUID primary keys, timestamps, and soft deletes where appropriate.

## Core Tables

### Users & RBAC

```sql
-- Users
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    username VARCHAR(100) UNIQUE NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    full_name VARCHAR(255),
    is_active BOOLEAN DEFAULT true,
    is_superuser BOOLEAN DEFAULT false,
    last_login TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- Roles
CREATE TABLE roles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(50) UNIQUE NOT NULL,
    description TEXT,
    is_system BOOLEAN DEFAULT false,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- Permissions
CREATE TABLE permissions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) UNIQUE NOT NULL,
    description TEXT,
    resource VARCHAR(50) NOT NULL,
    action VARCHAR(50) NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now(),
    UNIQUE(resource, action)
);

-- User-Role mapping
CREATE TABLE user_roles (
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    role_id UUID REFERENCES roles(id) ON DELETE CASCADE,
    PRIMARY KEY (user_id, role_id)
);

-- Role-Permission mapping
CREATE TABLE role_permissions (
    role_id UUID REFERENCES roles(id) ON DELETE CASCADE,
    permission_id UUID REFERENCES permissions(id) ON DELETE CASCADE,
    PRIMARY KEY (role_id, permission_id)
);
```

### Target Agents

```sql
CREATE TABLE target_agents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    endpoint_url VARCHAR(500) NOT NULL,
    auth_config JSONB DEFAULT '{}',
    request_template JSONB DEFAULT '{}',
    response_extraction JSONB DEFAULT '{}',
    timeout_seconds INTEGER DEFAULT 30,
    max_retries INTEGER DEFAULT 3,
    allowed BOOLEAN DEFAULT true,
    status VARCHAR(20) DEFAULT 'active',
    health_check_url VARCHAR(500),
    last_health_check TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now(),
    created_by UUID REFERENCES users(id) ON DELETE SET NULL
);

CREATE INDEX ix_target_agents_status_allowed ON target_agents(status, allowed);
```

### Test Suites & Cases

```sql
-- Test Suites
CREATE TABLE test_suites (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    version INTEGER DEFAULT 1,
    schema_version VARCHAR(20) DEFAULT '1.0',
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now(),
    created_by UUID REFERENCES users(id) ON DELETE SET NULL
);

CREATE UNIQUE INDEX uq_test_suite_name_version ON test_suites(name, version);
CREATE INDEX ix_test_suites_name_version ON test_suites(name, version);

-- Test Suite Versions
CREATE TABLE test_suite_versions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    suite_id UUID REFERENCES test_suites(id) ON DELETE CASCADE,
    version INTEGER NOT NULL,
    snapshot JSONB NOT NULL,
    changelog TEXT,
    created_at TIMESTAMPTZ DEFAULT now(),
    created_by UUID REFERENCES users(id) ON DELETE SET NULL
);

CREATE UNIQUE INDEX uq_test_suite_version ON test_suite_versions(suite_id, version);

-- Test Cases
CREATE TABLE test_cases (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    suite_id UUID REFERENCES test_suites(id) ON DELETE CASCADE,
    version INTEGER DEFAULT 1,
    test_case_id VARCHAR(100) NOT NULL,
    category VARCHAR(50) NOT NULL,
    severity VARCHAR(20) NOT NULL,
    input TEXT NOT NULL,
    expected_behavior_type VARCHAR(50) NOT NULL,
    matcher_config JSONB,
    rubric_config JSONB,
    metadata JSONB DEFAULT '{}',
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now(),
    created_by UUID REFERENCES users(id) ON DELETE SET NULL
);

CREATE UNIQUE INDEX uq_test_case_suite_id_version ON test_cases(suite_id, test_case_id, version);
CREATE INDEX ix_test_cases_suite_category ON test_cases(suite_id, category);

-- Test Case Versions
CREATE TABLE test_case_versions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    test_case_id UUID REFERENCES test_cases(id) ON DELETE CASCADE,
    version INTEGER NOT NULL,
    snapshot JSONB NOT NULL,
    changelog TEXT,
    created_at TIMESTAMPTZ DEFAULT now(),
    created_by UUID REFERENCES users(id) ON DELETE SET NULL
);

CREATE UNIQUE INDEX uq_test_case_version ON test_case_versions(test_case_id, version);
```

### Runs & Executions

```sql
-- Runs
CREATE TABLE runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    target_agent_id UUID REFERENCES target_agents(id) ON DELETE CASCADE,
    suite_id UUID REFERENCES test_suites(id) ON DELETE CASCADE,
    suite_version INTEGER NOT NULL,
    baseline_id UUID REFERENCES baselines(id) ON DELETE SET NULL,
    status VARCHAR(30) DEFAULT 'queued',
    framework_version VARCHAR(50) DEFAULT '1.0.0',
    model_versions JSONB DEFAULT '{}',
    prompt_versions JSONB DEFAULT '{}',
    config_snapshot JSONB DEFAULT '{}',
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    total_tests INTEGER DEFAULT 0,
    passed_count INTEGER DEFAULT 0,
    failed_count INTEGER DEFAULT 0,
    inconclusive_count INTEGER DEFAULT 0,
    regression_count INTEGER DEFAULT 0,
    critical_count INTEGER DEFAULT 0,
    high_count INTEGER DEFAULT 0,
    medium_count INTEGER DEFAULT 0,
    low_count INTEGER DEFAULT 0,
    total_cost_usd DOUBLE PRECISION DEFAULT 0.0,
    total_latency_ms INTEGER DEFAULT 0,
    error_message TEXT,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now(),
    created_by UUID REFERENCES users(id) ON DELETE SET NULL
);

CREATE INDEX ix_runs_status_created ON runs(status, created_at);
CREATE INDEX ix_runs_agent_suite ON runs(target_agent_id, suite_id);

-- Executions
CREATE TABLE executions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id UUID REFERENCES runs(id) ON DELETE CASCADE,
    test_case_id UUID REFERENCES test_cases(id) ON DELETE CASCADE,
    status VARCHAR(20) DEFAULT 'queued',
    target_request JSONB,
    target_response JSONB,
    tool_calls JSONB DEFAULT '[]',
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    latency_ms INTEGER DEFAULT 0,
    error TEXT,
    retry_count INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE UNIQUE INDEX uq_execution_run_test_case ON executions(run_id, test_case_id);
CREATE INDEX ix_executions_run_status ON executions(run_id, status);

-- Results
CREATE TABLE results (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    execution_id UUID UNIQUE REFERENCES executions(id) ON DELETE CASCADE,
    run_id UUID REFERENCES runs(id) ON DELETE CASCADE,
    test_case_id UUID REFERENCES test_cases(id) ON DELETE CASCADE,
    verdict VARCHAR(20) NOT NULL,
    confidence DOUBLE PRECISION NOT NULL,
    matcher_used VARCHAR(50),
    judge_output JSONB,
    second_judge_output JSONB,
    judge_agreement BOOLEAN DEFAULT true,
    evidence JSONB DEFAULT '[]',
    execution_time_ms INTEGER DEFAULT 0,
    tokens_used INTEGER DEFAULT 0,
    estimated_cost DOUBLE PRECISION DEFAULT 0.0,
    errors JSONB DEFAULT '[]',
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX ix_results_run_verdict ON results(run_id, verdict);
CREATE INDEX ix_results_test_case_verdict ON results(test_case_id, verdict);
```

### Baselines

```sql
-- Baselines
CREATE TABLE baselines (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    suite_id UUID REFERENCES test_suites(id) ON DELETE CASCADE,
    suite_version INTEGER NOT NULL,
    run_id UUID REFERENCES runs(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    framework_version VARCHAR(50) NOT NULL,
    model_versions JSONB DEFAULT '{}',
    prompt_versions JSONB DEFAULT '{}',
    approved_by UUID REFERENCES users(id) ON DELETE CASCADE,
    approved_at TIMESTAMPTZ DEFAULT now(),
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE UNIQUE INDEX uq_baseline_suite_version_run ON baselines(suite_id, suite_version, run_id);
CREATE INDEX ix_baselines_suite_active ON baselines(suite_id, is_active);

-- Baseline Items
CREATE TABLE baseline_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    baseline_id UUID REFERENCES baselines(id) ON DELETE CASCADE,
    test_case_id UUID REFERENCES test_cases(id) ON DELETE CASCADE,
    verdict VARCHAR(20) NOT NULL,
    confidence DOUBLE PRECISION NOT NULL,
    evidence JSONB DEFAULT '[]',
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE UNIQUE INDEX uq_baseline_item ON baseline_items(baseline_id, test_case_id);
```

### Regressions & Reviews

```sql
-- Regressions
CREATE TABLE regressions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id UUID REFERENCES runs(id) ON DELETE CASCADE,
    baseline_id UUID REFERENCES baselines(id) ON DELETE CASCADE,
    test_case_id UUID REFERENCES test_cases(id) ON DELETE CASCADE,
    previous_verdict VARCHAR(20) NOT NULL,
    current_verdict VARCHAR(20) NOT NULL,
    regression_type VARCHAR(30) NOT NULL,
    severity VARCHAR(20) NOT NULL,
    evidence JSONB DEFAULT '[]',
    acknowledged BOOLEAN DEFAULT false,
    acknowledged_by UUID REFERENCES users(id) ON DELETE SET NULL,
    acknowledged_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE UNIQUE INDEX uq_regression_run_baseline_test ON regressions(run_id, baseline_id, test_case_id);
CREATE INDEX ix_regressions_run_severity ON regressions(run_id, severity);
CREATE INDEX ix_regressions_baseline_test_case ON regressions(baseline_id, test_case_id);

-- Severity Findings
CREATE TABLE severity_findings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    regression_id UUID REFERENCES regressions(id) ON DELETE CASCADE,
    level VARCHAR(20) NOT NULL,
    rationale TEXT NOT NULL,
    deterministic_override BOOLEAN DEFAULT false,
    categories JSONB DEFAULT '[]',
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX ix_severity_findings_regression_level ON severity_findings(regression_id, level);

-- Review Queue
CREATE TABLE review_queue (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    regression_id UUID UNIQUE REFERENCES regressions(id) ON DELETE CASCADE,
    run_id UUID REFERENCES runs(id) ON DELETE CASCADE,
    severity VARCHAR(20) NOT NULL,
    confidence DOUBLE PRECISION NOT NULL,
    category VARCHAR(100) NOT NULL,
    status VARCHAR(20) DEFAULT 'pending',
    assigned_to UUID REFERENCES users(id) ON DELETE SET NULL,
    label VARCHAR(30),
    reviewer_notes TEXT,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now(),
    resolved_at TIMESTAMPTZ
);

CREATE UNIQUE INDEX uq_review_regression ON review_queue(regression_id);
CREATE INDEX ix_review_queue_status_severity ON review_queue(status, severity);
CREATE INDEX ix_review_queue_assigned ON review_queue(assigned_to, status);

-- Review Labels
CREATE TABLE review_labels (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    review_id UUID REFERENCES review_queue(id) ON DELETE CASCADE,
    label VARCHAR(30) NOT NULL,
    reviewer_id UUID REFERENCES users(id) ON DELETE CASCADE,
    rationale TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX ix_review_labels_review_created ON review_labels(review_id, created_at);
```

### Audit & Configuration

```sql
-- Audit Logs
CREATE TABLE audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    action VARCHAR(100) NOT NULL,
    resource_type VARCHAR(100) NOT NULL,
    resource_id UUID,
    details JSONB DEFAULT '{}',
    ip_address VARCHAR(45),
    user_agent TEXT,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX ix_audit_logs_user_created ON audit_logs(user_id, created_at);
CREATE INDEX ix_audit_logs_resource ON audit_logs(resource_type, resource_id);
CREATE INDEX ix_audit_logs_action_created ON audit_logs(action, created_at);

-- Model Configurations
CREATE TABLE model_configs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    provider VARCHAR(50) NOT NULL,
    model_name VARCHAR(100) NOT NULL,
    model_version VARCHAR(50) NOT NULL,
    role VARCHAR(50) NOT NULL,
    config JSONB DEFAULT '{}',
    is_active BOOLEAN DEFAULT true,
    is_default BOOLEAN DEFAULT false,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE UNIQUE INDEX uq_model_config ON model_configs(provider, model_name, model_version, role);
CREATE INDEX ix_model_configs_role_active ON model_configs(role, is_active);

-- Prompt Versions
CREATE TABLE prompt_versions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    prompt_type VARCHAR(50) NOT NULL,
    version VARCHAR(50) NOT NULL,
    content TEXT NOT NULL,
    variables JSONB DEFAULT '[]',
    status VARCHAR(20) DEFAULT 'draft',
    created_by UUID REFERENCES users(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ DEFAULT now(),
    promoted_at TIMESTAMPTZ,
    promoted_by UUID REFERENCES users(id) ON DELETE SET NULL
);

CREATE UNIQUE INDEX uq_prompt_version ON prompt_versions(prompt_type, version);
CREATE INDEX ix_prompt_versions_type_status ON prompt_versions(prompt_type, status);

-- Attack Taxonomy
CREATE TABLE attack_taxonomy (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    category VARCHAR(100) NOT NULL,
    subcategory VARCHAR(100),
    technique VARCHAR(200) NOT NULL,
    description TEXT NOT NULL,
    examples TEXT[] DEFAULT '{}',
    severity VARCHAR(20) NOT NULL,
    tags TEXT[] DEFAULT '{}',
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE UNIQUE INDEX uq_attack_taxonomy ON attack_taxonomy(category, subcategory, technique);
CREATE INDEX ix_attack_taxonomy_category_severity ON attack_taxonomy(category, severity);

-- Embedding Documents
CREATE TABLE embedding_documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    collection VARCHAR(100) NOT NULL,
    content TEXT NOT NULL,
    metadata JSONB DEFAULT '{}',
    embedding JSONB,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX ix_embedding_documents_collection ON embedding_documents(collection);

-- Feature Flags
CREATE TABLE feature_flags (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) UNIQUE NOT NULL,
    enabled BOOLEAN DEFAULT false,
    description TEXT NOT NULL,
    rollout_percentage INTEGER DEFAULT 100,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- Notifications
CREATE TABLE notifications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    type VARCHAR(50) NOT NULL,
    title VARCHAR(255) NOT NULL,
    message TEXT NOT NULL,
    data JSONB DEFAULT '{}',
    read BOOLEAN DEFAULT false,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX ix_notifications_user_read ON notifications(user_id, read);
CREATE INDEX ix_notifications_user_created ON notifications(user_id, created_at);
```

## Migration Strategy

### Alembic Configuration

```ini
# alembic.ini
[alembic]
script_location = migrations
prepend_sys_path = true
version_locations = migrations/versions
```

### Migration Commands

```bash
# Create new migration
alembic revision --autogenerate -m "Description"

# Apply migrations
alembic upgrade head

# Downgrade (if supported)
alembic downgrade -1

# Show current revision
alembic current

# Show history
alembic history
```

### Migration Best Practices

1. **Always review** auto-generated migrations
2. **Test upgrade/downgrade** on copy of production data
3. **Use transactions** for multi-table changes
4. **Add indexes** in separate migrations for large tables
5. **Backfill data** in separate step after schema change
6. **Never modify** applied migrations

## Indexing Strategy

### Primary Indexes
- All UUID primary keys (automatic)
- All foreign keys (explicit indexes)

### Query Optimization Indexes

```sql
-- Run queries
CREATE INDEX ix_runs_status_created ON runs(status, created_at DESC);
CREATE INDEX ix_runs_agent_suite ON runs(target_agent_id, suite_id);

-- Result queries
CREATE INDEX ix_results_run_verdict ON results(run_id, verdict);
CREATE INDEX ix_results_test_case_verdict ON results(test_case_id, verdict);

-- Regression queries
CREATE INDEX ix_regressions_run_severity ON regressions(run_id, severity);
CREATE INDEX ix_regressions_baseline_test_case ON regressions(baseline_id, test_case_id);

-- Review queries
CREATE INDEX ix_review_queue_status_severity ON review_queue(status, severity);
CREATE INDEX ix_review_queue_assigned ON review_queue(assigned_to, status);

-- Audit queries
CREATE INDEX ix_audit_logs_user_created ON audit_logs(user_id, created_at DESC);
CREATE INDEX ix_audit_logs_resource ON audit_logs(resource_type, resource_id);
CREATE INDEX ix_audit_logs_action_created ON audit_logs(action, created_at DESC);
```

### Partial Indexes (PostgreSQL)

```sql
-- Only index active records
CREATE INDEX ix_test_suites_active_name ON test_suites(name) WHERE is_active = true;
CREATE INDEX ix_target_agents_active ON target_agents(endpoint_url) WHERE allowed = true AND status = 'active';
```

## Backup & Recovery

### Automated Backups

```bash
# Daily full backup
pg_dump -h $HOST -U postgres redteam | gzip > s3://bucket/backups/redteam_$(date +%Y%m%d).sql.gz

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
gunzip -c redteam_20240115.sql.gz | psql -h $HOST -U postgres redteam
```

## Performance Tuning

### Configuration (postgresql.conf)

```ini
# Memory
shared_buffers = 4GB
effective_cache_size = 12GB
work_mem = 64MB
maintenance_work_mem = 1GB

# Parallelism
max_worker_processes = 8
max_parallel_workers_per_gather = 4
max_parallel_workers = 8

# WAL
wal_buffers = 16MB
min_wal_size = 1GB
max_wal_size = 4GB

# Planner
random_page_cost = 1.1
effective_io_concurrency = 200
```

### Monitoring Queries

```sql
-- Slow queries
SELECT query, mean_time, calls, total_time
FROM pg_stat_statements
ORDER BY mean_time DESC
LIMIT 20;

-- Table bloat
SELECT schemaname, tablename, pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;

-- Index usage
SELECT indexrelname, idx_scan, idx_tup_read, idx_tup_fetch
FROM pg_stat_user_indexes
ORDER BY idx_scan;
```