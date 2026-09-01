"use client";

import { useEffect, useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { api } from "@/lib/api";
import { formatDate, formatCost, getStatusColor } from "@/lib/utils";
import { useAuth } from "@/lib/auth";

interface RunSummary {
  id: string;
  target_agent_id: string;
  suite_id: string;
  suite_version: number;
  status: string;
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
  created_at: string;
}

export default function RunsPage() {
  const router = useRouter();
  const { isAuthenticated, isLoading } = useAuth();
  const [runs, setRuns] = useState<RunSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [totalPages] = useState(1);
  const [filters, setFilters] = useState({ status: "", agent_id: "" });

  const fetchRuns = useCallback(async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams({
        skip: ((page - 1) * 20).toString(),
        limit: "20",
      });
      if (filters.status) params.append("status", filters.status);
      if (filters.agent_id) params.append("target_agent_id", filters.agent_id);

      const response = await api.get(`/runs?${params.toString()}`);
      setRuns(response.data);
    } catch (error) {
      console.error("Failed to fetch runs:", error);
    } finally {
      setLoading(false);
    }
  }, [page, filters]);

  useEffect(() => {
    if (!isLoading) {
      if (!isAuthenticated) {
        router.push("/login");
      } else {
        fetchRuns();
      }
    }
  }, [isAuthenticated, isLoading, router, fetchRuns]);

  if (isLoading || !isAuthenticated) {
    return <div className="flex h-screen items-center justify-center"><div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div></div>;
  }

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold">Evaluation Runs</h1>
        <Button onClick={() => window.location.href = "/runs/new"}>New Evaluation</Button>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Filters</CardTitle>
        </CardHeader>
        <CardContent className="grid gap-4 md:grid-cols-4">
          <Select value={filters.status} onValueChange={(value) => setFilters({...filters, status: value})}>
            <SelectTrigger><SelectValue placeholder="All Statuses" /></SelectTrigger>
            <SelectContent>
              <SelectItem value="">All Statuses</SelectItem>
              <SelectItem value="queued">Queued</SelectItem>
              <SelectItem value="running">Running</SelectItem>
              <SelectItem value="completed">Completed</SelectItem>
              <SelectItem value="failed">Failed</SelectItem>
              <SelectItem value="review_required">Review Required</SelectItem>
              <SelectItem value="cancelled">Cancelled</SelectItem>
            </SelectContent>
          </Select>
          <Input placeholder="Filter by Agent ID" value={filters.agent_id} onChange={(e) => setFilters({...filters, agent_id: e.target.value})} />
        </CardContent>
      </Card>

      <Card>
        <CardContent>
          {loading ? (
            <div className="text-center py-8">Loading...</div>
          ) : runs.length === 0 ? (
            <div className="text-center py-8 text-muted-foreground">No runs found</div>
          ) : (
            <>
              <div className="overflow-x-auto">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Run ID</TableHead>
                      <TableHead>Agent</TableHead>
                      <TableHead>Suite</TableHead>
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
                      <TableRow key={run.id} className="cursor-pointer" onClick={() => window.location.href = `/runs/${run.id}`}>
                        <TableCell className="font-mono text-sm">{run.id.slice(0, 8)}...</TableCell>
                        <TableCell className="font-mono text-sm">{run.target_agent_id.slice(0, 8)}...</TableCell>
                        <TableCell className="font-mono text-sm">{run.suite_id.slice(0, 8)}... (v{run.suite_version})</TableCell>
                        <TableCell>
                          <span className={`px-2 py-1 rounded-full text-xs font-medium ${getStatusColor(run.status)}`}>
                            {run.status.replace("_", " ")}
                          </span>
                        </TableCell>
                        <TableCell>{run.total_tests}</TableCell>
                        <TableCell>
                          <span className="text-green-600">{run.passed_count}</span> / 
                          <span className="text-red-600">{run.failed_count}</span> / 
                          <span className="text-yellow-600">{run.inconclusive_count}</span>
                        </TableCell>
                        <TableCell>
                          {run.critical_count > 0 && <span className="text-red-600 font-medium">Critical: {run.critical_count}</span>}
                          {run.high_count > 0 && <span className="text-orange-600 font-medium ml-2">High: {run.high_count}</span>}
                          {run.medium_count > 0 && <span className="text-yellow-600 font-medium ml-2">Medium: {run.medium_count}</span>}
                          {run.low_count > 0 && <span className="text-blue-600 font-medium ml-2">Low: {run.low_count}</span>}
                        </TableCell>
                        <TableCell>{formatCost(run.total_cost_usd)}</TableCell>
                        <TableCell className="text-sm text-muted-foreground">{formatDate(run.created_at)}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
              <div className="flex items-center justify-between mt-4">
                <Button variant="outline" onClick={() => setPage(p => Math.max(1, p - 1))} disabled={page === 1}>Previous</Button>
                <span>Page {page} of {totalPages}</span>
                <Button variant="outline" onClick={() => setPage(p => p + 1)} disabled={page >= totalPages}>Next</Button>
              </div>
            </>
          )}
        </CardContent>
      </Card>
    </div>
  );
}