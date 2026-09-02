"use client";

import { useEffect, useState, useCallback } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger, DialogFooter } from "@/components/ui/dialog";
import { Textarea } from "@/components/ui/textarea";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { api } from "@/lib/api";
import { formatDate, getSeverityColor } from "@/lib/utils";
import { useAuth } from "@/lib/auth";
import { useParams, useRouter } from "next/navigation";
import { Plus, Edit, Trash2, Download, Eye, Copy, AlertTriangle, Upload } from "lucide-react";

interface TestCase {
  id: string;
  test_case_id: string;
  category: string;
  severity: string;
  input: string;
  expected_behavior: Record<string, unknown>;
  metadata: Record<string, unknown>;
  is_active: boolean;
  version: number;
}

interface TestSuite {
  id: string;
  name: string;
  description: string | null;
  version: number;
  schema_version: string;
  is_active: boolean;
  test_cases: TestCase[];
  created_at: string;
  updated_at: string;
}

const LoadingScreen = () => (
  <div className="flex h-screen items-center justify-center">
    <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
  </div>
);

const NotAuthenticated = () => (
  <div className="flex h-screen items-center justify-center">
    <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
  </div>
);

const SuiteNotFound = ({ router }: { router: ReturnType<typeof useRouter> }) => (
  <div className="p-6 text-center">
    <h2 className="text-xl font-medium">Suite not found</h2>
    <Button variant="outline" onClick={() => router.push("/suites")} className="mt-4">
      Go Back
    </Button>
  </div>
);

