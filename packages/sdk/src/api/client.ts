import axios, { AxiosInstance, AxiosRequestConfig, AxiosError } from "axios";
import type {
  PaginatedResponse,
  TestSuite,
  TestCase,
  TargetAgent,
  Run,
  Execution,
  Result,
  Baseline,
  BaselineItem,
  Regression,
  ReviewQueue,
  MatrixConfiguration,
  EvaluationMatrix,
  MatrixExecutionSummary,
  Dataset,
  DatasetVersion,
  DatasetSplit,
  PipelineConfig,
  PipelineResult,
  PipelineStatus,
  PipelineStep,
  MatrixConfig,
} from "../types";

interface ARTEFClientConfig {
  baseURL: string;
  timeout?: number;
  headers?: Record<string, string>;
}

interface LoginCredentials {
  username: string;
  password: string;
}

interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
}

class ARTEFClient {
  private client: AxiosInstance;
  private accessToken: string | null = null;
  private refreshToken: string | null = null;

  constructor(config: ARTEFClientConfig) {
    this.client = axios.create({
      baseURL: config.baseURL,
      timeout: config.timeout || 30000,
      headers: {
        "Content-Type": "application/json",
        ...config.headers,
      },
    });

    this.client.interceptors.request.use((config) => {
      if (this.accessToken) {
        config.headers.Authorization = `Bearer ${this.accessToken}`;
      }
      return config;
    });

    this.client.interceptors.response.use(
      (response) => response,
      async (error: AxiosError) => {
        const originalRequest = error.config as AxiosRequestConfig & { _retry?: boolean };

        if (error.response?.status === 401 && !originalRequest._retry && this.refreshToken) {
          originalRequest._retry = true;
          try {
            await this.refreshAccessToken();
            if (this.accessToken && originalRequest.headers) {
              originalRequest.headers.Authorization = `Bearer ${this.accessToken}`;
            }
            return this.client(originalRequest);
          } catch {
            this.accessToken = null;
            this.refreshToken = null;
          }
        }

        return Promise.reject(error);
      }
    );
  }

  async login(credentials: LoginCredentials): Promise<TokenResponse> {
    const response = await this.client.post<TokenResponse>("/api/v1/auth/login", credentials);
    this.accessToken = response.data.access_token;
    this.refreshToken = response.data.refresh_token;
    return response.data;
  }

  async refreshAccessToken(): Promise<void> {
    if (!this.refreshToken) {
      throw new Error("No refresh token available");
    }

    const response = await this.client.post<TokenResponse>("/api/v1/auth/refresh", {
      refresh_token: this.refreshToken,
    });

    this.accessToken = response.data.access_token;
    this.refreshToken = response.data.refresh_token;
  }

  async logout(): Promise<void> {
    this.accessToken = null;
    this.refreshToken = null;
  }

  setToken(token: string): void {
    this.accessToken = token;
  }

  getToken(): string | null {
    return this.accessToken;
  }

  // Suite operations
  async createSuite(data: { name: string; description?: string; test_cases?: any[] }): Promise<TestSuite> {
    const response = await this.client.post<TestSuite>("/api/v1/suites", data);
    return response.data;
  }

  async getSuite(id: string): Promise<TestSuite> {
    const response = await this.client.get<TestSuite>(`/api/v1/suites/${id}`);
    return response.data;
  }

  async listSuites(params?: { skip?: number; limit?: number }): Promise<PaginatedResponse<TestSuite>> {
    const response = await this.client.get<PaginatedResponse<TestSuite>>("/api/v1/suites", { params });
    return response.data;
  }

  async updateSuite(id: string, data: Partial<TestSuite>): Promise<TestSuite> {
    const response = await this.client.put<TestSuite>(`/api/v1/suites/${id}`, data);
    return response.data;
  }

  async deleteSuite(id: string): Promise<void> {
    await this.client.delete(`/api/v1/suites/${id}`);
  }

  async importSuite(file: string, format: "yaml" | "json" = "yaml"): Promise<TestSuite> {
    const fs = await import("fs");
    const content = fs.readFileSync(file, "utf-8");
    const contentType = file.endsWith(".yaml") || file.endsWith(".yml") ? "text/yaml" : "application/json";

    const response = await this.client.post<TestSuite>(
      `/api/v1/suites/import/${format}`,
      content,
      { headers: { "Content-Type": contentType } }
    );
    return response.data;
  }

  async exportSuite(id: string, format: "yaml" | "json" = "yaml"): Promise<string> {
    const response = await this.client.get(`/api/v1/suites/${id}/export`, {
      params: { format },
      responseType: "text",
    });
    return response.data;
  }

