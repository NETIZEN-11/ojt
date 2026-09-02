"""initial_schema

Revision ID: 001
Revises: 
Create Date: 2026-09-01 13:49:06.567045

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Create users table
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("username", sa.String(100), nullable=False),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("full_name", sa.String(255), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, default=True),
        sa.Column("is_superuser", sa.Boolean(), nullable=False, default=False),
        sa.Column("last_login", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
        sa.UniqueConstraint("username"),
    )
    op.create_index("ix_users_email_active", "users", ["email", "is_active"])

    # Create roles table
    op.create_table(
        "roles",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(50), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_system", sa.Boolean(), nullable=False, default=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )

    # Create permissions table
    op.create_table(
        "permissions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("resource", sa.String(50), nullable=False),
        sa.Column("action", sa.String(50), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
        sa.UniqueConstraint("resource", "action", name="uq_permission_resource_action"),
    )
    op.create_index("ix_permissions_resource", "permissions", ["resource"])

    # Create user_roles association table
    op.create_table(
        "user_roles",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("role_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["role_id"], ["roles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("user_id", "role_id"),
    )

    # Create role_permissions association table
    op.create_table(
        "role_permissions",
        sa.Column("role_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("permission_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.ForeignKeyConstraint(["role_id"], ["roles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["permission_id"], ["permissions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("role_id", "permission_id"),
    )

    # Create target_agents table
    op.create_table(
        "target_agents",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("endpoint_url", sa.String(500), nullable=False),
        sa.Column("auth_config", postgresql.JSONB(), nullable=False, default={}),
        sa.Column("request_template", postgresql.JSONB(), nullable=True),
        sa.Column("response_extraction", postgresql.JSONB(), nullable=True),
        sa.Column("timeout_seconds", sa.Integer(), nullable=False, default=30),
        sa.Column("max_retries", sa.Integer(), nullable=False, default=3),
        sa.Column("allowed", sa.Boolean(), nullable=False, default=True),
        sa.Column("status", sa.String(20), nullable=False, default="active"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_target_agents_status", "target_agents", ["status"])

    # Create test_suites table
    op.create_table(
        "test_suites",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False, default=1),
        sa.Column("schema_version", sa.String(20), nullable=False, default="1.0"),
        sa.Column("is_active", sa.Boolean(), nullable=False, default=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name", "version", name="uq_test_suite_name_version"),
    )
    op.create_index("ix_test_suites_name_version", "test_suites", ["name", "version"])

    # Create test_suite_versions table
    op.create_table(
        "test_suite_versions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("suite_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("snapshot", postgresql.JSONB(), nullable=False),
        sa.Column("changelog", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["suite_id"], ["test_suites.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("suite_id", "version", name="uq_test_suite_version"),
    )
    op.create_index("ix_test_suite_versions_suite_id", "test_suite_versions", ["suite_id"])

    # Create test_cases table
    op.create_table(
        "test_cases",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("suite_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False, default=1),
        sa.Column("test_case_id", sa.String(100), nullable=False),
        sa.Column("category", sa.String(20), nullable=False),
        sa.Column("severity", sa.String(10), nullable=False),
        sa.Column("input", sa.Text(), nullable=False),
        sa.Column("expected_behavior_type", sa.String(20), nullable=False),
        sa.Column("matcher_config", postgresql.JSONB(), nullable=True),
        sa.Column("rubric_config", postgresql.JSONB(), nullable=True),
        sa.Column("metadata", postgresql.JSONB(), nullable=False, default={}),
        sa.Column("is_active", sa.Boolean(), nullable=False, default=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["suite_id"], ["test_suites.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("suite_id", "test_case_id", "version", name="uq_test_case_suite_id_version"),
    )
    op.create_index("ix_test_cases_suite_category", "test_cases", ["suite_id", "category"])

    # Create test_case_versions table
    op.create_table(
        "test_case_versions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("test_case_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("snapshot", postgresql.JSONB(), nullable=False),
        sa.Column("changelog", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["test_case_id"], ["test_cases.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("test_case_id", "version", name="uq_test_case_version"),
    )
    op.create_index("ix_test_case_versions_test_case_id", "test_case_versions", ["test_case_id"])

    # Create runs table
    op.create_table(
        "runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("target_agent_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("suite_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("suite_version", sa.Integer(), nullable=False),
        sa.Column("baseline_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, default="queued"),
        sa.Column("framework_version", sa.String(50), nullable=False, default="1.0.0"),
        sa.Column("model_versions", postgresql.JSONB(), nullable=False, default={}),
        sa.Column("prompt_versions", postgresql.JSONB(), nullable=False, default={}),
        sa.Column("config_snapshot", postgresql.JSONB(), nullable=False, default={}),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("total_tests", sa.Integer(), nullable=False, default=0),
        sa.Column("passed_count", sa.Integer(), nullable=False, default=0),
        sa.Column("failed_count", sa.Integer(), nullable=False, default=0),
        sa.Column("inconclusive_count", sa.Integer(), nullable=False, default=0),
        sa.Column("regression_count", sa.Integer(), nullable=False, default=0),
        sa.Column("critical_count", sa.Integer(), nullable=False, default=0),
        sa.Column("high_count", sa.Integer(), nullable=False, default=0),
        sa.Column("medium_count", sa.Integer(), nullable=False, default=0),
        sa.Column("low_count", sa.Integer(), nullable=False, default=0),
        sa.Column("total_cost_usd", sa.Float(), nullable=False, default=0.0),
        sa.Column("total_latency_ms", sa.Integer(), nullable=False, default=0),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.ForeignKeyConstraint(["baseline_id"], ["baselines.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["suite_id"], ["test_suites.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["target_agent_id"], ["target_agents.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_runs_status_created", "runs", ["status", "created_at"])
    op.create_index("ix_runs_agent_suite", "runs", ["target_agent_id", "suite_id"])

    # Create executions table
    op.create_table(
        "executions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("test_case_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, default="queued"),
        sa.Column("target_request", postgresql.JSONB(), nullable=True),
        sa.Column("target_response", postgresql.JSONB(), nullable=True),
        sa.Column("tool_calls", postgresql.JSONB(), nullable=False, default=[]),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("latency_ms", sa.Integer(), nullable=False, default=0),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("retry_count", sa.Integer(), nullable=False, default=0),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["run_id"], ["runs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["test_case_id"], ["test_cases.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("run_id", "test_case_id", name="uq_execution_run_test_case"),
    )
    op.create_index("ix_executions_run_status", "executions", ["run_id", "status"])

    # Create results table
    op.create_table(
        "results",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("execution_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("test_case_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("verdict", sa.String(12), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("matcher_used", sa.String(20), nullable=True),
        sa.Column("judge_output", postgresql.JSONB(), nullable=True),
        sa.Column("second_judge_output", postgresql.JSONB(), nullable=True),
        sa.Column("judge_agreement", sa.Boolean(), nullable=False, default=True),
        sa.Column("evidence", postgresql.JSONB(), nullable=False, default=[]),
        sa.Column("execution_time_ms", sa.Integer(), nullable=False, default=0),
        sa.Column("tokens_used", sa.Integer(), nullable=False, default=0),
        sa.Column("estimated_cost", sa.Float(), nullable=False, default=0.0),
        sa.Column("errors", postgresql.JSONB(), nullable=False, default=[]),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["execution_id"], ["executions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["run_id"], ["runs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["test_case_id"], ["test_cases.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("execution_id"),
    )
    op.create_index("ix_results_run_verdict", "results", ["run_id", "verdict"])
    op.create_index("ix_results_test_case_verdict", "results", ["test_case_id", "verdict"])

    # Create baselines table
    op.create_table(
        "baselines",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("suite_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("suite_version", sa.Integer(), nullable=False),
        sa.Column("run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("framework_version", sa.String(50), nullable=False),
        sa.Column("model_versions", postgresql.JSONB(), nullable=False, default={}),
        sa.Column("prompt_versions", postgresql.JSONB(), nullable=False, default={}),
        sa.Column("approved_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, default=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["approved_by"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["run_id"], ["runs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["suite_id"], ["test_suites.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_baselines_suite_active", "baselines", ["suite_id", "is_active"])

    # Create baseline_items table
    op.create_table(
        "baseline_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("baseline_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("test_case_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("verdict", sa.String(12), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("evidence", postgresql.JSONB(), nullable=False, default=[]),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["baseline_id"], ["baselines.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["test_case_id"], ["test_cases.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_baseline_items_baseline_id", "baseline_items", ["baseline_id"])

    # Create regressions table
    op.create_table(
        "regressions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("baseline_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("test_case_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("previous_verdict", sa.String(12), nullable=False),
        sa.Column("current_verdict", sa.String(12), nullable=False),
        sa.Column("regression_type", sa.String(30), nullable=False),
        sa.Column("severity", sa.String(10), nullable=False),
        sa.Column("evidence", postgresql.JSONB(), nullable=False, default=[]),
        sa.Column("acknowledged", sa.Boolean(), nullable=False, default=False),
        sa.Column("acknowledged_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("acknowledged_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["acknowledged_by"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["baseline_id"], ["baselines.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["run_id"], ["runs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["test_case_id"], ["test_cases.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_regressions_run_id", "regressions", ["run_id"])
    op.create_index("ix_regressions_severity", "regressions", ["severity"])

    # Create review_queue table
    op.create_table(
        "review_queue",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("regression_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("severity", sa.String(10), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("category", sa.String(50), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, default="pending"),
        sa.Column("label", sa.String(30), nullable=True),
        sa.Column("assigned_to", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("reviewed_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["assigned_to"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["regression_id"], ["regressions.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["reviewed_by"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["run_id"], ["runs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_review_queue_status", "review_queue", ["status"])
    op.create_index("ix_review_queue_severity", "review_queue", ["severity"])

    # Create audit_logs table
    op.create_table(
        "audit_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("action", sa.String(50), nullable=False),
        sa.Column("resource_type", sa.String(50), nullable=True),
        sa.Column("resource_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("details", postgresql.JSONB(), nullable=False, default={}),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column("user_agent", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_audit_logs_user_created", "audit_logs", ["user_id", "created_at"])
    op.create_index("ix_audit_logs_action", "audit_logs", ["action"])

    # Create model_configs table
    op.create_table(
        "model_configs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("provider", sa.String(50), nullable=False),
        sa.Column("model", sa.String(100), nullable=False),
        sa.Column("config", postgresql.JSONB(), nullable=False, default={}),
        sa.Column("is_active", sa.Boolean(), nullable=False, default=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("provider", "model", name="uq_model_config_provider_model"),
    )

    # Create prompt_versions table
    op.create_table(
        "prompt_versions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("type", sa.String(30), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False, default=1),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("variables", postgresql.JSONB(), nullable=False, default={}),
        sa.Column("status", sa.String(20), nullable=False, default="draft"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name", "version", name="uq_prompt_version_name_version"),
    )

    # Create feature_flags table
    op.create_table(
        "feature_flags",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("enabled", sa.Boolean(), nullable=False, default=False),
        sa.Column("rollout_percentage", sa.Integer(), nullable=False, default=0),
        sa.Column("target_roles", postgresql.JSONB(), nullable=False, default=[]),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )

    # Create attack_taxonomy table
    op.create_table(
        "attack_taxonomy",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("category", sa.String(50), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("severity", sa.String(10), nullable=False),
        sa.Column("templates", postgresql.JSONB(), nullable=False, default=[]),
        sa.Column("tags", postgresql.JSONB(), nullable=False, default=[]),
        sa.Column("is_active", sa.Boolean(), nullable=False, default=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_attack_taxonomy_category", "attack_taxonomy", ["category"])
    op.create_index("ix_attack_taxonomy_active", "attack_taxonomy", ["is_active"])


def downgrade() -> None:
    op.drop_table("attack_taxonomy")
    op.drop_table("feature_flags")
    op.drop_table("prompt_versions")
    op.drop_table("model_configs")
    op.drop_table("audit_logs")
    op.drop_table("review_queue")
    op.drop_table("regressions")
    op.drop_table("baseline_items")
    op.drop_table("baselines")
    op.drop_table("results")
    op.drop_table("executions")
    op.drop_table("runs")
    op.drop_table("test_case_versions")
    op.drop_table("test_cases")
    op.drop_table("test_suite_versions")
    op.drop_table("test_suites")
    op.drop_table("target_agents")
    op.drop_table("role_permissions")
    op.drop_table("user_roles")
    op.drop_table("permissions")
    op.drop_table("roles")
    op.drop_table("users")
