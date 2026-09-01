"use client";

import { useEffect, useState, useCallback } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { api } from "@/lib/api";
import { formatDate, formatDuration, formatCost, getStatusColor } from "@/lib/utils";
import { useAuth } from "@/lib/auth";

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

interface Stats {
  total_runs: number;
  pass_rate: number;
  total_regressions: number;
  critical_findings: number;
  review_queue_count: number;
  avg_runtime: number;
  total_cost: number;
}

export default function DashboardPage() {
  const { isAuthenticated, isLoading } = useAuth();
  const [stats, setStats] = useState<Stats | null>(null);
  const [recentRuns, setRecentRuns] = useState<RunSummary[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchData = useCallback(async () => {
    try {
      const [statsRes, runsRes] = await Promise.all([
        api.get("/runs/stats"),
        api.get("/runs?limit=5"),
      ]);
      setStats(statsRes.data);
      setRecentRuns(runsRes.data);
    } catch (error) {
      console.error("Failed to fetch dashboard data:", error);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (!isLoading) {
      if (!isAuthenticated) {
        window.location.href = "/login";
      } else {
        fetchData();
      }
    }
  }, [isAuthenticated, isLoading, fetchData]);

  if (isLoading || !isAuthenticated) {
    return (
      <div className="flex h-screen items-center justify-center">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold">Dashboard</h1>
        <Button onClick={() => window.location.href = "/runs/new"}>New Evaluation</Button>
      </div>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Runs</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats?.total_runs ?? 0}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Pass Rate</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{(stats?.pass_rate ?? 0).toFixed(1)}%</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Regressions</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-destructive">{stats?.total_regressions ?? 0}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Critical Findings</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-red-600">{stats?.critical_findings ?? 0}</div>
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Review Queue</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats?.review_queue_count ?? 0}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Avg Runtime</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats?.avg_runtime ? formatDuration(stats.avg_runtime) : "N/A"}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Cost</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats?.total_cost ? formatCost(stats.total_cost) : "N/A"}</div>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Recent Runs</CardTitle>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="text-center py-8">Loading...</div>
          ) : recentRuns.length === 0 ? (
            <div className="text-center py-8 text-muted-foreground">No runs yet. Create your first evaluation!</div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b">
                    <th className="text-left p-4">Run ID</th>
                    <th className="text-left p-4">Status</th>
                    <th className="text-left p-4">Tests</th>
                    <th className="text-left p-4">Results</th>
                    <th className="text-left p-4">Regressions</th>
                    <th className="text-left p-4">Cost</th>
                    <th className="text-left p-4">Created</th>
                  </tr>
                </thead>
                <tbody>
                  {recentRuns.map((run) => (
                    <tr key={run.id} className="border-b hover:bg-muted/50 cursor-pointer" onClick={() => window.location.href = `/runs/${run.id}`}>
                      <td className="p-4 font-mono text-sm">{run.id.slice(0, 8)}...</td>
                      <td className="p-4">
                        <span className={`px-2 py-1 rounded-full text-xs font-medium ${getStatusColor(run.status)}`}>
                          {run.status.replace("_", " ")}
                        </span>
                      </td>
                      <td className="p-4">{run.total_tests}</td>
                      <td className="p-4">
                        <span className="text-green-600">{run.passed_count}</span> / 
                        <span className="text-red-600">{run.failed_count}</span> / 
                        <span className="text-yellow-600">{run.inconclusive_count}</span>
                      </td>
                      <td className="p-4">
                        {run.critical_count > 0 && <span className="text-red-600 font-medium">Critical: {run.critical_count}</span>}
                        {run.high_count > 0 && <span className="text-orange-600 font-medium ml-2">High: {run.high_count}</span>}
                        {run.medium_count > 0 && <span className="text-yellow-600 font-medium ml-2">Medium: {run.medium_count}</span>}
                        {run.low_count > 0 && <span className="text-blue-600 font-medium ml-2">Low: {run.low_count}</span>}
                      </td>
                      <td className="p-4">{formatCost(run.total_cost_usd)}</td>
                      <td className="p-4 text-sm text-muted-foreground">{formatDate(run.created_at)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}