  // Test Case operations
  async createTestCase(suiteId: string, data: Omit<TestCase, "id" | "suite_id" | "created_at" | "updated_at">): Promise<TestCase> {
    const response = await this.client.post<TestCase>(`/api/v1/suites/${suiteId}/test-cases`, data);
    return response.data;
  }

  async getTestCase(suiteId: string, caseId: string): Promise<TestCase> {
    const response = await this.client.get<TestCase>(`/api/v1/suites/${suiteId}/test-cases/${caseId}`);
    return response.data;
  }

  async listTestCases(suiteId: string): Promise<TestCase[]> {
    const response = await this.client.get<TestCase[]>(`/api/v1/suites/${suiteId}/test-cases`);
    return response.data;
  }

  // Agent operations
  async createAgent(data: Omit<TargetAgent, "id" | "created_at" | "updated_at">): Promise<TargetAgent> {
    const response = await this.client.post<TargetAgent>("/api/v1/agents", data);
    return response.data;
  }

  async getAgent(id: string): Promise<TargetAgent> {
    const response = await this.client.get<TargetAgent>(`/api/v1/agents/${id}`);
    return response.data;
  }

  async listAgents(params?: { skip?: number; limit?: number }): Promise<PaginatedResponse<TargetAgent>> {
    const response = await this.client.get<PaginatedResponse<TargetAgent>>("/api/v1/agents", { params });
    return response.data;
  }

  async updateAgent(id: string, data: Partial<TargetAgent>): Promise<TargetAgent> {
    const response = await this.client.put<TargetAgent>(`/api/v1/agents/${id}`, data);
    return response.data;
  }

  async deleteAgent(id: string): Promise<void> {
    await this.client.delete(`/api/v1/agents/${id}`);
  }

  async testAgent(id: string, input: string): Promise<any> {
    const response = await this.client.post(`/api/v1/agents/${id}/test`, { input });
    return response.data;
  }

  // Run operations
  async createRun(data: {
    target_agent_id: string;
    suite_id: string;
    suite_version?: number;
    baseline_id?: string;
  }): Promise<Run> {
    const response = await this.client.post<Run>("/api/v1/runs", data);
    return response.data;
  }

  async getRun(id: string): Promise<Run> {
    const response = await this.client.get<Run>(`/api/v1/runs/${id}`);
    return response.data;
  }

  async listRuns(params?: { skip?: number; limit?: number; status?: string; target_agent_id?: string; suite_id?: string }): Promise<PaginatedResponse<Run>> {
    const response = await this.client.get<PaginatedResponse<Run>>("/api/v1/runs", { params });
    return response.data;
  }

  async getRunExecutions(runId: string): Promise<Execution[]> {
    const response = await this.client.get<Execution[]>(`/api/v1/runs/${runId}/executions`);
    return response.data;
  }

  async getRunResults(runId: string): Promise<Result[]> {
    const response = await this.client.get<Result[]>(`/api/v1/runs/${runId}/results`);
    return response.data;
  }

  async cancelRun(runId: string): Promise<void> {
    await this.client.post(`/api/v1/runs/${runId}/cancel`);
  }

  // Result operations
  async getResult(id: string): Promise<Result> {
    const response = await this.client.get<Result>(`/api/v1/results/${id}`);
    return response.data;
  }

  // Baseline operations
  async createBaseline(data: {
    suite_id: string;
    suite_version: number;
    run_id: string;
    name: string;
    description?: string;
  }): Promise<Baseline> {
    const response = await this.client.post<Baseline>("/api/v1/baselines", data);
    return response.data;
  }

  async getBaseline(id: string): Promise<Baseline> {
    const response = await this.client.get<Baseline>(`/api/v1/baselines/${id}`);
    return response.data;
  }

  async listBaselines(params?: { suite_id?: string; active?: boolean }): Promise<Baseline[]> {
    const response = await this.client.get<Baseline[]>("/api/v1/baselines", { params });
    return response.data;
  }

  async approveBaseline(id: string): Promise<Baseline> {
    const response = await this.client.post<Baseline>(`/api/v1/baselines/${id}/approve`);
    return response.data;
  }

  async deactivateBaseline(id: string): Promise<Baseline> {
    const response = await this.client.post<Baseline>(`/api/v1/baselines/${id}/deactivate`);
    return response.data;
  }

  async deleteBaseline(id: string): Promise<void> {
    await this.client.delete(`/api/v1/baselines/${id}`);
  }

