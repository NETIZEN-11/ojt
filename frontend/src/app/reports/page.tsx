"use client";

import { useEffect, useState, useCallback } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { api } from "@/lib/api";
import { formatDate, formatDuration, formatCost } from "@/lib/utils";
import { useAuth } from "@/lib/auth";
import { Download, FileText, BarChart, TrendingUp, AlertTriangle, CheckCircle } from "lucide-react";

interface Report {
  id: string;
  run_id: string;
  type: string;
  status: string;
  format: string;
  content: unknown;
  generated_at: string;
  generated_by: string;
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

export default function ReportsPage() {
  const { isAuthenticated, isLoading } = useAuth();
  const [reports, setReports] = useState<Report[]>([]);
  const [runs, setRuns] = useState<RunSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [runsLoading, setRunsLoading] = useState(true);
  const [selectedRun, setSelectedRun] = useState<RunSummary | null>(null);
  const [reportFormat, setReportFormat] = useState<"json" | "markdown" | "html">("markdown");
  const [generating, setGenerating] = useState(false);

  const fetchReports = useCallback(async () => {
    try {
      const res = await api.get("/reports");
      setReports(res.data);
    } catch (error) {
      console.error("Failed to fetch reports:", error);
    } finally {
      setLoading(false);
    }
  }, []);

  const fetchRuns = useCallback(async () => {
    try {
      const res = await api.get("/runs?limit=50&status=completed");
      setRuns(res.data);
    } catch (error) {
      console.error("Failed to fetch runs:", error);
    } finally {
      setRunsLoading(false);
    }
  }, []);

  useEffect(() => {
    if (!isLoading) {
      if (!isAuthenticated) {
        window.location.href = "/login";
      } else {
        fetchReports();
        fetchRuns();
      }
    }
  }, [isAuthenticated, isLoading, fetchReports, fetchRuns]);

  const handleGenerateReport = async () => {
    if (!selectedRun) return;
    setGenerating(true);
    try {
      await api.post("/reports", {
        run_id: selectedRun.id,
        format: reportFormat,
        type: "full",
      });
      fetchReports();
      setSelectedRun(null);
    } catch (error) {
      console.error("Failed to generate report:", error);
    } finally {
      setGenerating(false);
    }
  };

  const handleDownloadReport = (report: Report) => {
    const blob = new Blob([JSON.stringify(report.content, null, 2)], {
      type: report.format === "json" ? "application/json" : "text/markdown",
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `report-${report.run_id.slice(0, 8)}-${report.id.slice(0, 8)}.${report.format}`;
    a.click();
    URL.revokeObjectURL(url);
  };

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
        <div>
          <h1 className="text-3xl font-bold">Reports</h1>
          <p className="text-muted-foreground">Generate and manage evaluation reports</p>
        </div>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Generate New Report</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-4 md:grid-cols-4">
            <div className="md:col-span-2">
              <Select value={selectedRun?.id || ""} onValueChange={(v) => setSelectedRun(runs.find(r => r.id === v) || null)}>
                <SelectTrigger className="w-full">
                  <SelectValue placeholder="Select a completed run..." />
                </SelectTrigger>
                <SelectContent>
                  {runs.map((run) => (
                    <SelectItem key={run.id} value={run.id}>
                      {run.id.slice(0, 8)}... - {run.status} - {formatDate(run.created_at)}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div>
              <Select value={reportFormat} onValueChange={(v) => setReportFormat(v as "markdown" | "json" | "html")}>
                <SelectTrigger className="w-full"><SelectValue placeholder="Format" /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="markdown">Markdown</SelectItem>
                  <SelectItem value="json">JSON</SelectItem>
                  <SelectItem value="html">HTML</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div>
              <Button onClick={handleGenerateReport} disabled={generating || !selectedRun || runsLoading}>
                {generating ? "Generating..." : (<> <Download className="mr-2 h-4 w-4" /> Generate Report </>)}
              </Button>
            </div>
          </div>
          {selectedRun && (
            <div className="p-4 bg-muted rounded-lg">
              <p className="font-medium">Selected Run: {selectedRun.id.slice(0, 8)}...</p>
              <div className="flex gap-4 text-sm text-muted-foreground mt-1">
                <span>Tests: {selectedRun.total_tests}</span>
                <span>Passed: {selectedRun.passed_count}</span>
                <span>Failed: {selectedRun.failed_count}</span>
                <span>Regressions: {selectedRun.regression_count}</span>
                <span>Cost: {formatCost(selectedRun.total_cost_usd)}</span>
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {loading ? (
        <Card>
          <CardContent className="text-center py-12">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary mx-auto"></div>
            <p className="mt-4 text-muted-foreground">Loading reports...</p>
          </CardContent>
        </Card>
      ) : reports.length === 0 ? (
        <Card>
          <CardContent className="text-center py-12">
            <FileText className="h-12 w-12 text-muted-foreground mx-auto" />
            <h3 className="mt-4 text-lg font-medium">No reports generated yet</h3>
            <p className="text-muted-foreground">Generate a report from a completed run above.</p>
          </CardContent>
        </Card>
      ) : (
        <Card>
          <CardHeader>
            <CardTitle>Generated Reports ({reports.length})</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Report ID</TableHead>
                    <TableHead>Run ID</TableHead>
                    <TableHead>Type</TableHead>
                    <TableHead>Format</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead>Generated By</TableHead>
                    <TableHead>Generated At</TableHead>
                    <TableHead className="w-24">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {reports.map((report) => (
                    <TableRow key={report.id}>
                      <TableCell className="font-mono text-sm">{report.id.slice(0, 8)}...</TableCell>
                      <TableCell className="font-mono text-sm">{report.run_id.slice(0, 8)}...</TableCell>
                      <TableCell><Badge variant="secondary">{report.type}</Badge></TableCell>
                      <TableCell><Badge variant="outline">{report.format}</Badge></TableCell>
                      <TableCell>
                        <Badge variant={
                          report.status === "completed" ? "default" :
                          report.status === "failed" ? "destructive" : "secondary"
                        }>
                          {report.status}
                        </Badge>
                      </TableCell>
                      <TableCell className="font-mono text-xs">{report.generated_by.slice(0, 8)}</TableCell>
                      <TableCell>{formatDate(report.generated_at)}</TableCell>
                      <TableCell>
                        <Button variant="ghost" size="icon" onClick={() => handleDownloadReport(report)}>
                          <Download className="h-4 w-4" />
                        </Button>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          </CardContent>
        </Card>
      )}

      <Tabs defaultValue="summary" className="space-y-4">
        <TabsList>
          <TabsTrigger value="summary">Summary</TabsTrigger>
          <TabsTrigger value="trends">Trends</TabsTrigger>
        </TabsList>

        <TabsContent value="summary">
          <div className="grid gap-4 md:grid-cols-4">
            <Card>
              <CardContent className="p-4">
                <div className="flex items-center gap-4">
                  <BarChart className="h-8 w-8 text-primary" />
                  <div>
                    <p className="text-sm text-muted-foreground">Total Reports</p>
                    <p className="text-2xl font-bold">{reports.length}</p>
                  </div>
                </div>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="p-4">
                <div className="flex items-center gap-4">
                  <TrendingUp className="h-8 w-8 text-green-600" />
                  <div>
                    <p className="text-sm text-muted-foreground">Completed Runs</p>
                    <p className="text-2xl font-bold">{runs.filter(r => r.status === "completed").length}</p>
                  </div>
                </div>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="p-4">
                <div className="flex items-center gap-4">
                  <AlertTriangle className="h-8 w-8 text-red-600" />
                  <div>
                    <p className="text-sm text-muted-foreground">Total Regressions</p>
                    <p className="text-2xl font-bold">{runs.reduce((sum, r) => sum + r.regression_count, 0)}</p>
                  </div>
                </div>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="p-4">
                <div className="flex items-center gap-4">
                  <CheckCircle className="h-8 w-8 text-blue-600" />
                  <div>
                    <p className="text-sm text-muted-foreground">Avg Pass Rate</p>
                    <p className="text-2xl font-bold">
                      {runs.length > 0
                        ? ((runs.reduce((sum, r) => sum + r.passed_count, 0) / runs.reduce((sum, r) => sum + r.total_tests, 0)) * 100).toFixed(1) + "%"
                        : "N/A"}
                    </p>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>

          <Card>
            <CardHeader><CardTitle>Recent Completed Runs</CardTitle></CardHeader>
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
                      <TableHead>Duration</TableHead>
                      <TableHead>Created</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {runs.slice(0, 10).map((run) => (
                      <TableRow key={run.id}>
                        <TableCell className="font-mono text-sm">{run.id.slice(0, 8)}...</TableCell>
                        <TableCell>
                          <Badge variant={run.status === "completed" ? "default" : "destructive"}>
                            {run.status}
                          </Badge>
                        </TableCell>
                        <TableCell>{run.total_tests}</TableCell>
                        <TableCell>
                          <span className="text-green-600">{run.passed_count}</span> / 
                          <span className="text-red-600">{run.failed_count}</span>
                        </TableCell>
                        <TableCell>
                          {run.critical_count > 0 && <Badge className="bg-red-100 text-red-800 mr-1">{run.critical_count} C</Badge>}
                          {run.high_count > 0 && <Badge className="bg-orange-100 text-orange-800 mr-1">{run.high_count} H</Badge>}
                          {run.medium_count > 0 && <Badge className="bg-yellow-100 text-yellow-800 mr-1">{run.medium_count} M</Badge>}
                          {run.low_count > 0 && <Badge className="bg-blue-100 text-blue-800 mr-1">{run.low_count} L</Badge>}
                        </TableCell>
                        <TableCell>{formatCost(run.total_cost_usd)}</TableCell>
                        <TableCell>{formatDuration(run.total_latency_ms)}</TableCell>
                        <TableCell className="text-sm text-muted-foreground">{formatDate(run.created_at)}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="trends">
          <Card>
            <CardHeader><CardTitle>Evaluation Trends (Last 30 Days)</CardTitle></CardHeader>
            <CardContent>
              <div className="grid gap-4 md:grid-cols-2">
                <div className="p-4 bg-muted rounded-lg">
                  <h4 className="font-medium mb-2">Pass Rate Trend</h4>
                  <p className="text-sm text-muted-foreground">Chart would show pass rate over time</p>
                </div>
                <div className="p-4 bg-muted rounded-lg">
                  <h4 className="font-medium mb-2">Regression Count Trend</h4>
                  <p className="text-sm text-muted-foreground">Chart would show regressions over time</p>
                </div>
                <div className="p-4 bg-muted rounded-lg">
                  <h4 className="font-medium mb-2">Cost Trend</h4>
                  <p className="text-sm text-muted-foreground">Chart would show cost over time</p>
                </div>
                <div className="p-4 bg-muted rounded-lg">
                  <h4 className="font-medium mb-2">Latency Trend</h4>
                  <p className="text-sm text-muted-foreground">Chart would show latency over time</p>
                </div>
              </div>
              <p className="text-center text-muted-foreground mt-4">
                Connect to Grafana for full visualization dashboards
              </p>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}