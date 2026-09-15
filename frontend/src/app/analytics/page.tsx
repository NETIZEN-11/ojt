"use client";

import { useEffect, useState, useCallback } from "react";
import { DashboardLayout } from "@/components/ui/dashboard-layout";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { api } from "@/lib/api";
import { formatDate, formatDuration, formatCost } from "@/lib/utils";
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
  AreaChart,
  Area,
} from "recharts";
import { TrendingUp, TrendingDown, Target, AlertTriangle, CheckCircle, DollarSign, Clock, Filter } from "lucide-react";

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

interface AnalyticsData {
  runs_over_time: { date: string; count: number }[];
  pass_rate_over_time: { date: string; rate: number }[];
  regressions_over_time: { date: string; count: number }[];
  cost_over_time: { date: string; cost: number }[];
  latency_over_time: { date: string; latency: number }[];
  severity_distribution: { severity: string; count: number }[];
  category_distribution: { category: string; count: number }[];
  top_failing_tests: { test_case_id: string; failure_count: number }[];
}

export default function AnalyticsPage() {
  const { isAuthenticated, isLoading } = useAuth();
  const [analytics, setAnalytics] = useState<AnalyticsData | null>(null);
  const [loading, setLoading] = useState(true);
  const [timeRange, setTimeRange] = useState("7d");

  const fetchAnalytics = useCallback(async () => {
    try {
      // TODO: Backend endpoint /analytics not implemented yet
      // const res = await api.get(`/analytics?range=${timeRange}`);
      // setAnalytics(res.data);
      setAnalytics({
        runs_over_time: [],
        pass_rate_over_time: [],
        regressions_over_time: [],
        cost_over_time: [],
        latency_over_time: [],
        severity_distribution: [],
        category_distribution: [],
        top_failing_tests: [],
      });
    } catch (error) {
      console.error("Failed to fetch analytics:", error);
    } finally {
      setLoading(false);
    }
  }, [timeRange]);

  useEffect(() => {
    if (!isLoading) {
      if (!isAuthenticated) {
        window.location.href = "/login";
      } else {
        fetchAnalytics();
      }
    }
  }, [isAuthenticated, isLoading, fetchAnalytics]);

  if (isLoading || !isAuthenticated) {
    return (
      <DashboardLayout>
        <div className="flex h-[calc(100vh-4rem)] items-center justify-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
        </div>
      </DashboardLayout>
    );
  }

  const passRateData = analytics?.pass_rate_over_time?.map(d => ({
    name: new Date(d.date).toLocaleDateString("en-US", { month: "short", day: "numeric" }),
    value: d.rate,
  })) || [];

  const regressionData = analytics?.regressions_over_time?.map(d => ({
    name: new Date(d.date).toLocaleDateString("en-US", { month: "short", day: "numeric" }),
    value: d.count,
  })) || [];

  const costData = analytics?.cost_over_time?.map(d => ({
    name: new Date(d.date).toLocaleDateString("en-US", { month: "short", day: "numeric" }),
    value: d.cost,
  })) || [];

  const runsData = analytics?.runs_over_time?.map(d => ({
    name: new Date(d.date).toLocaleDateString("en-US", { month: "short", day: "numeric" }),
    value: d.count,
  })) || [];

  const severityData = analytics?.severity_distribution?.map(d => ({
    name: d.severity,
    value: d.count,
    color: d.severity === "critical" ? "#ef4444" : d.severity === "high" ? "#f97316" : d.severity === "medium" ? "#eab308" : "#3b82f6",
  })) || [];

  const categoryData = analytics?.category_distribution?.map((d, i) => ({
    name: d.category,
    value: d.count,
    color: ["#3b82f6", "#8b5cf6", "#ec4899", "#f97316", "#eab308", "#22c55e", "#06b6d4"][i % 7],
  })) || [];

  return (
    <DashboardLayout>
      <div className="space-y-6">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <h1 className="text-3xl font-bold">Analytics</h1>
            <p className="text-muted-foreground">Deep insights into your evaluation data</p>
          </div>
          <Select value={timeRange} onValueChange={setTimeRange}>
            <SelectTrigger className="w-48"><SelectValue placeholder="Time range" /></SelectTrigger>
            <SelectContent>
              <SelectItem value="7d">Last 7 days</SelectItem>
              <SelectItem value="30d">Last 30 days</SelectItem>
              <SelectItem value="90d">Last 90 days</SelectItem>
              <SelectItem value="1y">Last year</SelectItem>
            </SelectContent>
          </Select>
        </div>

        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Total Runs</CardTitle>
              <Target className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{analytics?.runs_over_time?.reduce((sum, d) => sum + d.count, 0) || 0}</div>
              <p className="text-xs text-muted-foreground">{timeRange} period</p>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Avg Pass Rate</CardTitle>
              <TrendingUp className="h-4 w-4 text-green-600" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-green-600">
                {analytics?.pass_rate_over_time?.length
                  ? (analytics.pass_rate_over_time.reduce((sum, d) => sum + d.rate, 0) / analytics.pass_rate_over_time.length).toFixed(1) + "%"
                  : "N/A"}
              </div>
              <p className="text-xs text-muted-foreground">Average over period</p>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Total Regressions</CardTitle>
              <AlertTriangle className="h-4 w-4 text-destructive" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-destructive">
                {analytics?.regressions_over_time?.reduce((sum, d) => sum + d.count, 0) || 0}
              </div>
              <p className="text-xs text-muted-foreground">{timeRange} period</p>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Total Cost</CardTitle>
              <DollarSign className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">
                {analytics?.cost_over_time?.reduce((sum, d) => sum + d.cost, 0) ? formatCost(analytics.cost_over_time.reduce((sum, d) => sum + d.cost, 0)) : "N/A"}
              </div>
              <p className="text-xs text-muted-foreground">{timeRange} period</p>
            </CardContent>
          </Card>
        </div>

        <Tabs defaultValue="overview" className="space-y-4">
          <TabsList>
            <TabsTrigger value="overview">Overview</TabsTrigger>
            <TabsTrigger value="performance">Performance</TabsTrigger>
            <TabsTrigger value="quality">Quality</TabsTrigger>
            <TabsTrigger value="cost">Cost</TabsTrigger>
          </TabsList>

          <TabsContent value="overview">
            <div className="grid gap-4 lg:grid-cols-2">
              <Card>
                <CardHeader><CardTitle>Runs Over Time</CardTitle></CardHeader>
                <CardContent>
                  <div className="h-80">
                    <ResponsiveContainer width="100%" height="100%">
                      <AreaChart data={runsData.length > 0 ? runsData : [{ name: "Day 1", value: 0 }]}>
                        <defs>
                          <linearGradient id="colorRuns" x1="0" y1="0" x2="0" y2="1">
                            <stop offset="5%" stopColor="hsl(var(--primary))" stopOpacity={0.3} />
                            <stop offset="95%" stopColor="hsl(var(--primary))" stopOpacity={0} />
                          </linearGradient>
                        </defs>
                        <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                        <XAxis dataKey="name" className="text-xs" />
                        <YAxis className="text-xs" />
                        <Tooltip contentStyle={{ backgroundColor: "hsl(var(--card))", border: "1px solid hsl(var(--border))", borderRadius: "8px" }} />
                        <Area type="monotone" dataKey="value" stroke="hsl(var(--primary))" fillOpacity={1} fill="url(#colorRuns)" strokeWidth={2} />
                      </AreaChart>
                    </ResponsiveContainer>
                  </div>
                </CardContent>
              </Card>

              <Card>
                <CardHeader><CardTitle>Pass Rate Trend</CardTitle></CardHeader>
                <CardContent>
                  <div className="h-80">
                    <ResponsiveContainer width="100%" height="100%">
                      <LineChart data={passRateData.length > 0 ? passRateData : [{ name: "Day 1", value: 0 }]}>
                        <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                        <XAxis dataKey="name" className="text-xs" />
                        <YAxis className="text-xs" domain={[0, 100]} />
                        <Tooltip contentStyle={{ backgroundColor: "hsl(var(--card))", border: "1px solid hsl(var(--border))", borderRadius: "8px" }} />
                        <Line type="monotone" dataKey="value" stroke="hsl(var(--primary))" strokeWidth={2} dot={{ r: 4 }} />
                      </LineChart>
                    </ResponsiveContainer>
                  </div>
                </CardContent>
              </Card>

              <Card>
                <CardHeader><CardTitle>Regression Trend</CardTitle></CardHeader>
                <CardContent>
                  <div className="h-80">
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart data={regressionData.length > 0 ? regressionData : [{ name: "Day 1", value: 0 }]}>
                        <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                        <XAxis dataKey="name" className="text-xs" />
                        <YAxis className="text-xs" />
                        <Tooltip contentStyle={{ backgroundColor: "hsl(var(--card))", border: "1px solid hsl(var(--border))", borderRadius: "8px" }} />
                        <Bar dataKey="value" fill="hsl(var(--destructive))" radius={[4, 4, 0, 0]} />
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                </CardContent>
              </Card>

              <Card>
                <CardHeader><CardTitle>Cost Trend</CardTitle></CardHeader>
                <CardContent>
                  <div className="h-80">
                    <ResponsiveContainer width="100%" height="100%">
                      <LineChart data={costData.length > 0 ? costData : [{ name: "Day 1", value: 0 }]}>
                        <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                        <XAxis dataKey="name" className="text-xs" />
                        <YAxis className="text-xs" />
                        <Tooltip contentStyle={{ backgroundColor: "hsl(var(--card))", border: "1px solid hsl(var(--border))", borderRadius: "8px" }} />
                        <Line type="monotone" dataKey="value" stroke="hsl(var(--secondary-foreground))" strokeWidth={2} dot={{ r: 4 }} />
                      </LineChart>
                    </ResponsiveContainer>
                  </div>
                </CardContent>
              </Card>
            </div>

            <div className="grid gap-4 lg:grid-cols-2">
              <Card>
                <CardHeader><CardTitle>Severity Distribution</CardTitle></CardHeader>
                <CardContent>
                  <div className="h-64">
                    <ResponsiveContainer width="100%" height="100%">
                      <PieChart>
                        <Pie
                          data={severityData.length > 0 ? severityData : [{ name: "None", value: 1, color: "hsl(var(--muted))" }]}
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
                  </div>
                </CardContent>
              </Card>

              <Card>
                <CardHeader><CardTitle>Category Distribution</CardTitle></CardHeader>
                <CardContent>
                  <div className="h-64">
                    <ResponsiveContainer width="100%" height="100%">
                      <PieChart>
                        <Pie
                          data={categoryData.length > 0 ? categoryData : [{ name: "None", value: 1, color: "hsl(var(--muted))" }]}
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
                          {categoryData.map((entry, index) => (
                            <Cell key={`cell-${index}`} fill={entry.color} />
                          ))}
                        </Pie>
                        <Tooltip contentStyle={{ backgroundColor: "hsl(var(--card))", border: "1px solid hsl(var(--border))", borderRadius: "8px" }} />
                      </PieChart>
                    </ResponsiveContainer>
                  </div>
                </CardContent>
              </Card>
            </div>
          </TabsContent>

          <TabsContent value="performance">
            <div className="grid gap-4 lg:grid-cols-2">
              <Card>
                <CardHeader><CardTitle>Latency Over Time</CardTitle></CardHeader>
                <CardContent>
                  <div className="h-80">
                    <ResponsiveContainer width="100%" height="100%">
                      <LineChart data={analytics?.latency_over_time?.map(d => ({
                        name: new Date(d.date).toLocaleDateString("en-US", { month: "short", day: "numeric" }),
                        value: d.latency,
                      })) || [{ name: "Day 1", value: 0 }]}>
                        <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                        <XAxis dataKey="name" className="text-xs" />
                        <YAxis className="text-xs" />
                        <Tooltip contentStyle={{ backgroundColor: "hsl(var(--card))", border: "1px solid hsl(var(--border))", borderRadius: "8px" }} formatter={(value: number) => [formatDuration(value), "Latency"]} />
                        <Line type="monotone" dataKey="value" stroke="hsl(var(--accent-foreground))" strokeWidth={2} dot={{ r: 4 }} />
                      </LineChart>
                    </ResponsiveContainer>
                  </div>
                </CardContent>
              </Card>

              <Card>
                <CardHeader><CardTitle>Tests per Run</CardTitle></CardHeader>
                <CardContent>
                  <div className="h-80">
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart data={runsData.length > 0 ? runsData : [{ name: "Day 1", value: 0 }]}>
                        <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                        <XAxis dataKey="name" className="text-xs" />
                        <YAxis className="text-xs" />
                        <Tooltip contentStyle={{ backgroundColor: "hsl(var(--card))", border: "1px solid hsl(var(--border))", borderRadius: "8px" }} />
                        <Bar dataKey="value" fill="hsl(var(--primary))" radius={[4, 4, 0, 0]} />
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                </CardContent>
              </Card>
            </div>
          </TabsContent>

          <TabsContent value="quality">
            <Card>
              <CardHeader><CardTitle>Top Failing Tests</CardTitle></CardHeader>
              <CardContent>
                {(analytics?.top_failing_tests?.length ?? 0) > 0 ? (
                  <div className="overflow-x-auto">
                    <table className="w-full">
                      <thead>
                        <tr className="border-b">
                          <th className="text-left p-4">Test Case</th>
                          <th className="text-left p-4">Failure Count</th>
                        </tr>
                      </thead>
                      <tbody>
                        {analytics?.top_failing_tests?.map((test) => (
                          <tr key={test.test_case_id} className="border-b">
                            <td className="p-4 font-mono text-sm">{test.test_case_id}</td>
                            <td className="p-4"><span className="bg-destructive/10 text-destructive px-2 py-1 rounded">{test.failure_count}</span></td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                ) : (
                  <p className="text-center py-8 text-muted-foreground">No failing tests data available</p>
                )}
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="cost">
            <div className="grid gap-4 lg:grid-cols-2">
              <Card>
                <CardHeader><CardTitle>Daily Cost Breakdown</CardTitle></CardHeader>
                <CardContent>
                  <div className="h-80">
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart data={costData.length > 0 ? costData : [{ name: "Day 1", value: 0 }]}>
                        <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                        <XAxis dataKey="name" className="text-xs" />
                        <YAxis className="text-xs" />
                        <Tooltip contentStyle={{ backgroundColor: "hsl(var(--card))", border: "1px solid hsl(var(--border))", borderRadius: "8px" }} formatter={(value: number) => [formatCost(value), "Cost"]} />
                        <Bar dataKey="value" fill="hsl(var(--secondary-foreground))" radius={[4, 4, 0, 0]} />
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                </CardContent>
              </Card>

              <Card>
                <CardHeader><CardTitle>Cumulative Cost</CardTitle></CardHeader>
                <CardContent>
                  <div className="h-80">
                    <ResponsiveContainer width="100%" height="100%">
                      <AreaChart data={analytics?.cost_over_time?.map((d, i, arr) => ({
                        name: new Date(d.date).toLocaleDateString("en-US", { month: "short", day: "numeric" }),
                        value: arr.slice(0, i + 1).reduce((sum, item) => sum + item.cost, 0),
                      })) || [{ name: "Day 1", value: 0 }]}>
                        <defs>
                          <linearGradient id="colorCost" x1="0" y1="0" x2="0" y2="1">
                            <stop offset="5%" stopColor="hsl(var(--secondary-foreground))" stopOpacity={0.3} />
                            <stop offset="95%" stopColor="hsl(var(--secondary-foreground))" stopOpacity={0} />
                          </linearGradient>
                        </defs>
                        <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                        <XAxis dataKey="name" className="text-xs" />
                        <YAxis className="text-xs" />
                        <Tooltip contentStyle={{ backgroundColor: "hsl(var(--card))", border: "1px solid hsl(var(--border))", borderRadius: "8px" }} formatter={(value: number) => [formatCost(value), "Cumulative Cost"]} />
                        <Area type="monotone" dataKey="value" stroke="hsl(var(--secondary-foreground))" fillOpacity={1} fill="url(#colorCost)" strokeWidth={2} />
                      </AreaChart>
                    </ResponsiveContainer>
                  </div>
                </CardContent>
              </Card>
            </div>
          </TabsContent>
        </Tabs>
      </div>
    </DashboardLayout>
  );
}