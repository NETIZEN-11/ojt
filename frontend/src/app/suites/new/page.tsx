"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { DashboardLayout } from "@/components/ui/dashboard-layout";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger, DialogFooter } from "@/components/ui/dialog";
import { api } from "@/lib/api";
import { ArrowLeft, Plus, Trash2, Upload, FileText, AlertCircle } from "lucide-react";

interface TestCase {
  id: string;
  test_case_id: string;
  category: string;
  severity: string;
  input: string;
  expected_behavior_type: string;
  expected_behavior_matcher: Record<string, unknown>;
  metadata: Record<string, unknown>;
}

const CATEGORIES = [
  "jailbreak",
  "prompt_injection",
  "harmful_content",
  "pii_leak",
  "bias",
  "hallucination",
  "security",
  "compliance",
  "toxicity",
  "misinformation",
  "other"
];

const SEVERITIES = [
  "critical",
  "high",
  "medium",
  "low"
];

const BEHAVIOR_TYPES = [
  "exact_match",
  "regex_match",
  "keyword_match",
  "refusal_match",
  "llm_judge"
];

export default function NewSuitePage() {
  const router = useRouter();
  const [loading, setLoading] = useState(false);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [testCases, setTestCases] = useState<TestCase[]>([]);
  const [showAddCase, setShowAddCase] = useState(false);
  const [showImport, setShowImport] = useState(false);
  const [importFormat, setImportFormat] = useState<"yaml" | "json">("yaml");
  const [importFile, setImportFile] = useState<File | null>(null);

  // New test case form state
  const [newCase, setNewCase] = useState<Partial<TestCase>>({
    test_case_id: "",
    category: "other",
    severity: "medium",
    input: "",
    expected_behavior_type: "refusal_match",
    expected_behavior_matcher: {},
    metadata: {}
  });

  const handleAddTestCase = () => {
    if (!newCase.test_case_id || !newCase.input) {
      alert("Please fill in test case ID and input");
      return;
    }

    const testCase: TestCase = {
      id: `temp-${Date.now()}`,
      test_case_id: newCase.test_case_id!,
      category: newCase.category!,
      severity: newCase.severity!,
      input: newCase.input!,
      expected_behavior_type: newCase.expected_behavior_type!,
      expected_behavior_matcher: newCase.expected_behavior_matcher!,
      metadata: newCase.metadata!
    };

    setTestCases([...testCases, testCase]);
    setShowAddCase(false);
    setNewCase({
      test_case_id: "",
      category: "other",
      severity: "medium",
      input: "",
      expected_behavior_type: "refusal_match",
      expected_behavior_matcher: {},
      metadata: {}
    });
  };

  const handleRemoveTestCase = (id: string) => {
    setTestCases(testCases.filter(tc => tc.id !== id));
  };

  const handleImportFile = async () => {
    if (!importFile) return;

    try {
      const formData = new FormData();
      formData.append("file", importFile);

      const endpoint = importFormat === "yaml" ? "/suites/import/yaml" : "/suites/import/json";
      const response = await api.post(endpoint, formData, {
        headers: { "Content-Type": "multipart/form-data" }
      });

      router.push(`/suites/${response.data.id}`);
    } catch (error) {
      console.error("Failed to import suite:", error);
      alert("Failed to import suite. Please check the file format.");
    }
  };

  const handleCreateSuite = async () => {
    if (!name.trim()) {
      alert("Please enter a suite name");
      return;
    }

    setLoading(true);
    try {
      const payload = {
        name,
        description: description || undefined,
        test_cases: testCases.map(tc => ({
          test_case_id: tc.test_case_id,
          category: tc.category,
          severity: tc.severity,
          input: tc.input,
          expected_behavior_type: tc.expected_behavior_type,
          expected_behavior_matcher: tc.expected_behavior_matcher,
          metadata: tc.metadata
        }))
      };

      const response = await api.post("/suites", payload);
      router.push(`/suites/${response.data.id}`);
    } catch (error) {
      console.error("Failed to create suite:", error);
      alert("Failed to create suite. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <DashboardLayout>
      <div className="space-y-6">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="icon" onClick={() => router.push("/suites")}>
            <ArrowLeft className="h-4 w-4" />
          </Button>
          <div>
            <h1 className="text-3xl font-bold">Create Test Suite</h1>
            <p className="text-muted-foreground">Define a new test suite with test cases</p>
          </div>
        </div>

        <div className="grid gap-6 lg:grid-cols-3">
          <div className="lg:col-span-2 space-y-6">
            <Card>
              <CardHeader>
                <CardTitle>Suite Details</CardTitle>
                <CardDescription>Basic information about the test suite</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div>
                  <Label htmlFor="name">Name *</Label>
                  <Input
                    id="name"
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    placeholder="e.g., Safety Evaluation Suite v1"
                  />
                </div>
                <div>
                  <Label htmlFor="description">Description</Label>
                  <Textarea
                    id="description"
                    value={description}
                    onChange={(e) => setDescription(e.target.value)}
                    placeholder="Describe the purpose and scope of this test suite..."
                    rows={4}
                  />
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <div className="flex items-center justify-between">
                  <div>
                    <CardTitle>Test Cases</CardTitle>
                    <CardDescription>Add individual test cases to this suite</CardDescription>
                  </div>
                  <Dialog open={showAddCase} onOpenChange={setShowAddCase}>
                    <DialogTrigger asChild>
                      <Button size="sm">
                        <Plus className="mr-2 h-4 w-4" />
                        Add Test Case
                      </Button>
                    </DialogTrigger>
                    <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
                      <DialogHeader>
                        <DialogTitle>Add Test Case</DialogTitle>
                      </DialogHeader>
                      <div className="space-y-4 py-4">
                        <div>
                          <Label htmlFor="test_case_id">Test Case ID *</Label>
                          <Input
                            id="test_case_id"
                            value={newCase.test_case_id}
                            onChange={(e) => setNewCase({ ...newCase, test_case_id: e.target.value })}
                            placeholder="e.g., jb-001"
                          />
                        </div>
                        
                        <div className="grid grid-cols-2 gap-4">
                          <div>
                            <Label htmlFor="category">Category *</Label>
                            <Select
                              value={newCase.category}
                              onValueChange={(v) => setNewCase({ ...newCase, category: v })}
                            >
                              <SelectTrigger>
                                <SelectValue placeholder="Select category" />
                              </SelectTrigger>
                              <SelectContent>
                                {CATEGORIES.map((cat) => (
                                  <SelectItem key={cat} value={cat}>
                                    {cat.replace(/_/g, " ").replace(/\b\w/g, l => l.toUpperCase())}
                                  </SelectItem>
                                ))}
                              </SelectContent>
                            </Select>
                          </div>

                          <div>
                            <Label htmlFor="severity">Severity *</Label>
                            <Select
                              value={newCase.severity}
                              onValueChange={(v) => setNewCase({ ...newCase, severity: v })}
                            >
                              <SelectTrigger>
                                <SelectValue placeholder="Select severity" />
                              </SelectTrigger>
                              <SelectContent>
                                {SEVERITIES.map((sev) => (
                                  <SelectItem key={sev} value={sev}>
                                    {sev.charAt(0).toUpperCase() + sev.slice(1)}
                                  </SelectItem>
                                ))}
                              </SelectContent>
                            </Select>
                          </div>
                        </div>

                        <div>
                          <Label htmlFor="input">Input / Prompt *</Label>
                          <Textarea
                            id="input"
                            value={newCase.input}
                            onChange={(e) => setNewCase({ ...newCase, input: e.target.value })}
                            placeholder="Enter the test input or prompt..."
                            rows={6}
                          />
                        </div>

                        <div>
                          <Label htmlFor="behavior_type">Expected Behavior Type *</Label>
                          <Select
                            value={newCase.expected_behavior_type}
                            onValueChange={(v) => setNewCase({ ...newCase, expected_behavior_type: v })}
                          >
                            <SelectTrigger>
                              <SelectValue placeholder="Select behavior type" />
                            </SelectTrigger>
                            <SelectContent>
                              {BEHAVIOR_TYPES.map((type) => (
                                <SelectItem key={type} value={type}>
                                  {type.replace(/_/g, " ").replace(/\b\w/g, l => l.toUpperCase())}
                                </SelectItem>
                              ))}
                            </SelectContent>
                          </Select>
                          <p className="text-xs text-muted-foreground mt-1">
                            Determines how the agent response will be evaluated
                          </p>
                        </div>

                        {newCase.expected_behavior_type === "exact_match" && (
                          <div>
                            <Label htmlFor="expected_text">Expected Text</Label>
                            <Input
                              id="expected_text"
                              placeholder="Exact text to match"
                              onChange={(e) => setNewCase({
                                ...newCase,
                                expected_behavior_matcher: { expected_text: e.target.value }
                              })}
                            />
                          </div>
                        )}

                        {newCase.expected_behavior_type === "regex_match" && (
                          <div>
                            <Label htmlFor="pattern">Regex Pattern</Label>
                            <Input
                              id="pattern"
                              placeholder="e.g., ^(I cannot|I apologize)"
                              onChange={(e) => setNewCase({
                                ...newCase,
                                expected_behavior_matcher: { pattern: e.target.value }
                              })}
                            />
                          </div>
                        )}

                        {newCase.expected_behavior_type === "keyword_match" && (
                          <div>
                            <Label htmlFor="keywords">Keywords (comma-separated)</Label>
                            <Input
                              id="keywords"
                              placeholder="e.g., refuse, cannot, inappropriate"
                              onChange={(e) => setNewCase({
                                ...newCase,
                                expected_behavior_matcher: { keywords: e.target.value.split(",").map(k => k.trim()) }
                              })}
                            />
                          </div>
                        )}
                      </div>
                      <DialogFooter>
                        <Button variant="outline" onClick={() => setShowAddCase(false)}>Cancel</Button>
                        <Button onClick={handleAddTestCase}>Add Test Case</Button>
                      </DialogFooter>
                    </DialogContent>
                  </Dialog>
                </div>
              </CardHeader>
              <CardContent>
                {testCases.length === 0 ? (
                  <div className="text-center py-12 border-2 border-dashed rounded-lg">
                    <FileText className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
                    <h3 className="text-lg font-medium mb-2">No test cases yet</h3>
                    <p className="text-sm text-muted-foreground mb-4">
                      Add test cases manually or import from a file
                    </p>
                    <Button variant="outline" onClick={() => setShowAddCase(true)}>
                      <Plus className="mr-2 h-4 w-4" />
                      Add First Test Case
                    </Button>
                  </div>
                ) : (
                  <div className="overflow-x-auto">
                    <Table>
                      <TableHeader>
                        <TableRow>
                          <TableHead>ID</TableHead>
                          <TableHead>Category</TableHead>
                          <TableHead>Severity</TableHead>
                          <TableHead>Input Preview</TableHead>
                          <TableHead>Behavior</TableHead>
                          <TableHead className="w-[50px]"></TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {testCases.map((tc) => (
                          <TableRow key={tc.id}>
                            <TableCell className="font-mono text-sm">{tc.test_case_id}</TableCell>
                            <TableCell>
                              <Badge variant="secondary">{tc.category}</Badge>
                            </TableCell>
                            <TableCell>
                              <Badge
                                className={
                                  tc.severity === "critical" ? "bg-red-600" :
                                  tc.severity === "high" ? "bg-orange-600" :
                                  tc.severity === "medium" ? "bg-yellow-600" :
                                  "bg-blue-600"
                                }
                              >
                                {tc.severity}
                              </Badge>
                            </TableCell>
                            <TableCell className="max-w-xs truncate text-sm">
                              {tc.input.slice(0, 60)}...
                            </TableCell>
                            <TableCell className="text-sm">
                              {tc.expected_behavior_type.replace(/_/g, " ")}
                            </TableCell>
                            <TableCell>
                              <Button
                                variant="ghost"
                                size="icon"
                                onClick={() => handleRemoveTestCase(tc.id)}
                              >
                                <Trash2 className="h-4 w-4 text-destructive" />
                              </Button>
                            </TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </div>
                )}
              </CardContent>
            </Card>
          </div>

          <div className="space-y-6">
            <Card>
              <CardHeader>
                <CardTitle>Quick Import</CardTitle>
                <CardDescription>Import test cases from a file</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div>
                  <Label htmlFor="format">Format</Label>
                  <Select value={importFormat} onValueChange={(v) => setImportFormat(v as "yaml" | "json")}>
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="yaml">YAML</SelectItem>
                      <SelectItem value="json">JSON</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div>
                  <Label htmlFor="file">File</Label>
                  <Input
                    id="file"
                    type="file"
                    accept={importFormat === "yaml" ? ".yaml,.yml" : ".json"}
                    onChange={(e) => setImportFile(e.target.files?.[0] || null)}
                  />
                </div>
                <Button
                  className="w-full"
                  variant="outline"
                  onClick={handleImportFile}
                  disabled={!importFile}
                >
                  <Upload className="mr-2 h-4 w-4" />
                  Import File
                </Button>
                <p className="text-xs text-muted-foreground">
                  Importing will create the suite directly and redirect you to the suite page
                </p>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Summary</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <div className="flex justify-between">
                  <span className="text-sm text-muted-foreground">Total Test Cases</span>
                  <span className="font-medium">{testCases.length}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-sm text-muted-foreground">Categories</span>
                  <span className="font-medium">
                    {new Set(testCases.map(tc => tc.category)).size}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-sm text-muted-foreground">Critical</span>
                  <span className="font-medium text-red-600">
                    {testCases.filter(tc => tc.severity === "critical").length}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-sm text-muted-foreground">High</span>
                  <span className="font-medium text-orange-600">
                    {testCases.filter(tc => tc.severity === "high").length}
                  </span>
                </div>
              </CardContent>
            </Card>

            <Card className="border-amber-200 bg-amber-50 dark:bg-amber-950/20">
              <CardHeader>
                <div className="flex items-start gap-2">
                  <AlertCircle className="h-5 w-5 text-amber-600 mt-0.5" />
                  <div>
                    <CardTitle className="text-amber-900 dark:text-amber-100">Note</CardTitle>
                    <CardDescription className="text-amber-700 dark:text-amber-200">
                      You can add more test cases after creating the suite
                    </CardDescription>
                  </div>
                </div>
              </CardHeader>
            </Card>

            <div className="space-y-2">
              <Button
                className="w-full"
                onClick={handleCreateSuite}
                disabled={loading || !name.trim()}
              >
                {loading ? "Creating..." : "Create Suite"}
              </Button>
              <Button
                className="w-full"
                variant="outline"
                onClick={() => router.push("/suites")}
                disabled={loading}
              >
                Cancel
              </Button>
            </div>
          </div>
        </div>
      </div>
    </DashboardLayout>
  );
}
