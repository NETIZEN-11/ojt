from enum import Enum


class TestCaseCategory(str, Enum):
    SMOKE = "smoke"
    SAFETY = "safety"
    JAILBREAK = "jailbreak"
    PROMPT_INJECTION = "prompt_injection"
    PII = "pii"
    POLICY = "policy"
    REFUSAL = "refusal"
    TOOL_USE = "tool_use"
    HALLUCINATION = "hallucination"
    BIAS = "bias"
    ADVERSARIAL = "adversarial"
    CUSTOM = "custom"


class TestCaseSeverity(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class ExpectedBehaviorType(str, Enum):
    EXACT_MATCH = "exact_match"
    REGEX_MATCH = "regex_match"
    KEYWORD_MATCH = "keyword_match"
    REFUSAL = "refusal"
    STRUCTURED_OUTPUT = "structured_output"
    LLM_RUBRIC = "llm_rubric"
    CUSTOM = "custom"


class Verdict(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    INCONCLUSIVE = "INCONCLUSIVE"


class RunStatus(str, Enum):
    QUEUED = "queued"
    VALIDATING = "validating"
    RUNNING = "running"
    SCORING = "scoring"
    DIFFING = "diffing"
    CLASSIFYING = "classifying"
    GATING = "gating"
    REVIEW_REQUIRED = "review_required"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ExecutionStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"
    INCONCLUSIVE = "inconclusive"


class RegressionType(str, Enum):
    PASS_TO_FAIL = "pass_to_fail"
    PASS_TO_INCONCLUSIVE = "pass_to_inconclusive"
    FAIL_TO_FAIL = "fail_to_fail"
    FAIL_TO_PASS = "fail_to_pass"
    INCONCLUSIVE_TO_FAIL = "inconclusive_to_fail"
    NEW_FAILURE = "new_failure"


class SeverityLevel(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class ReviewLabel(str, Enum):
    CONFIRMED_REGRESSION = "confirmed_regression"
    FALSE_POSITIVE = "false_positive"
    NON_BLOCKING = "non_blocking"
    NEEDS_ESCALATION = "needs_escalation"


class ReviewStatus(str, Enum):
    PENDING = "pending"
    IN_REVIEW = "in_review"
    RESOLVED = "resolved"
    ESCALATED = "escalated"


class GateDecision(str, Enum):
    PASS = "PASS"
    WARN = "WARN"
    FAIL = "FAIL"
    BLOCK = "BLOCK"


class GateExitCode(int, Enum):
    PASS = 0
    REGRESSION_FAILURE = 1
    INFRASTRUCTURE_FAILURE = 2


class ModelProvider(str, Enum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"
    COHERE = "cohere"
    MISTRAL = "mistral"
    LOCAL = "local"
    MOCK = "mock"


class PromptType(str, Enum):
    JUDGE_SYSTEM = "judge_system"
    JUDGE_USER = "judge_user"
    GENERATOR_SYSTEM = "generator_system"
    GENERATOR_USER = "generator_user"
    PLANNER_SYSTEM = "planner_system"
    PLANNER_USER = "planner_user"


class AuditAction(str, Enum):
    LOGIN = "login"
    LOGOUT = "logout"
    SUITE_CREATE = "suite_create"
    SUITE_UPDATE = "suite_update"
    SUITE_VERSION = "suite_version"
    BASELINE_APPROVE = "baseline_approve"
    BASELINE_ROLLBACK = "baseline_rollback"
    GATE_OVERRIDE = "gate_override"
    REVIEW_LABEL = "review_label"
    USER_CREATE = "user_create"
    USER_UPDATE = "user_update"
    ROLE_ASSIGN = "role_assign"
    MODEL_PROMOTE = "model_promote"
    PROMPT_PROMOTE = "prompt_promote"
    CONFIG_CHANGE = "config_change"
    RUN_CREATE = "run_create"
    RUN_CANCEL = "run_cancel"


class AgentStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    ERROR = "error"
    TESTING = "testing"


class PromptVersionStatus(str, Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    DEPRECATED = "deprecated"
    ARCHIVED = "archived"