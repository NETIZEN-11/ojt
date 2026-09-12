"use client";

import { useEffect, useState, useCallback } from "react";
import { DashboardLayout } from "@/components/ui/dashboard-layout";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { api } from "@/lib/api";
import { formatDate, formatDuration, formatCost, getStatusColor } from "@/lib/utils";
import { useAuth } from "@/lib/auth";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  LineChart,
  Line,
  PieChart,
  Pie,
  Cell,
} from "recharts";
import { Plus, TrendingUp, TrendingDown, Target, AlertTriangle, CheckCircle, DollarSign, Clock } from "lucide-react";

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
  high_count: number;
  medium_count: number;
  low_count: number;
  pass_rate_trend: number[];
  regression_trend: number[];
  cost_trend: number[];
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
      <DashboardLayout>
        <div className="flex h-[calc(100vh-4rem)] items-center justify-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
        </div>
      </DashboardLayout>
    );
  }

  const passRateData = stats?.pass_rate_trend && stats.pass_rate_trend.length > 0
    ? stats.pass_rate_trend.map((value, index) => ({
        name: `Week ${index + 1}`,
        value,
      }))
    : [];

  const regressionData = stats?.regression_trend && stats.regression_trend.length > 0
    ? stats.regression_trend.map((value, index) => ({
        name: `Week ${index + 1}`,
        value,
      }))
    : [];

  const costData = stats?.cost_trend && stats.cost_trend.length > 0
    ? stats.cost_trend.map((value, index) => ({
        name: `Week ${index + 1}`,
        value,
      }))
    : [];

  const severityData = [
    { name: "Critical", value: stats?.critical_findings || 0, color: "#ef4444" },
    { name: "High", value: stats?.high_count || 0, color: "#f97316" },
    { name: "Medium", value: stats?.medium_count || 0, color: "#eab308" },
    { name: "Low", value: stats?.low_count || 0, color: "#3b82f6" },
  ].filter((d) => d.value > 0);

  return (
    <DashboardLayout>
      <div className="space-y-6">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <h1 className="text-3xl font-bold tracking-tight">Dashboard</h1>
            <p className="text-muted-foreground">Overview of your evaluation runs and system health</p>
          </div>
          <Button onClick={() => window.location.href = "/runs/new"}>
            <Plus className="mr-2 h-4 w-4" />
            New Evaluation
          </Button>
        </div>

        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Total Runs</CardTitle>
              <Target className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{stats?.total_runs ?? 0}</div>
              <p className="text-xs text-muted-foreground">All time</p>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Pass Rate</CardTitle>
              <TrendingUp className="h-4 w-4 text-green-600" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-green-600">{(stats?.pass_rate ?? 0).toFixed(1)}%</div>
              <p className="text-xs text-muted-foreground">Overall pass rate</p>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Regressions</CardTitle>
              <AlertTriangle className="h-4 w-4 text-destructive" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-destructive">{stats?.total_regressions ?? 0}</div>
              <p className="text-xs text-muted-foreground">Total detected</p>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Critical Findings</CardTitle>
              <CheckCircle className="h-4 w-4 text-red-600" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-red-600">{stats?.critical_findings ?? 0}</div>
              <p className="text-xs text-muted-foreground">Requires attention</p>
            </CardContent>
          </Card>
        </div>

        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Review Queue</CardTitle>
              <AlertTriangle className="h-4 w-4 text-orange-600" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{stats?.review_queue_count ?? 0}</div>
              <p className="text-xs text-muted-foreground">Pending reviews</p>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Avg Runtime</CardTitle>
              <Clock className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{stats?.avg_runtime ? formatDuration(stats.avg_runtime) : "N/A"}</div>
              <p className="text-xs text-muted-foreground">Per evaluation run</p>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Total Cost</CardTitle>
              <DollarSign className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{stats?.total_cost ? formatCost(stats.total_cost) : "N/A"}</div>
              <p className="text-xs text-muted-foreground">All evaluations</p>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">System Health</CardTitle>
              <TrendingUp className="h-4 w-4 text-green-600" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-green-600">Healthy</div>
              <p className="text-xs text-muted-foreground">All services operational</p>
            </CardContent>
          </Card>
        </div>

        <div className="grid gap-4 lg:grid-cols-2">
          <Card>
            <CardHeader>
              <CardTitle>Pass Rate Trend</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="h-64">
                {passRateData.length === 0 ? (
                  <div className="flex items-center justify-center h-full text-muted-foreground">
                    <div className="text-center">
                      <TrendingUp className="h-12 w-12 mx-auto mb-2 opacity-30" />
                      <p>No trend data available</p>
                      <p className="text-sm">Run evaluations to see trends</p>
                    </div>
                  </div>
                ) : (
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={passRateData}>
                      <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                      <XAxis dataKey="name" className="text-xs" />
                      <YAxis className="text-xs" domain={[0, 100]} />
                      <Tooltip contentStyle={{ backgroundColor: "hsl(var(--card))", border: "1px solid hsl(var(--border))", borderRadius: "8px" }} />
                      <Line type="monotone" dataKey="value" stroke="hsl(var(--primary))" strokeWidth={2} dot={{ r: 4 }} />
                    </LineChart>
                  </ResponsiveContainer>
                )}
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Regression Trend</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="h-64">
                {regressionData.length === 0 ? (
                  <div className="flex items-center justify-center h-full text-muted-foreground">
                    <div className="text-center">
                      <AlertTriangle className="h-12 w-12 mx-auto mb-2 opacity-30" />
                      <p>No regression data available</p>
                      <p className="text-sm">Run evaluations to track regressions</p>
                    </div>
                  </div>
                ) : (
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={regressionData}>
                      <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                      <XAxis dataKey="name" className="text-xs" />
                      <YAxis className="text-xs" />
                      <Tooltip contentStyle={{ backgroundColor: "hsl(var(--card))", border: "1px solid hsl(var(--border))", borderRadius: "8px" }} />
                      <Bar dataKey="value" fill="hsl(var(--destructive))" radius={[4, 4, 0, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                )}
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Cost Trend</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="h-64">
                {costData.length === 0 ? (
                  <div className="flex items-center justify-center h-full text-muted-foreground">
                    <div className="text-center">
                      <DollarSign className="h-12 w-12 mx-auto mb-2 opacity-30" />
                      <p>No cost data available</p>
                      <p className="text-sm">Run evaluations to track costs</p>
                    </div>
                  </div>
                ) : (
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={costData}>
                      <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                      <XAxis dataKey="name" className="text-xs" />
                      <YAxis className="text-xs" />
                      <Tooltip contentStyle={{ backgroundColor: "hsl(var(--card))", border: "1px solid hsl(var(--border))", borderRadius: "8px" }} />
                      <Line type="monotone" dataKey="value" stroke="hsl(var(--secondary-foreground))" strokeWidth={2} dot={{ r: 4 }} />
                    </LineChart>
                  </ResponsiveContainer>
                )}
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Severity Distribution</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="h-64">
                {severityData.length === 0 ? (
                  <div className="flex items-center justify-center h-full text-muted-foreground">
                    <div className="text-center">
                      <CheckCircle className="h-12 w-12 mx-auto mb-2 opacity-30" />
                      <p>No severity data available</p>
                      <p className="text-sm">No critical findings detected</p>
                    </div>
                  </div>
                ) : (
                  <ResponsiveContainer width="100%" height="100%">
                    <PieChart>
                      <Pie
                        data={severityData}
                        cx="50%"
                        cy="50%"
                        innerRadius={60}
                        outerRadius={100}
                        paddingAngle={2}
                        dataKey="value"
                        nameKey="name"
                        label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                        labelLine={false}
                      >
                        {severityData.map((entry, index) => (
                          <Cell key={`cell-${index}`} fill={entry.color} />
                        ))}
                      </Pie>
                      <Tooltip contentStyle={{ backgroundColor: "hsl(var(--card))", border: "1px solid hsl(var(--border))", borderRadius: "8px" }} />
                    </PieChart>
                  </ResponsiveContainer>
                )}
              </div>
            </CardContent>
          </Card>
        </div>

        <Card>
          <CardHeader>
            <CardTitle>Recent Runs</CardTitle>
          </CardHeader>
          <CardContent>
            {loading ? (
              <div className="text-center py-8">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary mx-auto"></div>
                <p className="mt-4 text-muted-foreground">Loading...</p>
              </div>
            ) : recentRuns.length === 0 ? (
              <div className="text-center py-8 text-muted-foreground">
                <Target className="h-12 w-12 mx-auto mb-4 opacity-50" />
                <h3 className="text-lg font-medium">No runs yet</h3>
                <p>Create your first evaluation to get started!</p>
              </div>
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
    </DashboardLayout>
  );
}