const MainContent = ({
  suite,
  router,
  handleCreateVersion,
  showCreateCaseDialog,
  setShowCreateCaseDialog,
  showImportDialog,
  setShowImportDialog,
  importFormat,
  setImportFormat,
  importContent,
  setImportContent,
  newCase,
  setNewCase,
  handleCreateCase,
  handleImport,
  handleCreateVersion,
  editingCase,
  setEditingCase,
  handleUpdateCase,
  handleDeleteCase,
  suiteId,
  fetchSuite,
  formatDate,
  getSeverityColor,
  suite,
  router,
}: {
  suite: TestSuite | null;
  router: ReturnType<typeof useRouter>;
  handleCreateVersion: () => Promise<void>;
  showCreateCaseDialog: boolean;
  setShowCreateCaseDialog: (v: boolean) => void;
  showImportDialog: boolean;
  setShowImportDialog: (v: boolean) => void;
  importFormat: "yaml" | "json";
  setImportFormat: (v: "yaml" | "json") => void;
  importContent: string;
  setImportContent: (v: string) => void;
  newCase: {
    test_case_id: string;
    category: string;
    severity: string;
    input: string;
    expected_behavior_type: string;
    expected_behavior_matcher: Record<string, unknown>;
    metadata: Record<string, unknown>;
  };
  setNewCase: React.Dispatch<React.SetStateAction<{
    test_case_id: string;
    category: string;
    severity: string;
    input: string;
    expected_behavior_type: string;
    expected_behavior_matcher: Record<string, unknown>;
    metadata: Record<string, unknown>;
  }>>;
  handleCreateCase: () => Promise<void>;
  handleImport: () => Promise<void>;
  handleCreateVersion: () => Promise<void>;
  editingCase: TestCase | null;
  setEditingCase: React.Dispatch<React.SetStateAction<TestCase | null>>;
  handleUpdateCase: () => Promise<void>;
  handleDeleteCase: (caseId: string) => Promise<void>;
  suiteId: string;
  fetchSuite: () => Promise<void>;
  formatDate: (date: string) => string;
  getSeverityColor: (severity: string) => string;
  suite: TestSuite | null;
  router: ReturnType<typeof useRouter>;
}) => (
  !suite ? null : (
    <div className="p-6 space-y-6">
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-3xl font-bold">{suite.name}</h1>
          <div className="flex items-center gap-2 mt-1">
            <Badge variant="secondary">v{suite.version}</Badge>
            <Badge variant={suite.is_active ? "default" : "secondary"}>
              {suite.is_active ? "Active" : "Inactive"}
            </Badge>
            <span className="text-sm text-muted-foreground">Schema: {suite.schema_version}</span>
          </div>
          {suite.description && (
            <p className="text-muted-foreground mt-2">{suite.description}</p>
          )}
        </div>
        <div className="flex gap-2">
          <Button variant="outline" onClick={handleCreateVersion}>
            <Plus className="mr-2 h-4 w-4" /> New Version
          </Button>
          <Dialog open={showCreateCaseDialog} onOpenChange={setShowCreateCaseDialog}>
            <DialogTrigger asChild>
              <Button><Plus className="mr-2 h-4 w-4" /> Add Test Case</Button>
            </DialogTrigger>
            <DialogContent className="max-w-2xl">
              <DialogHeader>
                <DialogTitle>Add Test Case</DialogTitle>
              </DialogHeader>
              <div className="space-y-4 py-4">
                <div className="grid gap-4 md:grid-cols-2">
                  <div>
                    <Label htmlFor="test_case_id">Test Case ID</Label>
                    <Input
                      id="test_case_id"
                      value={newCase.test_case_id}
                      onChange={(e) => setNewCase({...newCase, test_case_id: e.target.value})}
                      placeholder="e.g., SAFETY_001"
                    />
                  </div>
                  <div>
                    <Label htmlFor="category">Category</Label>
                    <Select value={newCase.category} onValueChange={(v) => setNewCase({...newCase, category: v})}>
                      <SelectTrigger><SelectValue placeholder="Select category" /></SelectTrigger>
                      <SelectContent>
                        <SelectItem value="smoke">Smoke</SelectItem>
                        <SelectItem value="safety">Safety</SelectItem>
                        <SelectItem value="jailbreak">Jailbreak</SelectItem>
                        <SelectItem value="prompt_injection">Prompt Injection</SelectItem>
                        <SelectItem value="pii">PII</SelectItem>
                        <SelectItem value="policy">Policy</SelectItem>
                        <SelectItem value="refusal">Refusal</SelectItem>
                        <SelectItem value="tool_use">Tool Use</SelectItem>
                        <SelectItem value="hallucination">Hallucination</SelectItem>
                        <SelectItem value="bias">Bias</SelectItem>
                        <SelectItem value="adversarial">Adversarial</SelectItem>
                        <SelectItem value="custom">Custom</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  <div>
                    <Label htmlFor="severity">Severity</Label>
                    <Select value={newCase.severity} onValueChange={(v) => setNewCase({...newCase, severity: v})}>
                      <SelectTrigger><SelectValue placeholder="Select severity" /></SelectTrigger>
                      <SelectContent>
                        <SelectItem value="critical">Critical</SelectItem>
                        <SelectItem value="high">High</SelectItem>
                        <SelectItem value="medium">Medium</SelectItem>
                        <SelectItem value="low">Low</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  <div>
                    <Label htmlFor="expected_behavior_type">Expected Behavior Type</Label>
                    <Select value={newCase.expected_behavior_type} onValueChange={(v) => setNewCase({...newCase, expected_behavior_type: v})}>
                      <SelectTrigger><SelectValue placeholder="Select type" /></SelectTrigger>
                      <SelectContent>
                        <SelectItem value="exact_match">Exact Match</SelectItem>
                        <SelectItem value="regex_match">Regex Match</SelectItem>
                        <SelectItem value="keyword_match">Keyword Match</SelectItem>
                        <SelectItem value="refusal">Refusal</SelectItem>
                        <SelectItem value="structured_output">Structured Output</SelectItem>
                        <SelectItem value="llm_rubric">LLM Rubric</SelectItem>
                        <SelectItem value="custom">Custom</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                </div>
                <div>
                  <Label htmlFor="input">Input</Label>
                  <Textarea
                    id="input"
                    value={newCase.input}
                    onChange={(e) => setNewCase({...newCase, input: e.target.value})}
                    placeholder="Enter the test input..."
                    rows={3}
                  />
                </div>
                <div>
                  <Label>Expected Behavior Matcher Config (JSON)</Label>
                  <Textarea
                    value={JSON.stringify(newCase.expected_behavior_matcher, null, 2)}
                    onChange={(e) => {
                      try {
                        setNewCase({...newCase, expected_behavior_matcher: JSON.parse(e.target.value)});
                      } catch {}
                    }}
                    placeholder='{"keywords": ["hello", "hi"], "case_sensitive": false}'
                    rows={4}
                    className="font-mono text-sm"
                  />
                </div>
              </div>
              <DialogFooter>
                <Button variant="outline" onClick={() => setShowCreateCaseDialog(false)}>Cancel</Button>
                <Button onClick={handleCreateCase}>Create</Button>
              </DialogFooter>
            </DialogContent>
          </Dialog>
          <Dialog open={showImportDialog} onOpenChange={setShowImportDialog}>
            <DialogTrigger asChild>
              <Button variant="outline"><Upload className="mr-2 h-4 w-4" /> Import</Button>
            </DialogTrigger>
            <DialogContent className="max-w-2xl">
              <DialogHeader>
                <DialogTitle>Import Test Suite</DialogTitle>
              </DialogHeader>
              <div className="space-y-4 py-4">
                <div>
                  <Label>Format</Label>
                  <Select value={importFormat} onValueChange={(v) => setImportFormat(v as "yaml" | "json")}>
                    <SelectTrigger><SelectValue placeholder="Select format" /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="yaml">YAML</SelectItem>
                      <SelectItem value="json">JSON</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div>
                  <Label htmlFor="importContent">Content</Label>
                  <Textarea
                    id="importContent"
                    value={importContent}
                    onChange={(e) => setImportContent(e.target.value)}
                    placeholder="Paste YAML or JSON content here..."
                    className="min-h-[300px] font-mono text-sm"
                  />
                </div>
              </div>
              <DialogFooter>
                <Button variant="outline" onClick={() => setShowImportDialog(false)}>Cancel</Button>
                <Button onClick={handleImport}>Import</Button>
              </DialogFooter>
            </DialogContent>
          </Dialog>
        </div>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Test Cases ({suite?.test_cases.length ?? 0})</CardTitle>
        </CardHeader>
        <CardContent>
          {suite?.test_cases.length === 0 ? (
            <div className="text-center py-8">
              <p className="text-muted-foreground">No test cases yet. Click "Add Test Case" to create one.</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Test Case ID</TableHead>
                    <TableHead>Category</TableHead>
                    <TableHead>Severity</TableHead>
                    <TableHead>Input</TableHead>
                    <TableHead>Expected Behavior</TableHead>
                    <TableHead>Version</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead className="w-24">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {suite?.test_cases.map((tc) => (
                    <TableRow key={tc.id}>
                      <TableCell className="font-mono text-sm">{tc.test_case_id}</TableCell>
                      <TableCell><Badge variant="secondary">{tc.category}</Badge></TableCell>
                      <TableCell><Badge className={getSeverityColor(tc.severity)}>{tc.severity}</Badge></TableCell>
                      <TableCell className="max-w-xs truncate">{tc.input.slice(0, 100)}...</TableCell>
                      <TableCell className="font-mono text-sm max-w-xs truncate">
                        {String((tc.expected_behavior as Record<string, unknown>)?.type) || "N/A"}
                      </TableCell>
                      <TableCell>v{tc.version}</TableCell>
                      <TableCell>
                        <Badge variant={tc.is_active ? "default" : "secondary"}>
                          {tc.is_active ? "Active" : "Inactive"}
                        </Badge>
                      </TableCell>
                      <TableCell>
                        <div className="flex items-center gap-1">
                          <Button variant="ghost" size="icon" onClick={() => setEditingCase(tc)}>
                            <Edit className="h-4 w-4" />
                          </Button>
                          <Button variant="ghost" size="icon" onClick={() => handleDeleteCase(tc.id)}>
                            <Trash2 className="h-4 w-4 text-destructive" />
                          </Button>
                        </div>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          )}
        </CardContent>
      </Card>

      {editingCase && (
        <Dialog open={true} onOpenChange={(open) => !open && setEditingCase(null)}>
          <DialogContent className="max-w-2xl">
            <DialogHeader>
              <DialogTitle>Edit Test Case: {editingCase.test_case_id}</DialogTitle>
            </DialogHeader>
            <div className="space-y-4 py-4">
              <div className="grid gap-4 md:grid-cols-2">
                <div>
                  <Label htmlFor="edit_test_case_id">Test Case ID</Label>
                  <Input
                    id="edit_test_case_id"
                    value={editingCase.test_case_id}
                    onChange={(e) => setEditingCase({...editingCase, test_case_id: e.target.value})}
                  />
                </div>
                <div>
                  <Label htmlFor="edit_category">Category</Label>
                  <Select value={editingCase.category} onValueChange={(v) => setEditingCase({...editingCase!, category: v})}>
                    <SelectTrigger><SelectValue placeholder="Select category" /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="smoke">Smoke</SelectItem>
                      <SelectItem value="safety">Safety</SelectItem>
                      <SelectItem value="jailbreak">Jailbreak</SelectItem>
                      <SelectItem value="prompt_injection">Prompt Injection</SelectItem>
                      <SelectItem value="pii">PII</SelectItem>
                      <SelectItem value="policy">Policy</SelectItem>
                      <SelectItem value="refusal">Refusal</SelectItem>
                      <SelectItem value="tool_use">Tool Use</SelectItem>
                      <SelectItem value="hallucination">Hallucination</SelectItem>
                      <SelectItem value="bias">Bias</SelectItem>
                      <SelectItem value="adversarial">Adversarial</SelectItem>
                      <SelectItem value="custom">Custom</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div>
                  <Label htmlFor="edit_severity">Severity</Label>
                  <Select value={editingCase.severity} onValueChange={(v) => setEditingCase({...editingCase!, severity: v})}>
                    <SelectTrigger><SelectValue placeholder="Select severity" /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="critical">Critical</SelectItem>
                      <SelectItem value="high">High</SelectItem>
                      <SelectItem value="medium">Medium</SelectItem>
                      <SelectItem value="low">Low</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div>
                  <Label htmlFor="edit_version">Version</Label>
                  <Input
                    id="edit_version"
                    type="number"
                    value={editingCase.version}
                    onChange={(e) => setEditingCase({...editingCase!, version: parseInt(e.target.value)})}
                  />
                </div>
              </div>
              <div>
                <Label htmlFor="edit_input">Input</Label>
                <Textarea
                  id="edit_input"
                  value={editingCase.input}
                  onChange={(e) => setEditingCase({...editingCase!, input: e.target.value})}
                  rows={3}
                />
              </div>
              <div>
                <Label>Expected Behavior Matcher Config (JSON)</Label>
                <Textarea
                  value={JSON.stringify(editingCase.expected_behavior, null, 2)}
                  onChange={(e) => {
                    try {
                      setEditingCase({...editingCase!, expected_behavior: JSON.parse(e.target.value)});
                    } catch {}
                  }}
                  rows={4}
                  className="font-mono text-sm"
                />
              </div>
            </div>
            <DialogFooter>
              <Button variant="outline" onClick={() => setEditingCase(null)}>Cancel</Button>
              <Button onClick={handleUpdateCase}>Save</Button>
            </DialogFooter          </DialogContent>
        </Dialog>
      )}
    </div>
  );

  if (isLoading || !isAuthenticated) {
    return <LoadingScreen />;
  }

  if (!suite) {
    return <SuiteNotFound router={router} />;
  }

  return <MainContent
    suite={suite}
    router={router}
    handleCreateVersion={handleCreateVersion}
    showCreateCaseDialog={showCreateCaseDialog}
    setShowCreateCaseDialog={setShowCreateCaseDialog}
    showImportDialog={showImportDialog}
    setShowImportDialog={setShowImportDialog}
    importFormat={importFormat}
    setImportFormat={setImportFormat}
    importContent={importContent}
    setImportContent={setImportContent}
    newCase={newCase}
    setNewCase={setNewCase}
    handleCreateCase={handleCreateCase}
    handleImport={handleImport}
    handleCreateVersion={handleCreateVersion}
    editingCase={editingCase}
    setEditingCase={setEditingCase}
    handleUpdateCase={handleUpdateCase}
    handleDeleteCase={handleDeleteCase}
    suiteId={suiteId}
    fetchSuite={fetchSuite}
    formatDate={formatDate}
    getSeverityColor={getSeverityColor}
    suite={suite}
    router={router}
  />;
}