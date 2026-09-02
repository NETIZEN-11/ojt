"use client";

import { useEffect, useState, useCallback } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "@/components/ui/dialog";
import { Textarea } from "@/components/ui/textarea";
import { api } from "@/lib/api";
import { formatDate, getSeverityColor } from "@/lib/utils";
import { useAuth } from "@/lib/auth";
import { useParams, useRouter } from "next/navigation";
import { ArrowLeft, Edit, AlertTriangle, CheckCircle, XCircle, AlertCircle, Flag } from "lucide-react";

interface ReviewItem {
  id: string;
  run_id: string;
  regression_id: string | null;
  severity: string;
  confidence: number;
  category: string;
  status: string;
  label: string | null;
  assigned_to: string | null;
  reviewed_by: string | null;
  reviewed_at: string | null;
  notes: string | null;
  created_at: string;
  updated_at: string;
  run?: {
    id: string;
    suite_id: string;
    target_agent_id: string;
  };
  regression?: {
    id: string;
    test_case_id: string;
    previous_verdict: string;
    current_verdict: string;
    regression_type: string;
    evidence: unknown[];
  };
}

export default function ReviewDetailPage() {
  const params = useParams();
  const reviewId = params.id as string;
  const router = useRouter();
  const { isAuthenticated, isLoading } = useAuth();
  const [review, setReview] = useState<ReviewItem | null>(null);
  const [loading, setLoading] = useState(true);
  const [newLabel, setNewLabel] = useState("");
  const [newNotes, setNewNotes] = useState("");
  const [saving, setSaving] = useState(false);

  const fetchReview = useCallback(async () => {
    try {
      const res = await api.get(`/reviews/${reviewId}`);
      setReview(res.data);
      if (res.data.label) setNewLabel(res.data.label);
      if (res.data.notes) setNewNotes(res.data.notes);
    } catch (error) {
      console.error("Failed to fetch review:", error);
    } finally {
      setLoading(false);
    }
  }, [reviewId]);

  useEffect(() => {
    if (!isLoading) {
      if (!isAuthenticated) {
        window.location.href = "/login";
      } else {
        fetchReview();
      }
    }
  }, [isAuthenticated, isLoading, fetchReview]);

  const handleLabelReview = async (label: string) => {
    setSaving(true);
    try {
      await api.patch(`/reviews/${reviewId}`, { label, notes: newNotes });
      fetchReview();
    } catch (error) {
      console.error("Failed to label review:", error);
    } finally {
      setSaving(false);
    }
  };

  const labels = ["confirmed_regression", "false_positive", "non_blocking", "needs_escalation"];

  const getStatusBadge = (status: string) => {
    switch (status) {
      case "pending": return <Badge variant="secondary">Pending</Badge>;
      case "in_review": return <Badge variant="default">In Review</Badge>;
      case "resolved": return <Badge variant="default" className="bg-green-100 text-green-800">Resolved</Badge>;
      case "escalated": return <Badge variant="destructive">Escalated</Badge>;
      default: return <Badge variant="secondary">{status}</Badge>;
    }
  };

  const getLabelBadge = (label: string | null) => {
    if (!label) return <Badge variant="outline">Unlabeled</Badge>;
    switch (label) {
      case "confirmed_regression": return <Badge className="bg-red-100 text-red-800"><AlertTriangle className="mr-1 h-3 w-3" /> Confirmed</Badge>;
      case "false_positive": return <Badge className="bg-green-100 text-green-800"><CheckCircle className="mr-1 h-3 w-3" /> False Positive</Badge>;
      case "non_blocking": return <Badge className="bg-blue-100 text-blue-800"><Flag className="mr-1 h-3 w-3" /> Non-Blocking</Badge>;
      case "needs_escalation": return <Badge className="bg-orange-100 text-orange-800"><AlertCircle className="mr-1 h-3 w-3" /> Needs Escalation</Badge>;
      default: return <Badge variant="outline">{label}</Badge>;
    }
  };

  if (isLoading || !isAuthenticated) {
    return (
      <div className="flex h-screen items-center justify-center">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
      </div>
    );
  }

  if (!review) {
    return (
      <div className="p-6 text-center">
        <h2 className="text-xl font-medium">Review not found</h2>
        <Button variant="outline" onClick={() => router.push("/reviews")} className="mt-4">
          <ArrowLeft className="mr-2 h-4 w-4" /> Back to Reviews
        </Button>
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="icon" onClick={() => router.push("/reviews")}>
            <ArrowLeft className="h-4 w-4" />
          </Button>
          <div>
            <h1 className="text-3xl font-bold">Review Details</h1>
            <p className="text-muted-foreground">{review.id}</p>
          </div>
        </div>
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2">
            <span className="text-sm text-muted-foreground">Status:</span>
            {getStatusBadge(review.status)}
            <span className="text-sm text-muted-foreground">Label:</span>
            {getLabelBadge(review.label)}
          </div>
        </div>
      </div>

      <Tabs defaultValue="overview" className="space-y-4">
        <TabsList>
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="regression">Regression</TabsTrigger>
          <TabsTrigger value="run">Run Details</TabsTrigger>
          <TabsTrigger value="label">Label & Resolve</TabsTrigger>
        </TabsList>

        <TabsContent value="overview">
          <div className="grid gap-4 md:grid-cols-3">
            <Card>
              <CardHeader><CardTitle>Severity</CardTitle></CardHeader>
              <CardContent>
                <Badge className={`${getSeverityColor(review.severity)} text-lg`}>{review.severity}</Badge>
              </CardContent>
            </Card>
            <Card>
              <CardHeader><CardTitle>Confidence</CardTitle></CardHeader>
              <CardContent>
                <p className="text-2xl font-bold">{(review.confidence * 100).toFixed(1)}%</p>
              </CardContent>
            </Card>
            <Card>
              <CardHeader><CardTitle>Category</CardTitle></CardHeader>
              <CardContent>
                <Badge variant="secondary" className="text-lg">{review.category}</Badge>
              </CardContent>
            </Card>
          </div>

          <Card>
            <CardHeader><CardTitle>Review Information</CardTitle></CardHeader>
            <CardContent className="space-y-4">
              <div className="grid gap-4 md:grid-cols-3">
                <div>
                  <p className="text-sm text-muted-foreground">Review ID</p>
                  <p className="font-mono text-sm">{review.id}</p>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Run ID</p>
                  <p className="font-mono text-sm">{review.run_id}</p>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Created</p>
                  <p>{formatDate(review.created_at)}</p>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Updated</p>
                  <p>{formatDate(review.updated_at)}</p>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Assigned To</p>
                  <p className="font-mono text-xs">{review.assigned_to?.slice(0, 8) || "Unassigned"}</p>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Reviewed By</p>
                  <p className="font-mono text-xs">{review.reviewed_by?.slice(0, 8) || "N/A"}</p>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Reviewed At</p>
                  <p>{review.reviewed_at ? formatDate(review.reviewed_at) : "N/A"}</p>
                </div>
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Notes</p>
                <Textarea
                  value={review.notes || ""}
                  onChange={(e) => setNewNotes(e.target.value)}
                  placeholder="Add review notes..."
                  rows={3}
                  disabled={review.status === "resolved"}
                />
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="regression">
          {review.regression ? (
            <div className="space-y-6">
              <div className="grid gap-4 md:grid-cols-4">
                <Card>
                  <CardHeader><CardTitle>Test Case</CardTitle></CardHeader>
                  <CardContent>
                    <p className="font-mono text-sm">{review.regression.test_case_id.slice(0, 12)}...</p>
                  </CardContent>
                </Card>
                <Card>
                  <CardHeader><CardTitle>Previous Verdict</CardTitle></CardHeader>
                  <CardContent>
                    <Badge variant={
                      review.regression.previous_verdict === "PASS" ? "default" :
                      review.regression.previous_verdict === "FAIL" ? "destructive" : "secondary"
                    } className="text-lg">
                      {review.regression.previous_verdict}
                    </Badge>
                  </CardContent>
                </Card>
                <Card>
                  <CardHeader><CardTitle>Current Verdict</CardTitle></CardHeader>
                  <CardContent>
                    <Badge variant={
                      review.regression.current_verdict === "PASS" ? "default" :
                      review.regression.current_verdict === "FAIL" ? "destructive" : "secondary"
                    } className="text-lg">
                      {review.regression.current_verdict}
                    </Badge>
                  </CardContent>
                </Card>
                <Card>
                  <CardHeader><CardTitle>Regression Type</CardTitle></CardHeader>
                  <CardContent>
                    <p className="font-medium">{review.regression.regression_type.replace(/_/g, " ")}</p>
                  </CardContent>
                </Card>
              </div>

              <Card>
                <CardHeader><CardTitle>Evidence</CardTitle></CardHeader>
                <CardContent>
                  {review.regression.evidence && review.regression.evidence.length > 0 ? (
                    <div className="space-y-2">
                      {review.regression.evidence.map((evidence: unknown, idx: number) => (
                        <div key={idx} className="p-3 bg-muted rounded text-sm font-mono">
                          {JSON.stringify(evidence, null, 2)}
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className="text-muted-foreground">No evidence recorded</p>
                  )}
                </CardContent>
              </Card>
            </div>
          ) : (
            <Card>
              <CardContent className="text-center py-12">
                <AlertTriangle className="h-12 w-12 text-muted-foreground mx-auto" />
                <h3 className="mt-4 text-lg font-medium">No regression details available</h3>
              </CardContent>
            </Card>
          )}
        </TabsContent>

        <TabsContent value="run">
          {review.run ? (
            <Card>
              <CardHeader><CardTitle>Run Information</CardTitle></CardHeader>
              <CardContent className="space-y-4">
                <div className="grid gap-4 md:grid-cols-3">
                  <div>
                    <p className="text-sm text-muted-foreground">Run ID</p>
                    <p className="font-mono text-sm">{review.run.id}</p>
                  </div>
                  <div>
                    <p className="text-sm text-muted-foreground">Suite</p>
                    <p className="font-mono text-xs">{review.run.suite_id?.slice(0, 8) || "N/A"}</p>
                  </div>
                  <div>
                    <p className="text-sm text-muted-foreground">Target Agent</p>
                    <p className="font-mono text-xs">{review.run.target_agent_id?.slice(0, 8) || "N/A"}</p>
                  </div>
                </div>
                <Button variant="outline" onClick={() => router.push(`/runs/${review.run_id}`)}>
                  View Full Run Details
                </Button>
              </CardContent>
            </Card>
          ) : (
            <Card>
              <CardContent className="text-center py-12">
                <p className="text-muted-foreground">Run details not available</p>
              </CardContent>
            </Card>
          )}
        </TabsContent>

        <TabsContent value="label">
          <div className="space-y-6">
            <div>
              <h4 className="font-medium mb-4">Select Label</h4>
              <div className="grid gap-4 md:grid-cols-2">
                {labels.map((label) => (
                  <Button
                    key={label}
                    variant={newLabel === label ? "default" : "outline"}
                    className="w-full justify-start h-16"
                    onClick={() => setNewLabel(label)}
                  >
                    <div className="flex flex-col items-start">
                      {label === "confirmed_regression" && <AlertTriangle className="h-6 w-6 mb-1" />}
                      {label === "false_positive" && <CheckCircle className="h-6 w-6 mb-1" />}
                      {label === "non_blocking" && <Flag className="h-6 w-6 mb-1" />}
                      {label === "needs_escalation" && <AlertCircle className="h-6 w-6 mb-1" />}
                      <span className="font-medium">{label.replace("_", " ")}</span>
                      <span className="text-xs text-muted-foreground">
                        {label === "confirmed_regression" && "This is a real regression that needs fixing"}
                        {label === "false_positive" && "The detection was incorrect, no regression"}
                        {label === "non_blocking" && "Real regression but doesn't block deployment"}
                        {label === "needs_escalation" && "Requires further investigation"}
                      </span>
                    </div>
                  </Button>
                ))}
              </div>
            </div>

            <div>
              <h4 className="font-medium mb-2">Resolution Notes</h4>
              <Textarea
                value={newNotes}
                onChange={(e) => setNewNotes(e.target.value)}
                placeholder="Explain your decision..."
                rows={4}
              />
            </div>

            {review.status !== "resolved" && newLabel && (
              <div className="p-4 bg-muted rounded-lg border">
                <p className="font-medium mb-2">Ready to submit:</p>
                <p>Label: <strong>{newLabel.replace("_", " ")}</strong></p>
                <p>Notes: {newNotes || "(none)"}</p>
                <Button
                  onClick={() => handleLabelReview(newLabel)}
                  disabled={saving}
                  className="mt-4 w-full"
                >
                  {saving ? "Submitting..." : `Submit as ${newLabel.replace("_", " ")}`}
                </Button>
              </div>
            )}
          </div>
        </TabsContent>
      </Tabs>
    </div>
  );
}