  async getBaselineItems(baselineId: string): Promise<BaselineItem[]> {
    const response = await this.client.get<BaselineItem[]>(`/api/v1/baselines/${baselineId}/items`);
    return response.data;
  }

  // Regression operations
  async getRegression(id: string): Promise<Regression> {
    const response = await this.client.get<Regression>(`/api/v1/regressions/${id}`);
    return response.data;
  }

  async listRegressions(runId: string): Promise<Regression[]> {
    const response = await this.client.get<Regression[]>(`/api/v1/regressions?run_id=${runId}`);
    return response.data;
  }

  async acknowledgeRegression(id: string): Promise<Regression> {
    const response = await this.client.post<Regression>(`/api/v1/regressions/${id}/acknowledge`);
    return response.data;
  }

  // Review operations
  async listReviews(params?: { status?: string; severity?: string }): Promise<ReviewQueue[]> {
    const response = await this.client.get<ReviewQueue[]>("/api/v1/reviews", { params });
    return response.data;
  }

  async getReview(id: string): Promise<ReviewQueue> {
    const response = await this.client.get<ReviewQueue>(`/api/v1/reviews/${id}`);
    return response.data;
  }

  async updateReview(id: string, data: { label?: string; notes?: string; assigned_to?: string }): Promise<ReviewQueue> {
    const response = await this.client.patch<ReviewQueue>(`/api/v1/reviews/${id}`, data);
    return response.data;
  }

  // Report operations
  async generateReport(data: {
    run_id: string;
    format: "json" | "markdown" | "html";
    type: "full" | "summary";
  }): Promise<any> {
    const response = await this.client.post<any>("/api/v1/reports", data);
    return response.data;
  }

  async listReports(): Promise<any[]> {
    const response = await this.client.get<any[]>("/api/v1/reports");
    return response.data;
  }

  async downloadReport(reportId: string): Promise<string> {
    const response = await this.client.get(`/api/v1/reports/${reportId}/download`, {
      responseType: "text",
    });
    return response.data;
  }

  // Evaluation operations
  async evaluateRAG(data: {
    query: string;
    answer: string;
    retrieved_docs: Array<Record<string, unknown>>;
    ground_truth_docs?: string[];
  }): Promise<any> {
    const response = await this.client.post<any>("/api/v1/evaluate/rag", data);
    return response.data;
  }

  async evaluateAgent(data: {
    trajectory: Array<Record<string, unknown>>;
    expected_final_answer?: string;
    expected_tool_calls?: Array<Record<string, unknown>>;
  }): Promise<any> {
    const response = await this.client.post<any>("/api/v1/evaluate/agent", data);
    return response.data;
  }

  async evaluatePrompt(data: {
    prompt_id: string;
    prompt_version: string;
    content: string;
  }): Promise<any> {
    const response = await this.client.post<any>("/api/v1/evaluate/prompt", data);
    return response.data;
  }

  async comparePrompts(data: {
    prompt_a_id: string;
    prompt_a_version: string;
    content_a: string;
    prompt_b_id: string;
    prompt_b_version: string;
    content_b: string;
    models?: string[];
    datasets?: string[];
  }): Promise<any> {
    const response = await this.client.post<any>("/api/v1/evaluate/prompt/compare", data);
    return response.data;
  }

  // Security operations
  async scanModel(modelPath: string): Promise<any> {
    const response = await this.client.post<any>("/api/v1/security/scan-model", { model_path: modelPath });
    return response.data;
  }

  // Cost tracking
  async getCostSummary(days: number = 30): Promise<any> {
    const response = await this.client.get<any>(`/api/v1/cost/summary?days=${days}`);
    return response.data;
  }

  // Red-team operations
  async generateAttacks(data: {
    category?: string;
    batch_size?: number;
    novelty_threshold?: number;
  }): Promise<any> {
    const response = await this.client.post<any>("/api/v1/redteam/generate", data);
    return response.data;
  }

  async runRedTeam(data: {
    agent_id: string;
    suite_id?: string;
    max_turns?: number;
  }): Promise<any> {
    const response = await this.client.post<any>("/api/v1/redteam/run", data);
    return response.data;
  }

  // Health check
  async healthCheck(): Promise<{ status: string; service: string }> {
    const response = await this.client.get<{ status: string; service: string }>("/api/v1/health/health");
    return response.data;
  }

  async readinessCheck(): Promise<{ ready: boolean; checks: Record<string, boolean> }> {
    const response = await this.client.get<{ ready: boolean; checks: Record<string, boolean> }>("/api/v1/health/ready");
    return response.data;
  }

  // =========================================================================
  // Higher-level Evaluation Orchestration API
  // =========================================================================

