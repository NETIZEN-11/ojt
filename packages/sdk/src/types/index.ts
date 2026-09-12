export interface UUID {
  value: string;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  skip: number;
  limit: number;
}

export interface TestCase {
  id: string;
  suite_id: string;
  version: number;
  test_case_id: string;
  category: string;
  severity: "critical" | "high" | "medium" | "low";
  input: string;
  expected_behavior: ExpectedBehavior;
  metadata: Record<string, unknown>;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface ExpectedBehavior {
  type: ExpectedBehaviorType;
  matcher?: MatcherConfig;
  rubric?: LLMRubric;
}

export type ExpectedBehaviorType =
  | "exact_match"
  | "regex_match"
  | "keyword_match"
  | "refusal"
  | "llm_rubric";

export interface MatcherConfig {
  type: ExpectedBehaviorType;
  pattern?: string;
  keywords?: string[];
  case_sensitive?: boolean;
  regex_timeout_ms?: number;
  expected_keys?: string[];
  required_fields?: Record<string, unknown>;
}

export interface LLMRubric {
  criteria: LLMRubricCriterion[];
  overall_threshold: number;
  require_evidence: boolean;
}

export interface LLMRubricCriterion {
  name: string;
  description: string;
  weight: number;
  pass_threshold: number;
}

export interface TestSuite {
  id: string;
  name: string;
  description: string | null;
  version: number;
  schema_version: string;
  is_active: boolean;
  test_cases: TestCase[];
  created_at: string;
  updated_at: string;
  created_by: string | null;
}

export interface TargetAgent {
  id: string;
  name: string;
  description: string | null;
  endpoint_url: string;
  auth_config: Record<string, unknown>;
  request_template: Record<string, unknown> | null;
  response_extraction: Record<string, unknown> | null;
  timeout_seconds: number;
  max_retries: number;
  allowed: boolean;
  status: "active" | "inactive" | "testing";
  created_at: string;
  updated_at: string;
  created_by: string | null;
}

export interface Run {
  id: string;
  target_agent_id: string;
  suite_id: string;
  suite_version: number;
  baseline_id: string | null;
  status:
    | "queued"
    | "running"
    | "scoring"
    | "diffing"
    | "gating"
    | "completed"
    | "failed"
    | "cancelled"
    | "review_required";
  framework_version: string;
  model_versions: Record<string, string>;
  prompt_versions: Record<string, string>;
  config_snapshot: Record<string, unknown>;
  started_at: string | null;
  completed_at: string | null;
  total_tests: number;
  passed_count: number;
  failed_count: number;
  inconclusive_count: number;
  regression_count: number;
  critical_count: number;
  high_count: number;
  medium_count: number;
  low_count: number;
  total_cost_usd: number;
  total_latency_ms: number;
  error_message: string | null;
  created_at: string;
  updated_at: string;
  created_by: string | null;
}

export interface Execution {
  id: string;
  run_id: string;
  test_case_id: string;
  status: "queued" | "running" | "completed" | "failed";
  target_request: Record<string, unknown> | null;
  target_response: Record<string, unknown> | null;
  tool_calls: Array<Record<string, unknown>>;
  started_at: string | null;
  completed_at: string | null;
  latency_ms: number;
  error: string | null;
  retry_count: number;
}

export interface Result {
  id: string;
  execution_id: string;
  run_id: string;
  test_case_id: string;
  verdict: "PASS" | "FAIL" | "INCONCLUSIVE";
  confidence: number;
  matcher_used: string | null;
  judge_output: Record<string, unknown> | null;
  second_judge_output: Record<string, unknown> | null;
  judge_agreement: boolean;
  evidence: Array<Record<string, unknown>>;
  execution_time_ms: number;
  tokens_used: number;
  estimated_cost: number;
  errors: string[];
  created_at: string;
}

export interface Baseline {
  id: string;
  suite_id: string;
  suite_version: number;
  run_id: string;
  name: string;
  description: string | null;
  framework_version: string;
  model_versions: Record<string, string>;
  prompt_versions: Record<string, string>;
  approved_by: string;
  approved_at: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface BaselineItem {
  id: string;
  baseline_id: string;
  test_case_id: string;
  verdict: "PASS" | "FAIL" | "INCONCLUSIVE";
  confidence: number;
  evidence: Array<Record<string, unknown>>;
  created_at: string;
}

export interface Regression {
  id: string;
  run_id: string;
  baseline_id: string;
  test_case_id: string;
  previous_verdict: "PASS" | "FAIL" | "INCONCLUSIVE";
  current_verdict: "PASS" | "FAIL" | "INCONCLUSIVE";
  regression_type: string;
  severity: "critical" | "high" | "medium" | "low";
  evidence: Array<Record<string, unknown>>;
  acknowledged: boolean;
  acknowledged_by: string | null;
  acknowledged_at: string | null;
  created_at: string;
}

export interface ReviewQueue {
  id: string;
  run_id: string;
  regression_id: string | null;
  severity: "critical" | "high" | "medium" | "low";
  confidence: number;
  category: string;
  status: "pending" | "in_review" | "resolved" | "escalated";
  label: string | null;
  assigned_to: string | null;
  reviewed_by: string | null;
  reviewed_at: string | null;
  notes: string | null;
  created_at: string;
  updated_at: string;
  resolved_at: string | null;
}

export interface EvaluationConfig {
  name: string;
  description?: string;
  suite_id: string;
  target_agent_id: string;
  baseline_id?: string;
  models?: string[];
  judge_config?: JudgeConfig;
  redteam_config?: RedTeamConfig;
  cost_limits?: CostLimits;
}

export interface JudgeConfig {
  provider: string;
  model: string;
  temperature: number;
  max_tokens: number;
  confidence_threshold: number;
  double_score: boolean;
  retry_on_schema_error: boolean;
}

export interface RedTeamConfig {
  enabled: boolean;
  categories: string[];
  max_turns: number;
  turn_timeout_seconds: number;
  novelty_threshold: number;
}

export interface CostLimits {
  per_run_limit_usd: number;
  daily_limit_usd: number;
}

export interface GateResult {
  decision: "PASS" | "WARN" | "BLOCK" | "FAIL";
  exit_code: number;
  critical_count: number;
  high_count: number;
  medium_count: number;
  low_count: number;
  inconclusive_count: number;
}

export interface RAGEvaluationResult {
  test_case_id: string;
  query: string;
  answer: string;
  retrieved_docs: Array<Record<string, unknown>>;
  ground_truth_docs: string[];
  retrieval_result: {
    test_case_id: string;
    query: string;
    retrieved_docs: Array<Record<string, unknown>>;
    ground_truth_docs: string[];
    metrics: {
      relevant_docs: number;
      retrieved_docs: number;
      precision: number;
      recall: number;
      f1_score: number;
      mrr: number;
      ndcg: number;
    };
    execution_time_ms: number;
    errors: string[];
  };
  generation_result: {
    test_case_id: string;
    query: string;
    answer: string;
    context: string[];
    metrics: {
      faithfulness: number;
      answer_relevance: number;
      context_recall: number;
      context_precision: number;
      factuality: number;
      hallucination_rate: number;
    };
    execution_time_ms: number;
    errors: string[];
  };
  overall_score: number;
  execution_time_ms: number;
  errors: string[];
}

export interface AgentEvaluationResult {
  test_case_id: string;
  trajectory_evaluation: {
    test_case_id: string;
    trajectory: Array<Record<string, unknown>>;
    metrics: {
      step_count: number;
      valid_tool_calls: number;
      invalid_tool_calls: number;
      unauthorized_tool_calls: number;
      tool_selection_accuracy: number;
      argument_validity: number;
      trajectory_coherence: number;
      goal_achievement: number;
    };
    execution_time_ms: number;
    errors: string[];
  };
  tool_call_evaluation: {
    test_case_id: string;
    tool_calls: Array<{
      correct_tool_selected: boolean;
      arguments_valid: boolean;
      result_processed: boolean;
      execution_time_ms: number;
      error: string | null;
    }>;
    overall_accuracy: number;
    execution_time_ms: number;
    errors: string[];
  };
  overall_score: number;
  execution_time_ms: number;
  errors: string[];
}

export interface PromptEvaluationResult {
  prompt_id: string;
  prompt_version: string;
  content: string;
  metrics: {
    quality_score: number;
    clarity_score: number;
    specificity_score: number;
    safety_score: number;
    token_efficiency: number;
  };
  execution_time_ms: number;
  errors: string[];
}

export interface PromptComparisonResult {
  prompt_a_id: string;
  prompt_a_version: string;
  prompt_b_id: string;
  prompt_b_version: string;
  winner: "A" | "B" | "TIE";
  score_difference: number;
  metrics_a: Record<string, number>;
  metrics_b: Record<string, number>;
  cross_model_results: Record<string, unknown>;
  execution_time_ms: number;
  errors: string[];
}

export interface ScanReport {
  model_id: string;
  model_path: string;
  scan_status: "completed" | "partial" | "failed";
  findings: Array<{
    detector: string;
    finding_type: string;
    severity: "info" | "low" | "medium" | "high" | "critical";
    description: string;
    file_path: string;
    line_number: number | null;
    metadata: Record<string, unknown>;
    timestamp: string;
  }>;
  errors: string[];
  scan_duration_ms: number;
  timestamp: string;
}

export interface CostEntry {
  id: string;
  run_id: string | null;
  test_case_id: string | null;
  category:
    | "llm_inference"
    | "embedding"
    | "judge"
    | "red_team"
    | "retrieval"
    | "vector_store"
    | "storage"
    | "compute";
  provider: string;
  model: string;
  input_tokens: number;
  output_tokens: number;
  total_tokens: number;
  cost_usd: number;
  currency: string;
  timestamp: string;
  metadata: Record<string, unknown>;
}

export interface CostSummary {
  total_cost_usd: number;
  total_input_tokens: number;
  total_output_tokens: number;
  total_tokens: number;
  by_category: Record<string, number>;
  by_provider: Record<string, number>;
  by_model: Record<string, number>;
  by_run: Record<string, number>;
  period_start: string;
  period_end: string;
}

// Matrix types
export interface MatrixConfig {
  name: string;
  description?: string;
  suite_id: string;
  test_case_ids: string[];
  configurations: MatrixConfiguration[];
}

export interface MatrixConfiguration {
  model_id: string;
  model_provider: string;
  model_parameters?: Record<string, any>;
  prompt_version_id?: string;
  prompt_variables?: Record<string, any>;
  dataset_id?: string;
  dataset_version?: number;
  dataset_split?: string;
  provider_config?: Record<string, any>;
  judge_config?: Record<string, any>;
  redteam_config?: Record<string, any>;
  max_retries?: number;
  timeout_seconds?: number;
  tags?: string[];
  metadata?: Record<string, any>;
}

export interface EvaluationMatrix {
  id: string;
  name: string;
  description?: string;
  suite_id: string;
  suite_version: number;
  test_case_ids: string[];
  configurations: MatrixConfiguration[];
  cells: any[];
  status: string;
  total_cells: number;
  completed_cells: number;
  failed_cells: number;
  created_at: string;
  updated_at: string;
  created_by: string | null;
}

export interface MatrixExecutionSummary {
  matrix_id: string;
  total_cells: number;
  completed_cells: number;
  failed_cells: number;
  queued_cells: number;
  running_cells: number;
  overall_status: string;
  cells: any[];
}

// Dataset types
export interface Dataset {
  id: string;
  name: string;
  description?: string;
  status: "draft" | "active" | "archived";
  source_type: string;
  source_config: Record<string, any>;
  schema: Record<string, any>;
  split_config: Record<string, any>;
  total_records: number;
  current_version: number;
  created_at: string;
  updated_at: string;
}

export interface DatasetVersion {
  id: string;
  dataset_id: string;
  version: number;
  snapshot: Record<string, any>;
  changelog?: string;
  split_sizes: Record<string, number>;
  total_records: number;
  checksum: string;
  created_at: string;
  created_by?: string;
}

export interface DatasetSplit {
  id: string;
  dataset_version_id: string;
  split_name: string;
  records: Array<Record<string, any>>;
  record_indices: number[];
  created_at: string;
}

// Pipeline types
export interface PipelineConfig {
  name: string;
  description?: string;
  suite_id: string;
  suite_version?: number;
  target_agent_id: string;
  dataset_id?: string;
  dataset_version?: number;
  models: Array<{
    model_id: string;
    provider: string;
    parameters?: Record<string, any>;
  }>;
  prompt_versions: string[];
  provider_configs?: Array<Record<string, any>>;
  judge_config?: Record<string, any>;
  redteam_config?: Record<string, any>;
  baseline_id?: string;
  auto_baseline?: boolean;
  gate_config?: Record<string, any>;
  cost_limit_usd?: number;
  max_parallel_cells?: number;
  timeout_seconds?: number;
}

export interface PipelineStep {
  name: string;
  status: "pending" | "running" | "completed" | "failed" | "skipped";
  started_at?: string;
  completed_at?: string;
  error?: string;
  metadata?: Record<string, any>;
}

export interface PipelineResult {
  pipeline_id: string;
  status: "queued" | "validating" | "building_matrix" | "scheduling" | "executing" | 
    "aggregating" | "comparing_baseline" | "classifying_severity" | "evaluating_gate" | 
    "awaiting_review" | "completed" | "failed" | "cancelled";
  config: PipelineConfig;
  started_at?: string;
  completed_at?: string;
  total_duration_seconds?: number;
  total_cells: number;
  completed_cells: number;
  failed_cells: number;
  passed_count: number;
  failed_count: number;
  inconclusive_count: number;
  regression_count: number;
  critical_count: number;
  high_count: number;
  medium_count: number;
  low_count: number;
  total_cost_usd: number;
  gate_decision?: string;
  gate_exit_code?: number;
  release_decision?: "READY" | "WARNING" | "NEEDS_REVIEW" | "BLOCKED";
  review_required: boolean;
  review_ids: string[];
  steps: PipelineStep[];
  error?: string;
  metadata: Record<string, any>;
}

export type PipelineStatus = 
  | "queued" | "validating" | "building_matrix" | "scheduling" | "executing" 
  | "aggregating" | "comparing_baseline" | "classifying_severity" | "evaluating_gate" 
  | "awaiting_review" | "completed" | "failed" | "cancelled";

// Dataset types
export interface Dataset {
  id: string;
  name: string;
  description?: string;
  status: "draft" | "active" | "archived";
  source_type: string;
  source_config: Record<string, any>;
  schema: Record<string, any>;
  split_config: Record<string, any>;
  total_records: number;
  current_version: number;
  created_at: string;
  updated_at: string;
}

export interface DatasetVersion {
  id: string;
  dataset_id: string;
  version: number;
  snapshot: Record<string, any>;
  changelog?: string;
  split_sizes: Record<string, number>;
  total_records: number;
  checksum: string;
  created_at: string;
  created_by?: string;
}

export interface DatasetSplit {
  id: string;
  dataset_version_id: string;
  split_name: string;
  records: Array<Record<string, any>>;
  record_indices: number[];
  created_at: string;
}