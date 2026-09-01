"use client";

import { useEffect, useState, useCallback } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Badge } from "@/components/ui/badge";
import { api } from "@/lib/api";
import { formatDate, formatDuration, formatCost, getSeverityColor } from "@/lib/utils";
import { useAuth } from "@/lib/auth";
import { useParams } from "next/navigation";

interface RunDetail {
  id: string;
  target_agent_id: string;
  suite_id: string;
  suite_version: number;
  baseline_id: string | null;
  status: string;
  framework_version: string;
  model_versions: Record<string, string>;
  prompt_versions: Record<string, string>;
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
  started_at: string | null;
  completed_at: string | null;
  created_at: string;
  error_message: string | null;
}

interface ResultDetail {
  id: string;
  test_case_id: string;
  verdict: string;
  confidence: number;
  matcher_used: string | null;
  judge_output: unknown;
  second_judge_output: unknown;
  judge_agreement: boolean;
  evidence: unknown[];
  execution_time_ms: number;
  tokens_used: number;
  estimated_cost: number;
  errors: string[];
}

interface RegressionDetail {
  id: string;
  test_case_id: string;
  previous_verdict: string;
  current_verdict: string;
  regression_type: string;
  severity: string;
  evidence: unknown[];
}

export default function RunDetailPage() {
  const params = useParams();
  const runId = params.id as string;
  const { isAuthenticated, isLoading } = useAuth();
  const [run, setRun] = useState<RunDetail | null>(null);
  const [results, setResults] = useState<ResultDetail[]>([]);
  const [regressions, setRegressions] = useState<RegressionDetail[]>([]);

  const fetchData = useCallback(async () => {
    try {
      const [runRes, resultsRes, regsRes] = await Promise.all([
        api.get(`/runs/${runId}`),
        api.get(`/results/run/${runId}`),
        api.get(`/regressions/run/${runId}`),
      ]);
      setRun(runRes.data);
      setResults(resultsRes.data);
      setRegressions(regsRes.data);
    } catch (error) {
      console.error("Failed to fetch run detail:", error);
    }
  }, [runId]);

  useEffect(() => {
    if (!isLoading) {
      if (!isAuthenticated) {
        window.location.href = "/login";
      } else {
        fetchData();
      }
    }
  }, [isAuthenticated, isLoading, runId, fetchData]);

  if (isLoading || !isAuthenticated) {
    return <div className="flex h-screen items-center justify-center"><div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div></div>;
  }

  if (!run) {
    return <div className="p-6 text-center">Run not found</div>;
  }

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Run Details</h1>
          <p className="text-muted-foreground">{run.id}</p>
        </div>
        <div className="flex gap-2">
          <Badge variant={run.status === "completed" ? "default" : run.status === "failed" ? "destructive" : "secondary"}>
            {run.status.replace("_", " ").toUpperCase()}
          </Badge>
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-4">
        <Card><CardContent><div className="text-2xl font-bold">{run.total_tests}</div><p className="text-sm text-muted-foreground">Total Tests</p></CardContent></Card>
        <Card><CardContent><div className="text-2xl font-bold text-green-600">{run.passed_count}</div><p className="text-sm text-muted-foreground">Passed</p></CardContent></Card>
        <Card><CardContent><div className="text-2xl font-bold text-red-600">{run.failed_count}</div><p className="text-sm text-muted-foreground">Failed</p></CardContent></Card>
        <Card><CardContent><div className="text-2xl font-bold text-yellow-600">{run.inconclusive_count}</div><p className="text-sm text-muted-foreground">Inconclusive</p></CardContent></Card>
      </div>

      <Tabs defaultValue="overview" className="space-y-4">
        <TabsList>
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="results">Results ({results.length})</TabsTrigger>
          <TabsTrigger value="regressions">Regressions ({regressions.length})</TabsTrigger>
          <TabsTrigger value="config">Configuration</TabsTrigger>
        </TabsList>

        <TabsContent value="overview">
          <div className="grid gap-4 md:grid-cols-2">
            <Card>
              <CardHeader><CardTitle>Run Information</CardTitle></CardHeader>
              <CardContent className="space-y-2">
                <div className="grid grid-cols-2 gap-2 text-sm">
                  <span>Framework Version</span><span className="font-medium">{run.framework_version}</span>
                  <span>Suite Version</span><span className="font-medium">{run.suite_version}</span>
                  <span>Total Cost</span><span className="font-medium">{formatCost(run.total_cost_usd)}</span>
                  <span>Total Latency</span><span className="font-medium">{formatDuration(run.total_latency_ms)}</span>
                  <span>Started</span><span className="font-medium">{run.started_at ? formatDate(run.started_at) : "N/A"}</span>
                  <span>Completed</span><span className="font-medium">{run.completed_at ? formatDate(run.completed_at) : "N/A"}</span>
                </div>
              </CardContent>
            </Card>
            <Card>
              <CardHeader><CardTitle>Severity Breakdown</CardTitle></CardHeader>
              <CardContent className="space-y-2">
                {run.critical_count > 0 && <div className="flex justify-between"><span>Critical</span><Badge className="bg-red-100 text-red-800">{run.critical_count}</Badge></div>}
                {run.high_count > 0 && <div className="flex justify-between"><span>High</span><Badge className="bg-orange-100 text-orange-800">{run.high_count}</Badge></div>}
                {run.medium_count > 0 && <div className="flex justify-between"><span>Medium</span><Badge className="bg-yellow-100 text-yellow-800">{run.medium_count}</Badge></div>}
                {run.low_count > 0 && <div className="flex justify-between"><span>Low</span><Badge className="bg-blue-100 text-blue-800">{run.low_count}</Badge></div>}
                <div className="flex justify-between border-t pt-2"><span>Total Regressions</span><span className="font-bold">{run.regression_count}</span></div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        <TabsContent value="results">
          <Card>
            <CardContent>
              <div className="overflow-x-auto">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Test Case</TableHead>
                      <TableHead>Verdict</TableHead>
                      <TableHead>Confidence</TableHead>
                      <TableHead>Matcher</TableHead>
                      <TableHead>Time</TableHead>
                      <TableHead>Cost</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {results.map((result) => (
                      <TableRow key={result.id}>
                        <TableCell className="font-mono text-sm">{result.test_case_id.slice(0, 12)}...</TableCell>
                        <TableCell><Badge variant={result.verdict === "PASS" ? "default" : result.verdict === "FAIL" ? "destructive" : "secondary"}>{result.verdict}</Badge></TableCell>
                        <TableCell>{(result.confidence * 100).toFixed(1)}%</TableCell>
                        <TableCell className="text-sm">{result.matcher_used || "N/A"}</TableCell>
                        <TableCell>{formatDuration(result.execution_time_ms)}</TableCell>
                        <TableCell>{formatCost(result.estimated_cost)}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            </CardContent>
          </Card>
          </TabsContent>

        <TabsContent value="regressions">
          <Card>
            <CardContent>
              {regressions.length === 0 ? (
                <div className="text-center py-8 text-muted-foreground">No regressions detected</div>
              ) : (
                <div className="overflow-x-auto">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Test Case</TableHead>
                        <TableHead>Previous</TableHead>
                        <TableHead>Current</TableHead>
                        <TableHead>Type</TableHead>
                        <TableHead>Severity</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {regressions.map((reg) => (
                        <TableRow key={reg.id}>
                          <TableCell className="font-mono text-sm">{reg.test_case_id.slice(0, 12)}...</TableCell>
                          <TableCell><Badge variant={reg.previous_verdict === "PASS" ? "default" : reg.previous_verdict === "FAIL" ? "destructive" : "secondary"}>{reg.previous_verdict}</Badge></TableCell>
                          <TableCell><Badge variant={reg.current_verdict === "PASS" ? "default" : reg.current_verdict === "FAIL" ? "destructive" : "secondary"}>{reg.current_verdict}</Badge></TableCell>
                          <TableCell className="text-sm">{reg.regression_type.replace("_", " ")}</TableCell>
                          <TableCell><Badge className={getSeverityColor(reg.severity)}>{reg.severity}</Badge></TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="config">
          <Card>
            <CardHeader><CardTitle>Model Versions</CardTitle></CardHeader>
            <CardContent>
              <pre className="text-sm bg-muted p-4 rounded overflow-auto">{JSON.stringify(run.model_versions, null, 2)}</pre>
            </CardContent>
          </Card>
          <Card>
            <CardHeader><CardTitle>Prompt Versions</CardTitle></CardHeader>
            <CardContent>
              <pre className="text-sm bg-muted p-4 rounded overflow-auto">{JSON.stringify(run.prompt_versions, null, 2)}</pre>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}