  // Dataset operations
  async createDataset(data: {
    name: string;
    description?: string;
    source_type?: string;
    source_config?: Record<string, any>;
    schema?: Record<string, any>;
    split_config?: Record<string, any>;
    status?: "draft" | "active" | "archived";
  }): Promise<Dataset> {
    const response = await this.client.post<Dataset>("/api/v1/datasets", data);
    return response.data;
  }

  async getDataset(id: string): Promise<Dataset> {
    const response = await this.client.get<Dataset>(`/api/v1/datasets/${id}`);
    return response.data;
  }

  async listDatasets(params?: { status?: string; skip?: number; limit?: number }): Promise<PaginatedResponse<Dataset>> {
    const response = await this.client.get<PaginatedResponse<Dataset>>("/api/v1/datasets", { params });
    return response.data;
  }

  async createDatasetVersion(datasetId: string, changelog?: string): Promise<DatasetVersion> {
    const response = await this.client.post<DatasetVersion>(`/api/v1/datasets/${datasetId}/versions`, { changelog });
    return response.data;
  }

  async getDatasetVersion(datasetId: string, versionId: string): Promise<DatasetVersion> {
    const response = await this.client.get<DatasetVersion>(`/api/v1/datasets/${datasetId}/versions/${versionId}`);
    return response.data;
  }

  async listDatasetVersions(datasetId: string): Promise<DatasetVersion[]> {
    const response = await this.client.get<DatasetVersion[]>(`/api/v1/datasets/${datasetId}/versions`);
    return response.data;
  }

  async getDatasetSplit(datasetId: string, versionId: string, splitName: string): Promise<DatasetSplit> {
    const response = await this.client.get<DatasetSplit>(`/api/v1/datasets/${datasetId}/versions/${versionId}/splits/${splitName}`);
    return response.data;
  }

  async uploadDatasetFile(datasetId: string, file: File): Promise<{ message: string; dataset_id: string }> {
    const formData = new FormData();
    formData.append("file", file);
    const response = await this.client.post(`/api/v1/datasets/${datasetId}/upload`, formData, {
      headers: { "Content-Type": "multipart/form-data" },
    });
    return response.data;
  }

  // Matrix operations
  async createMatrix(data: {
    name: string;
    suite_id: string;
    test_case_ids: string[];
    configurations: MatrixConfiguration[];
    description?: string;
  }): Promise<EvaluationMatrix> {
    const response = await this.client.post<EvaluationMatrix>("/api/v1/matrices", data);
    return response.data;
  }

  async getMatrix(id: string): Promise<EvaluationMatrix> {
    const response = await this.client.get<EvaluationMatrix>(`/api/v1/matrices/${id}`);
    return response.data;
  }

  async listMatrices(params?: { suite_id?: string; status?: string; skip?: number; limit?: number }): Promise<PaginatedResponse<EvaluationMatrix>> {
    const response = await this.client.get<PaginatedResponse<EvaluationMatrix>>("/api/v1/matrices", { params });
    return response.data;
  }

  async getMatrixSummary(id: string): Promise<MatrixExecutionSummary> {
    const response = await this.client.get<MatrixExecutionSummary>(`/api/v1/matrices/${id}/summary`);
    return response.data;
  }

  async executeMatrix(id: string): Promise<EvaluationMatrix> {
    const response = await this.client.post<EvaluationMatrix>(`/api/v1/matrices/${id}/execute`);
    return response.data;
  }

  async listMatrixCells(matrixId: string, status?: string): Promise<any[]> {
    const response = await this.client.get(`/api/v1/matrices/${matrixId}/cells`, { params: { status } });
    return response.data;
  }

  async getMatrixCell(matrixId: string, cellId: string): Promise<any> {
    const response = await this.client.get(`/api/v1/matrices/${matrixId}/cells/${cellId}`);
    return response.data;
  }

  // Pipeline operations
  async runPipeline(config: PipelineConfig): Promise<PipelineResult> {
    const response = await this.client.post<PipelineResult>("/api/v1/pipelines", config);
    return response.data;
  }

  async getPipelineStatus(pipelineId: string): Promise<PipelineResult> {
    const response = await this.client.get<PipelineResult>(`/api/v1/pipelines/${pipelineId}`);
    return response.data;
  }

  async listPipelines(params?: { status?: string; skip?: number; limit?: number }): Promise<PaginatedResponse<PipelineResult>> {
    const response = await this.client.get<PaginatedResponse<PipelineResult>>("/api/v1/pipelines", { params });
    return response.data;
  }

