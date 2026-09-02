"use client";

import { useEffect, useState, useCallback } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { api } from "@/lib/api";
import { formatDate, formatDuration } from "@/lib/utils";
import { useAuth } from "@/lib/auth";
import { useParams, useRouter } from "next/navigation";
import { Edit, Trash2, ArrowLeft, Wifi, Play } from "lucide-react";

interface TargetAgent {
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
  status: string;
  created_at: string;
  updated_at: string;
  created_by: string | null;
}

interface RunSummary {
  id: string;
  status: string;
  created_at: string;
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
}

export default function AgentDetailPage() {
  const params = useParams();
  const agentId = params.id as string;
  const router = useRouter();
  const { isAuthenticated, isLoading } = useAuth();
  const [agent, setAgent] = useState<TargetAgent | null>(null);
  const [runs, setRuns] = useState<RunSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [runsLoading, setRunsLoading] = useState(true);

  const fetchAgent = useCallback(async () => {
    try {
      const res = await api.get(`/agents/${agentId}`);
      setAgent(res.data);
    } catch (error) {
      console.error("Failed to fetch agent:", error);
    } finally {
      setLoading(false);
    }
  }, [agentId]);

  const fetchRuns = useCallback(async () => {
    try {
      const res = await api.get(`/runs?target_agent_id=${agentId}&limit=20`);
      setRuns(res.data);
    } catch (error) {
      console.error("Failed to fetch runs:", error);
    } finally {
      setRunsLoading(false);
    }
  }, [agentId]);

  useEffect(() => {
    if (!isLoading) {
      if (!isAuthenticated) {
        window.location.href = "/login";
      } else {
        fetchAgent();
        fetchRuns();
      }
    }
  }, [isAuthenticated, isLoading, fetchAgent, fetchRuns]);

  const handleDelete = async () => {
    if (!confirm("Are you sure you want to delete this agent?")) return;
    try {
      await api.delete(`/agents/${agentId}`);
      router.push("/agents");
    } catch (error) {
      console.error("Failed to delete agent:", error);
    }
  };

  if (isLoading || !isAuthenticated) {
    return (
      <div className="flex h-screen items-center justify-center">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
      </div>
    );
  }

  if (!agent) {
    return (
      <div className="p-6 text-center">
        <h2 className="text-xl font-medium">Agent not found</h2>
        <Button variant="outline" onClick={() => router.push("/agents")} className="mt-4">
          <ArrowLeft className="mr-2 h-4 w-4" /> Back to Agents
        </Button>
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="icon" onClick={() => router.push("/agents")}>
            <ArrowLeft className="h-4 w-4" />
          </Button>
          <div>
            <h1 className="text-3xl font-bold">{agent.name}</h1>
            <div className="flex items-center gap-2 mt-1">
              <Badge variant={agent.allowed ? "default" : "secondary"}>
                {agent.allowed ? "Allowed" : "Blocked"}
              </Badge>
              <Badge variant={agent.status === "active" ? "default" : agent.status === "testing" ? "secondary" : "destructive"}>
                {agent.status}
              </Badge>
            </div>
            {agent.description && (
              <p className="text-muted-foreground mt-2">{agent.description}</p>
            )}
          </div>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" onClick={() => router.push(`/runs/new?agent=${agentId}`)}>
            <Play className="mr-2 h-4 w-4" /> New Evaluation
          </Button>
          <Button variant="outline" onClick={() => router.push(`/agents/${agentId}/edit`)}>
            <Edit className="mr-2 h-4 w-4" /> Edit
          </Button>
          <Button variant="destructive" onClick={handleDelete}>
            <Trash2 className="mr-2 h-4 w-4" /> Delete
          </Button>
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-4">
        <Card>
          <CardContent className="p-4">
            <p className="text-sm text-muted-foreground">Endpoint</p>
            <p className="font-mono text-sm truncate max-w-xs">{agent.endpoint_url}</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <p className="text-sm text-muted-foreground">Timeout</p>
            <p className="font-bold">{agent.timeout_seconds}s</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <p className="text-sm text-muted-foreground">Max Retries</p>
            <p className="font-bold">{agent.max_retries}</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <p className="text-sm text-muted-foreground">Total Runs</p>
            <p className="font-bold">{runs.length}</p>
          </CardContent>
        </Card>
      </div>

      <Tabs defaultValue="config" className="space-y-4">
        <TabsList>
          <TabsTrigger value="config">Configuration</TabsTrigger>
          <TabsTrigger value="runs">Recent Runs ({runs.length})</TabsTrigger>
        </TabsList>

        <TabsContent value="config">
          <div className="grid gap-4 md:grid-cols-2">
            <Card>
              <CardHeader><CardTitle>Request Template</CardTitle></CardHeader>
              <CardContent>
                <pre className="bg-muted p-4 rounded text-sm font-mono overflow-auto max-h-96">
                  {JSON.stringify(agent.request_template, null, 2)}
                </pre>
              </CardContent>
            </Card>
            <Card>
              <CardHeader><CardTitle>Response Extraction</CardTitle></CardHeader>
              <CardContent>
                <pre className="bg-muted p-4 rounded text-sm font-mono overflow-auto max-h-96">
                  {JSON.stringify(agent.response_extraction, null, 2)}
                </pre>
              </CardContent>
            </Card>
            <Card>
              <CardHeader><CardTitle>Auth Config</CardTitle></CardHeader>
              <CardContent>
                <pre className="bg-muted p-4 rounded text-sm font-mono overflow-auto max-h-96">
                  {JSON.stringify(agent.auth_config, null, 2)}
                </pre>
              </CardContent>
            </Card>
            <Card>
              <CardHeader><CardTitle>Metadata</CardTitle></CardHeader>
              <CardContent className="space-y-2">
                <dl className="grid grid-cols-2 gap-2 text-sm">
                  <dt className="text-muted-foreground">Created</dt>
                  <dd>{formatDate(agent.created_at)}</dd>
                  <dt className="text-muted-foreground">Updated</dt>
                  <dd>{formatDate(agent.updated_at)}</dd>
                  <dt className="text-muted-foreground">Created By</dt>
                  <dd className="font-mono text-xs">{agent.created_by?.slice(0, 8) || "N/A"}</dd>
                </dl>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        <TabsContent value="runs">
          {runsLoading ? (
            <Card>
              <CardContent className="text-center py-12">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary mx-auto"></div>
                <p className="mt-4 text-muted-foreground">Loading runs...</p>
              </CardContent>
            </Card>
          ) : runs.length === 0 ? (
            <Card>
              <CardContent className="text-center py-12">
                <p className="text-muted-foreground">No runs for this agent yet.</p>
                <Button onClick={() => router.push(`/runs/new?agent=${agentId}`)} className="mt-4">
                  <Play className="mr-2 h-4 w-4" /> Run Evaluation
                </Button>
              </CardContent>
            </Card>
          ) : (
            <Card>
              <CardContent>
                <div className="overflow-x-auto">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Run ID</TableHead>
                        <TableHead>Status</TableHead>
                        <TableHead>Tests</TableHead>
                        <TableHead>Results</TableHead>
                        <TableHead>Regressions</TableHead>
                        <TableHead>Cost</TableHead>
                        <TableHead>Created</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {runs.map((run) => (
                        <TableRow key={run.id} className="cursor-pointer" onClick={() => router.push(`/runs/${run.id}`)}>
                          <TableCell className="font-mono text-sm">{run.id.slice(0, 8)}...</TableCell>
                          <TableCell>
                            <Badge variant={
                              run.status === "completed" ? "default" :
                              run.status === "failed" ? "destructive" :
                              run.status === "review_required" ? "destructive" : "secondary"
                            }>
                              {run.status.replace("_", " ")}
                            </Badge>
                          </TableCell>
                          <TableCell>{run.total_tests}</TableCell>
                          <TableCell>
                            <span className="text-green-600">{run.passed_count}</span> / 
                            <span className="text-red-600">{run.failed_count}</span> / 
                            <span className="text-yellow-600">{run.inconclusive_count}</span>
                          </TableCell>
                          <TableCell>
                            {run.critical_count > 0 && <Badge className="bg-red-100 text-red-800 mr-1">Critical: {run.critical_count}</Badge>}
                            {run.high_count > 0 && <Badge className="bg-orange-100 text-orange-800 mr-1">High: {run.high_count}</Badge>}
                            {run.medium_count > 0 && <Badge className="bg-yellow-100 text-yellow-800 mr-1">Medium: {run.medium_count}</Badge>}
                            {run.low_count > 0 && <Badge className="bg-blue-100 text-blue-800 mr-1">Low: {run.low_count}</Badge>}
                          </TableCell>
                          <TableCell>${run.total_cost_usd.toFixed(4)}</TableCell>
                          <TableCell className="text-sm text-muted-foreground">{formatDate(run.created_at)}</TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </div>
              </CardContent>
            </Card>
          )}
        </TabsContent>
      </Tabs>
    </div>
  );
}