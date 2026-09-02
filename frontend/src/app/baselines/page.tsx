"use client";

import { useEffect, useState, useCallback } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { api } from "@/lib/api";
import { formatDate } from "@/lib/utils";
import { useAuth } from "@/lib/auth";
import { Plus, Eye, Check, X, Clock, Trash2 } from "lucide-react";

interface Baseline {
  id: string;
  suite_id: string;
  suite_version: number;
  run_id: string;
  name: string;
  description: string | null;
  framework_version: string;
  model_versions: Record<string, string>;
  prompt_versions: Record<string, string>;
  approved_by: string | null;
  approved_at: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

interface BaselineItem {
  id: string;
  baseline_id: string;
  test_case_id: string;
  verdict: string;
  confidence: number;
  evidence: unknown[];
  created_at: string;
}

export default function BaselinesPage() {
  const { isAuthenticated, isLoading } = useAuth();
  const [baselines, setBaselines] = useState<Baseline[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedBaseline, setSelectedBaseline] = useState<Baseline | null>(null);
  const [baselineItems, setBaselineItems] = useState<BaselineItem[]>([]);
  const [itemsLoading, setItemsLoading] = useState(false);

  const fetchBaselines = useCallback(async () => {
    try {
      const res = await api.get("/baselines");
      setBaselines(res.data);
    } catch (error) {
      console.error("Failed to fetch baselines:", error);
    } finally {
      setLoading(false);
    }
  }, []);

  const fetchBaselineItems = useCallback(async (baselineId: string) => {
    setItemsLoading(true);
    try {
      const res = await api.get(`/baselines/${baselineId}/items`);
      setBaselineItems(res.data);
      setSelectedBaseline(baselines.find(b => b.id === baselineId) || null);
    } catch (error) {
      console.error("Failed to fetch baseline items:", error);
    } finally {
      setItemsLoading(false);
    }
  }, [baselines]);

  const handleApprove = async (baselineId: string) => {
    try {
      await api.post(`/baselines/${baselineId}/approve`);
      fetchBaselines();
    } catch (error) {
      console.error("Failed to approve baseline:", error);
    }
  };

  const handleDeactivate = async (baselineId: string) => {
    try {
      await api.post(`/baselines/${baselineId}/deactivate`);
      fetchBaselines();
    } catch (error) {
      console.error("Failed to deactivate baseline:", error);
    }
  };

  const handleDelete = async (baselineId: string) => {
    if (!confirm("Are you sure you want to delete this baseline?")) return;
    try {
      await api.delete(`/baselines/${baselineId}`);
      fetchBaselines();
    } catch (error) {
      console.error("Failed to delete baseline:", error);
    }
  };

  useEffect(() => {
    if (!isLoading) {
      if (!isAuthenticated) {
        window.location.href = "/login";
      } else {
        fetchBaselines();
      }
    }
  }, [isAuthenticated, isLoading, fetchBaselines]);

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
          <h1 className="text-3xl font-bold">Baselines</h1>
          <p className="text-muted-foreground">Manage approved baselines for regression detection</p>
        </div>
      </div>

      {loading ? (
        <Card>
          <CardContent className="text-center py-12">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary mx-auto"></div>
            <p className="mt-4 text-muted-foreground">Loading baselines...</p>
          </CardContent>
        </Card>
      ) : baselines.length === 0 ? (
        <Card>
          <CardContent className="text-center py-12">
            <p className="text-muted-foreground">No baselines found. Create one from a completed run.</p>
          </CardContent>
        </Card>
      ) : (
        <Card>
          <CardHeader>
            <CardTitle>All Baselines ({baselines.length})</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Name</TableHead>
                    <TableHead>Suite</TableHead>
                    <TableHead>Version</TableHead>
                    <TableHead>Run</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead>Approved By</TableHead>
                    <TableHead>Approved At</TableHead>
                    <TableHead>Created</TableHead>
                    <TableHead className="w-40">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {baselines.map((baseline) => (
                    <TableRow key={baseline.id}>
                      <TableCell className="font-medium">{baseline.name}</TableCell>
                      <TableCell className="font-mono text-sm">{baseline.suite_id.slice(0, 8)}...</TableCell>
                      <TableCell>v{baseline.suite_version}</TableCell>
                      <TableCell className="font-mono text-sm">{baseline.run_id.slice(0, 8)}...</TableCell>
                      <TableCell>
                        <Badge variant={baseline.is_active ? "default" : "secondary"}>
                          {baseline.is_active ? "Active" : "Inactive"}
                        </Badge>
                      </TableCell>
                      <TableCell className="font-mono text-xs">
                        {baseline.approved_by?.slice(0, 8) || "N/A"}
                      </TableCell>
                      <TableCell>{baseline.approved_at ? formatDate(baseline.approved_at) : "N/A"}</TableCell>
                      <TableCell>{formatDate(baseline.created_at)}</TableCell>
                      <TableCell>
                        <div className="flex items-center gap-1">
                          <Button variant="ghost" size="icon" onClick={() => fetchBaselineItems(baseline.id)}>
                            <Eye className="h-4 w-4" />
                          </Button>
                          {!baseline.is_active && baseline.approved_at ? (
                            <Button variant="ghost" size="icon" onClick={() => handleApprove(baseline.id)}>
                              <Check className="h-4 w-4 text-green-600" />
                            </Button>
                          ) : baseline.is_active ? (
                            <Button variant="ghost" size="icon" onClick={() => handleDeactivate(baseline.id)}>
                              <X className="h-4 w-4 text-red-600" />
                            </Button>
                          ) : (
                            <Badge variant="secondary">Pending</Badge>
                          )}
                          <Button variant="ghost" size="icon" onClick={() => handleDelete(baseline.id)}>
                            <Trash2 className="h-4 w-4 text-destructive" />
                          </Button>
                        </div>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          </CardContent>
        </Card>
      )}

      {selectedBaseline && (
        <Card>
          <CardHeader className="flex flex-row items-center justify-between">
            <CardTitle>Baseline Items: {selectedBaseline.name}</CardTitle>
            <Button variant="ghost" size="icon" onClick={() => { setSelectedBaseline(null); setBaselineItems([]); }}>
              <X className="h-4 w-4" />
            </Button>
          </CardHeader>
          <CardContent>
            {itemsLoading ? (
              <div className="text-center py-8">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary mx-auto"></div>
                <p className="mt-4 text-muted-foreground">Loading items...</p>
              </div>
            ) : baselineItems.length === 0 ? (
              <p className="text-center text-muted-foreground py-8">No items in this baseline</p>
            ) : (
              <div className="overflow-x-auto">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Test Case</TableHead>
                      <TableHead>Verdict</TableHead>
                      <TableHead>Confidence</TableHead>
                      <TableHead>Created</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {baselineItems.map((item) => (
                      <TableRow key={item.id}>
                        <TableCell className="font-mono text-sm">{item.test_case_id.slice(0, 12)}...</TableCell>
                        <TableCell>
                          <Badge variant={
                            item.verdict === "PASS" ? "default" :
                            item.verdict === "FAIL" ? "destructive" : "secondary"
                          }>
                            {item.verdict}
                          </Badge>
                        </TableCell>
                        <TableCell>{(item.confidence * 100).toFixed(1)}%</TableCell>
                        <TableCell className="text-sm text-muted-foreground">{formatDate(item.created_at)}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  );
}