  async rerunPipeline(pipelineId: string): Promise<PipelineResult> {
    const response = await this.client.post<PipelineResult>(`/api/v1/pipelines/${pipelineId}/rerun`);
    return response.data;
  }

  // Prompt version operations
  async listPrompts(): Promise<any[]> {
    const response = await this.client.get("/api/v1/settings/prompts");
    return response.data;
  }

  async promotePrompt(promptType: string, version: string): Promise<any> {
    const response = await this.client.post("/api/v1/settings/prompts/promote", {
      prompt_type: promptType,
      version: version,
    });
    return response.data;
  }

  async deprecatePrompt(promptType: string, version: string): Promise<any> {
    const response = await this.client.post("/api/v1/settings/prompts/deprecate", {
      prompt_type: promptType,
      version: version,
    });
    return response.data;
  }

  async archivePrompt(promptType: string, version: string): Promise<any> {
    const response = await this.client.post("/api/v1/settings/prompts/archive", {
      prompt_type: promptType,
      version: version,
    });
    return response.data;
  }

  async diffPrompts(promptType: string, versionA: string, versionB: string): Promise<any> {
    const response = await this.client.post("/api/v1/settings/prompts/diff", {
      prompt_type: promptType,
      version_a: versionA,
      version_b: versionB,
    });
    return response.data;
  }

  // Release Decision
  async getReleaseDecision(runId: string): Promise<{ decision: string; exit_code: number; details: any }> {
    const run = await this.getRun(runId);
    return {
      decision: run.status === "completed" ? "READY" : 
               run.status === "review_required" ? "NEEDS_REVIEW" : "BLOCKED",
      exit_code: run.status === "completed" ? 0 : 1,
      details: run,
    };
  }

  // =========================================================================
  // High-level Evaluation Workflow Methods
  // =========================================================================

  /**
   * Run a complete evaluation pipeline with the given configuration.
   * This is the main entry point for running evaluations.
   */
  async runEvaluation(config: {
    name: string;
    description?: string;
    suite_id: string;
    target_agent_id: string;
    dataset_id?: string;
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
    tags?: string[];
  }): Promise<PipelineResult> {
    // Create pipeline config
    const pipelineConfig: PipelineConfig = {
      name: config.name,
      description: config.description,
      suite_id: config.suite_id,
      target_agent_id: config.target_agent_id,
      models: config.models,
      prompt_versions: config.prompt_versions.map(id => id),
      provider_configs: config.provider_configs || [],
      judge_config: config.judge_config,
      redteam_config: config.redteam_config,
      baseline_id: config.baseline_id,
      auto_baseline: config.auto_baseline || false,
      gate_config: config.gate_config,
      cost_limit_usd: config.cost_limit_usd,
      max_parallel_cells: config.max_parallel_cells || 4,
      timeout_seconds: config.timeout_seconds || 3600,
    };

    if (config.dataset_id) {
      pipelineConfig.dataset_id = config.dataset_id;
    }

    return this.runPipeline(pipelineConfig);
  }

  /**
   * Wait for a pipeline to complete and return the final result.
   */
  async waitForPipeline(pipelineId: string, pollIntervalMs: number = 5000): Promise<PipelineResult> {
    while (true) {
      const result = await this.getPipelineStatus(pipelineId);
      if (result.status === "completed" || result.status === "failed" || result.status === "cancelled") {
        return result;
      }
      await new Promise(resolve => setTimeout(resolve, pollIntervalMs));
    }
  }

  /**
   * Run an evaluation and wait for completion.
   */
  async runEvaluationAndWait(config: Parameters<typeof this.runEvaluation>[0]): Promise<PipelineResult> {
    const result = await this.runEvaluation(config);
    return this.waitForPipeline(result.pipeline_id);
  }

  /**
   * Generate a comprehensive evaluation report for a pipeline run.
   */
  async generatePipelineReport(pipelineId: string, format: "json" | "markdown" | "html" = "json"): Promise<any> {
    const result = await this.getPipelineStatus(pipelineId);
    const runIds = result.metadata?.run_ids || [];
    
    if (runIds.length === 0) {
      throw new Error("No runs found for this pipeline");
    }
    
    // Generate report for the first run (or could aggregate all)
    return this.generateReport({
      run_id: runIds[0],
      format,
      type: "full",
    });
  }
}

export { ARTEFClient };
export type { ARTEFClientConfig, LoginCredentials, TokenResponse, PipelineConfig, PipelineResult, PipelineStatus, PipelineStep, MatrixConfig, MatrixConfiguration, EvaluationMatrix, MatrixExecutionSummary, Dataset, DatasetVersion, DatasetSplit };