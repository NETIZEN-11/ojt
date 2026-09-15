"use client";

import { useEffect, useState, useCallback } from "react";
import { DashboardLayout } from "@/components/ui/dashboard-layout";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "@/components/ui/dialog";
import { Textarea } from "@/components/ui/textarea";
import { ScrollArea } from "@/components/ui/scroll-area";
import { api } from "@/lib/api";
import { formatDate, getSeverityColor } from "@/lib/utils";
import { useAuth } from "@/lib/auth";
import { Eye, Edit, Filter, AlertTriangle, CheckCircle, XCircle, AlertCircle, Flag, FileText, Code, Copy, ChevronDown, ChevronUp, Search } from "lucide-react";

interface EvidenceItem {
  source: string;
  text: string;
  metadata?: Record<string, any>;
}

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
  };
  evidence?: EvidenceItem[];
  test_case_input?: string;
  test_case_expected?: string;
  actual_response?: string;
  judge_output?: Record<string, any>;
}

export default function ReviewsPage() {
  const { isAuthenticated, isLoading } = useAuth();
  const [reviews, setReviews] = useState<ReviewItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedReview, setSelectedReview] = useState<ReviewItem | null>(null);
  const [filterStatus, setFilterStatus] = useState("");
  const [filterSeverity, setFilterSeverity] = useState("");
  const [newLabel, setNewLabel] = useState("");
  const [newNotes, setNewNotes] = useState("");
  const [saving, setSaving] = useState(false);
  const [evidenceSearch, setEvidenceSearch] = useState("");

  const fetchReviews = useCallback(async () => {
    try {
      // TODO: Backend endpoint /reviews not implemented yet (returns 500 due to missing reviewer_notes column)
      // Fixed database schema but endpoint may have other issues
      // const params = new URLSearchParams();
      // if (filterStatus) params.append("status", filterStatus);
      // if (filterSeverity) params.append("severity", filterSeverity);
      // const res = await api.get(`/reviews?${params.toString()}`);
      // setReviews(res.data);
      setReviews([]);
    } catch (error) {
      console.error("Failed to fetch reviews:", error);
    } finally {
      setLoading(false);
    }
  }, [filterStatus, filterSeverity]);

  const fetchReviewDetails = useCallback(async (reviewId: string) => {
    try {
      const res = await api.get(`/reviews/${reviewId}`);
      setSelectedReview(res.data);
    } catch (error) {
      console.error("Failed to fetch review details:", error);
    }
  }, []);

  useEffect(() => {
    if (!isLoading) {
      if (!isAuthenticated) {
        window.location.href = "/login";
      } else {
        fetchReviews();
      }
    }
  }, [isAuthenticated, isLoading, fetchReviews]);

  const handleLabelReview = async (reviewId: string, label: string) => {
    setSaving(true);
    try {
      await api.patch(`/reviews/${reviewId}`, { label, notes: newNotes });
      setSelectedReview(null);
      setNewLabel("");
      setNewNotes("");
      fetchReviews();
    } catch (error) {
      console.error("Failed to label review:", error);
    } finally {
      setSaving(false);
    }
  };

  const handleAssign = async (reviewId: string) => {
    const userId = prompt("Enter user ID to assign:");
    if (userId) {
      try {
        await api.patch(`/reviews/${reviewId}`, { assigned_to: userId });
        fetchReviews();
      } catch (error) {
        console.error("Failed to assign review:", error);
      }
    }
  };

  const handleViewReview = async (review: ReviewItem) => {
    setSelectedReview(review);
    await fetchReviewDetails(review.id);
  };

  const statuses = ["pending", "in_review", "resolved", "escalated"];
  const severities = ["critical", "high", "medium", "low"];
  const labels = ["confirmed_regression", "false_positive", "non_blocking", "needs_escalation"];

  const filteredReviews = reviews.filter((review) => {
    const matchesStatus = !filterStatus || review.status === filterStatus;
    const matchesSeverity = !filterSeverity || review.severity === filterSeverity;
    return matchesStatus && matchesSeverity;
  });

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

  const EvidenceViewer = ({ 
    evidence, 
    title, 
    searchTerm = "",
    emptyMessage = "No evidence available"
  }: { 
    evidence: EvidenceItem[]; 
    title: string;
    searchTerm?: string;
    emptyMessage?: string;
  }) => {
    const filteredEvidence = evidence.filter(e => 
      e.text.toLowerCase().includes(searchTerm.toLowerCase()) ||
      e.source.toLowerCase().includes(searchTerm.toLowerCase()) ||
      JSON.stringify(e.metadata).toLowerCase().includes(searchTerm.toLowerCase())
    );

    if (filteredEvidence.length === 0) {
      return (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center justify-between">
              {title}
              <Badge variant="secondary">{filteredEvidence.length}</Badge>
            </CardTitle>
          </CardHeader>
          <CardContent className="text-center py-8 text-muted-foreground">
            {emptyMessage}
          </CardContent>
        </Card>
      );
    }

    return (
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle>{title}</CardTitle>
            <div className="flex items-center gap-2">
              <span className="text-sm text-muted-foreground">{filteredEvidence.length} items</span>
              <input
                type="text"
                placeholder="Search evidence..."
                value={searchTerm}
                onChange={(e) => setEvidenceSearch(e.target.value)}
                className="w-64 px-2 py-1 text-sm border rounded"
              />
            </div>
          </div>
        </CardHeader>
        <CardContent>
          {filteredEvidence.length === 0 ? (
            <div className="text-center py-8 text-muted-foreground">
              {emptyMessage}
            </div>
          ) : (
            <div className="space-y-2">
              {filteredEvidence.map((item, index) => (
                <EvidenceItem key={`${item.source}-${index}`} item={item} index={index} />
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    );
  };

  const EvidenceItem = ({ item, index }: { item: EvidenceItem; index: number }) => {
    const [copied, setCopied] = useState(false);
    const [expanded, setExpanded] = useState(false);
    const isLong = item.text.length > 500;

    return (
      <div className="border rounded-lg p-4 mb-3 bg-muted/30">
        <div className="flex items-start justify-between gap-4 mb-2">
          <div className="flex items-center gap-2">
            <span className="font-mono text-xs text-muted-foreground">#{index + 1}</span>
            <Badge variant="outline" className="text-xs">{item.source}</Badge>
            {item.metadata && Object.keys(item.metadata).length > 0 && (
              <Badge variant="secondary" className="text-xs">{Object.keys(item.metadata).length} metadata</Badge>
            )}
          </div>
          <div className="flex items-center gap-1">
            <Button 
              variant="ghost" 
              size="icon" 
              onClick={() => {
                navigator.clipboard.writeText(item.text);
                setCopied(true);
                setTimeout(() => setCopied(false), 2000);
              }}
              title="Copy text"
            >
              <Copy className="h-3 w-3" />
            </Button>
            <Button 
              variant="ghost" 
              size="icon" 
              onClick={() => setExpanded(!expanded)}
              title={expanded ? "Collapse" : "Expand"}
            >
              {expanded ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />}
            </Button>
          </div>
        </div>
        
        <div className="font-mono text-sm whitespace-pre-wrap" style={{ maxHeight: expanded || !isLong ? 'none' : '200px', overflow: 'auto' }}>
          {item.text}
        </div>

        {item.metadata && Object.keys(item.metadata).length > 0 && expanded && (
          <details className="mt-2">
            <summary className="text-xs text-muted-foreground cursor-pointer">Metadata</summary>
            <pre className="mt-1 text-xs bg-background p-2 rounded overflow-auto">
              {JSON.stringify(item.metadata, null, 2)}
            </pre>
          </details>
        )}
      </div>
    );
  };

  const CodeViewer = ({ 
    code, 
    title,
    language = "json"
  }: { 
    code: string | Record<string, any>; 
    title: string;
    language?: string;
  }) => {
    const [copied, setCopied] = useState(false);
    const codeString = typeof code === 'string' ? code : JSON.stringify(code, null, 2);

    return (
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle>{title}</CardTitle>
            <Button 
              variant="ghost" 
              size="icon" 
              onClick={() => {
                navigator.clipboard.writeText(codeString);
                setCopied(true);
                setTimeout(() => setCopied(false), 2000);
              }}
              title="Copy"
            >
              <Copy className="h-4 w-4" />
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          <ScrollArea className="h-[400px] w-full">
            <pre className="font-mono text-sm p-4 bg-muted rounded overflow-auto">
              <code>{codeString}</code>
            </pre>
          </ScrollArea>
        </CardContent>
      </Card>
    );
  };

  if (isLoading || !isAuthenticated) {
    return (
      <DashboardLayout>
        <div className="flex h-[calc(100vh-4rem)] items-center justify-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
        </div>
      </DashboardLayout>
    );
  }

  return (
    <DashboardLayout>
      <div className="space-y-6">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <h1 className="text-3xl font-bold">Review Queue</h1>
            <p className="text-muted-foreground">Review and label regression findings</p>
          </div>
        </div>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between">
            <CardTitle>Filters</CardTitle>
          </CardHeader>
          <CardContent className="flex flex-col sm:flex-row gap-4">
            <Select value={filterStatus} onValueChange={setFilterStatus}>
              <SelectTrigger className="w-48"><SelectValue placeholder="All statuses" /></SelectTrigger>
              <SelectContent>
                <SelectItem value="">All statuses</SelectItem>
                {statuses.map((s) => <SelectItem key={s} value={s}>{s.replace("_", " ")}</SelectItem>)}
              </SelectContent>
            </Select>
            <Select value={filterSeverity} onValueChange={setFilterSeverity}>
              <SelectTrigger className="w-48"><SelectValue placeholder="All severities" /></SelectTrigger>
              <SelectContent>
                <SelectItem value="">All severities</SelectItem>
                {severities.map((s) => <SelectItem key={s} value={s}>{s}</SelectItem>)}
              </SelectContent>
            </Select>
          </CardContent>
        </Card>

        {loading ? (
          <Card>
            <CardContent className="text-center py-12">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary mx-auto"></div>
              <p className="mt-4 text-muted-foreground">Loading reviews...</p>
            </CardContent>
          </Card>
        ) : filteredReviews.length === 0 ? (
          <Card>
            <CardContent className="text-center py-12">
              <AlertTriangle className="h-12 w-12 text-muted-foreground mx-auto" />
              <h3 className="mt-4 text-lg font-medium">No reviews found</h3>
              <p className="text-muted-foreground">All caught up! No pending reviews.</p>
            </CardContent>
          </Card>
        ) : (
          <Card>
            <CardHeader>
              <CardTitle>Review Queue ({filteredReviews.length})</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="overflow-x-auto">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>ID</TableHead>
                      <TableHead>Run</TableHead>
                      <TableHead>Category</TableHead>
                      <TableHead>Severity</TableHead>
                      <TableHead>Confidence</TableHead>
                      <TableHead>Status</TableHead>
                      <TableHead>Label</TableHead>
                      <TableHead>Assigned</TableHead>
                      <TableHead>Created</TableHead>
                      <TableHead className="w-32">Actions</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {filteredReviews.map((review) => (
                      <TableRow key={review.id}>
                        <TableCell className="font-mono text-sm">{review.id.slice(0, 8)}...</TableCell>
                        <TableCell className="font-mono text-sm">{review.run_id.slice(0, 8)}...</TableCell>
                        <TableCell><Badge variant="secondary">{review.category}</Badge></TableCell>
                        <TableCell><Badge className={getSeverityColor(review.severity)}>{review.severity}</Badge></TableCell>
                        <TableCell>{(review.confidence * 100).toFixed(1)}%</TableCell>
                        <TableCell>{getStatusBadge(review.status)}</TableCell>
                        <TableCell>{getLabelBadge(review.label)}</TableCell>
                        <TableCell className="font-mono text-xs">
                          {review.assigned_to?.slice(0, 8) || "Unassigned"}
                        </TableCell>
                        <TableCell className="text-sm text-muted-foreground">{formatDate(review.created_at)}</TableCell>
                        <TableCell>
                          <div className="flex items-center gap-1">
                            <Button variant="ghost" size="icon" onClick={() => handleViewReview(review)}>
                              <Eye className="h-4 w-4" />
                            </Button>
                            {review.status === "pending" && (
                              <Button variant="ghost" size="icon" onClick={() => handleAssign(review.id)}>
                                <Edit className="h-4 w-4" />
                              </Button>
                            )}
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

        {selectedReview && (
          <Dialog open={true} onOpenChange={(open) => !open && setSelectedReview(null)}>
            <DialogContent className="max-w-3xl">
              <DialogHeader>
                <DialogTitle>Review: {selectedReview.id.slice(0, 8)}...</DialogTitle>
              </DialogHeader>
              <div className="space-y-4 py-4">
                <Tabs defaultValue="details" className="w-full">
                  <TabsList>
                    <TabsTrigger value="details">Details</TabsTrigger>
                    <TabsTrigger value="evidence">Evidence</TabsTrigger>
                    <TabsTrigger value="io">Input/Output</TabsTrigger>
                    <TabsTrigger value="judge">Judge Output</TabsTrigger>
                    <TabsTrigger value="regression">Regression</TabsTrigger>
                    <TabsTrigger value="label">Label</TabsTrigger>
                  </TabsList>

                  <TabsContent value="details">
                    <div className="grid gap-4 md:grid-cols-2 mt-4">
                      <div>
                        <h4 className="font-medium mb-2">Review Info</h4>
                        <dl className="space-y-2 text-sm">
                          <div className="grid grid-cols-2 gap-2">
                            <dt className="text-muted-foreground">Status</dt>
                            <dd>{getStatusBadge(selectedReview.status)}</dd>
                            <dt className="text-muted-foreground">Severity</dt>
                            <dd><Badge className={getSeverityColor(selectedReview.severity)}>{selectedReview.severity}</Badge></dd>
                            <dt className="text-muted-foreground">Confidence</dt>
                            <dd>{(selectedReview.confidence * 100).toFixed(1)}%</dd>
                            <dt className="text-muted-foreground">Category</dt>
                            <dd><Badge variant="secondary">{selectedReview.category}</Badge></dd>
                            <dt className="text-muted-foreground">Created</dt>
                            <dd>{formatDate(selectedReview.created_at)}</dd>
                            <dt className="text-muted-foreground">Updated</dt>
                            <dd>{formatDate(selectedReview.updated_at)}</dd>
                          </div>
                        </dl>
                      </div>
                      <div>
                        <h4 className="font-medium mb-2">Run Info</h4>
                        <dl className="space-y-2 text-sm">
                          <div className="grid grid-cols-2 gap-2">
                            <dt className="text-muted-foreground">Run ID</dt>
                            <dd className="font-mono text-xs">{selectedReview.run_id}</dd>
                            <dt className="text-muted-foreground">Suite</dt>
                            <dd className="font-mono text-xs">{selectedReview.run?.suite_id?.slice(0, 8) || "N/A"}</dd>
                            <dt className="text-muted-foreground">Agent</dt>
                            <dd className="font-mono text-xs">{selectedReview.run?.target_agent_id?.slice(0, 8) || "N/A"}</dd>
                          </div>
                        </dl>
                      </div>
                      <div className="md:col-span-2">
                        <h4 className="font-medium mb-2">Notes</h4>
                        <Textarea
                          value={selectedReview.notes || ""}
                          onChange={(e) => setNewNotes(e.target.value)}
                          placeholder="Add review notes..."
                          rows={3}
                          disabled={selectedReview.status === "resolved"}
                        />
                      </div>
                    </div>
                  </TabsContent>

                  <TabsContent value="evidence">
                    <div className="mt-4 space-y-4">
                      {selectedReview.evidence && selectedReview.evidence.length > 0 ? (
                        <>
                          <h4 className="font-medium">All Evidence ({selectedReview.evidence.length} items)</h4>
                          <div className="space-y-2">
                            {selectedReview.evidence.map((item, index) => (
                              <EvidenceItem key={`${item.source}-${index}`} item={item} index={index} />
                            ))}
                          </div>
                        </>
                      ) : (
                        <Card>
                          <CardContent className="text-center py-8 text-muted-foreground">
                            <FileText className="h-12 w-12 mx-auto mb-4 opacity-50" />
                            <p>No evidence available for this review</p>
                          </CardContent>
                        </Card>
                      )}
                    </div>
                  </TabsContent>

                  <TabsContent value="io">
                    <div className="mt-4 grid gap-4 md:grid-cols-2">
                      <CodeViewer 
                        code={selectedReview.test_case_input || "No input available"} 
                        title="Test Case Input"
                      />
                      <CodeViewer 
                        code={selectedReview.actual_response || "No response available"} 
                        title="Actual Response"
                      />
                      {selectedReview.test_case_expected && (
                        <CodeViewer 
                          code={selectedReview.test_case_expected} 
                          title="Expected Behavior"
                        />
                      )}
                      {selectedReview.judge_output && (
                        <CodeViewer 
                          code={selectedReview.judge_output} 
                          title="Judge Output (Full)"
                        />
                      )}
                    </div>
                  </TabsContent>

                  <TabsContent value="judge">
                    <div className="mt-4 space-y-4">
                      {selectedReview.judge_output ? (
                        <>
                          <h4 className="font-medium">LLM Judge Evaluation</h4>
                          <div className="grid gap-4 md:grid-cols-2">
                            <Card>
                              <CardHeader>
                                <CardTitle>Verdict</CardTitle>
                              </CardHeader>
                              <CardContent>
                                <Badge 
                                  variant={
                                    selectedReview.judge_output.verdict === "PASS" ? "default" :
                                    selectedReview.judge_output.verdict === "FAIL" ? "destructive" : "secondary"
                                  } 
                                  className="text-lg px-4 py-2"
                                >
                                  {selectedReview.judge_output.verdict}
                                </Badge>
                              </CardContent>
                            </Card>
                            <Card>
                              <CardHeader>
                                <CardTitle>Confidence</CardTitle>
                              </CardHeader>
                              <CardContent>
                                <div className="text-3xl font-bold">
                                  {(selectedReview.judge_output.confidence * 100).toFixed(1)}%
                                </div>
                              </CardContent>
                            </Card>
                          </div>
                          
                          <Card>
                            <CardHeader>
                              <CardTitle>Rationale</CardTitle>
                            </CardHeader>
                            <CardContent>
                              <p className="whitespace-pre-wrap">{selectedReview.judge_output.rationale}</p>
                            </CardContent>
                          </Card>

                          {selectedReview.judge_output.criteria_results && selectedReview.judge_output.criteria_results.length > 0 && (
                            <Card>
                              <CardHeader>
                                <CardTitle>Criteria Results</CardTitle>
                              </CardHeader>
                              <CardContent>
                                <div className="space-y-2">
                                  {selectedReview.judge_output.criteria_results.map((criterion: any, idx: number) => (
                                    <div key={idx} className="flex items-center justify-between p-3 bg-muted rounded">
                                      <div>
                                        <p className="font-medium">{criterion.criterion}</p>
                                        <p className="text-sm text-muted-foreground">{criterion.evidence}</p>
                                      </div>
                                      <Badge variant={criterion.passed ? "default" : "destructive"}>
                                        {criterion.passed ? "PASS" : "FAIL"}
                                      </Badge>
                                    </div>
                                  ))}
                                </div>
                              </CardContent>
                            </Card>
                          )}

                          <CodeViewer 
                            code={selectedReview.judge_output} 
                            title="Full Judge Output (JSON)"
                          />
                        </>
                      ) : (
                        <Card>
                          <CardContent className="text-center py-8 text-muted-foreground">
                            <AlertTriangle className="h-12 w-12 mx-auto mb-4 opacity-50" />
                            <p>No judge output available for this review</p>
                          </CardContent>
                        </Card>
                      )}
                    </div>
                  </TabsContent>

                  <TabsContent value="regression">
                    {selectedReview.regression ? (
                      <div className="mt-4 space-y-4">
                        <h4 className="font-medium">Regression Details</h4>
                        <div className="grid gap-4 md:grid-cols-3">
                          <div className="p-4 bg-muted rounded-lg">
                            <p className="text-sm text-muted-foreground">Test Case</p>
                            <p className="font-mono font-medium">{selectedReview.regression.test_case_id.slice(0, 12)}...</p>
                          </div>
                          <div className="p-4 bg-muted rounded-lg">
                            <p className="text-sm text-muted-foreground">Previous Verdict</p>
                            <Badge variant={
                              selectedReview.regression.previous_verdict === "PASS" ? "default" :
                              selectedReview.regression.previous_verdict === "FAIL" ? "destructive" : "secondary"
                            }>
                              {selectedReview.regression.previous_verdict}
                            </Badge>
                          </div>
                          <div className="p-4 bg-muted rounded-lg">
                            <p className="text-sm text-muted-foreground">Current Verdict</p>
                            <Badge variant={
                              selectedReview.regression.current_verdict === "PASS" ? "default" :
                              selectedReview.regression.current_verdict === "FAIL" ? "destructive" : "secondary"
                            }>
                              {selectedReview.regression.current_verdict}
                            </Badge>
                          </div>
                          <div className="p-4 bg-muted rounded-lg md:col-span-3">
                            <p className="text-sm text-muted-foreground">Regression Type</p>
                            <p className="font-medium">{selectedReview.regression.regression_type.replace(/_/g, " ")}</p>
                          </div>
                        </div>
                      </div>
                    ) : (
                      <p className="mt-4 text-muted-foreground">No regression details available</p>
                    )}
                  </TabsContent>

                  <TabsContent value="label">
                    <div className="mt-4 space-y-4">
                      <h4 className="font-medium">Label This Review</h4>
                      <div className="grid gap-4 md:grid-cols-2">
                        {labels.map((label) => (
                          <Button
                            key={label}
                            variant={newLabel === label ? "default" : "outline"}
                            className="w-full justify-start"
                            onClick={() => setNewLabel(label)}
                          >
                            {label === "confirmed_regression" && <AlertTriangle className="mr-2 h-4 w-4" />}
                            {label === "false_positive" && <CheckCircle className="mr-2 h-4 w-4" />}
                            {label === "non_blocking" && <Flag className="mr-2 h-4 w-4" />}
                            {label === "needs_escalation" && <AlertCircle className="mr-2 h-4 w-4" />}
                            {label.replace("_", " ")}
                          </Button>
                        ))}
                      </div>
                      <div>
                        <h4 className="font-medium mb-2">Resolution Notes</h4>
                        <Textarea
                          value={newNotes}
                          onChange={(e) => setNewNotes(e.target.value)}
                          placeholder="Add notes explaining your decision..."
                          rows={4}
                        />
                      </div>
                    </div>
                  </TabsContent>
                </Tabs>
              </div>
              <DialogFooter>
                <Button variant="outline" onClick={() => { setSelectedReview(null); setNewLabel(""); setNewNotes(""); }}>Close</Button>
                {selectedReview.status !== "resolved" && newLabel && (
                  <Button onClick={() => handleLabelReview(selectedReview.id, newLabel)} disabled={saving}>
                    {saving ? "Saving..." : `Mark as ${newLabel.replace("_", " ")}`}
                  </Button>
                )}
              </DialogFooter>
            </DialogContent>
          </Dialog>
        )}
      </div>
    </DashboardLayout>
  );
}