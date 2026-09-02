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
import { Plus, Upload, Search, FileText, Eye, Edit, Trash2, Download, AlertTriangle } from "lucide-react";

interface TestCase {
  id: string;
  test_case_id: string;
  category: string;
  severity: string;
  input: string;
  expected_behavior: Record<string, unknown>;
  metadata: Record<string, unknown>;
  is_active: boolean;
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

interface SuiteStats {
  total: number;
  by_category: Record<string, number>;
  by_severity: Record<string, number>;
}

export default function SuitesPage() {
  const { isAuthenticated, isLoading } = useAuth();
  const [suites, setSuites] = useState<TestSuite[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedCategory, setSelectedCategory] = useState("");
  const [showCreateDialog, setShowCreateDialog] = useState(false);
  const [showImportDialog, setShowImportDialog] = useState(false);
  const [importFormat, setImportFormat] = useState<"yaml" | "json">("yaml");
  const [importContent, setImportContent] = useState("");
  const [newSuiteName, setNewSuiteName] = useState("");
  const [newSuiteDescription, setNewSuiteDescription] = useState("");

  const fetchSuites = useCallback(async () => {
    try {
      const res = await api.get("/suites");
      setSuites(res.data);
    } catch (error) {
      console.error("Failed to fetch suites:", error);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (!isLoading) {
      if (!isAuthenticated) {
        window.location.href = "/login";
      } else {
        fetchSuites();
      }
    }
  }, [isAuthenticated, isLoading, fetchSuites]);

  const handleCreateSuite = async () => {
    if (!newSuiteName.trim()) return;
    try {
      await api.post("/suites", {
        name: newSuiteName,
        description: newSuiteDescription,
        test_cases: [],
      });
      setShowCreateDialog(false);
      setNewSuiteName("");
      setNewSuiteDescription("");
      fetchSuites();
    } catch (error) {
      console.error("Failed to create suite:", error);
    }
  };

  const handleImport = async () => {
    if (!importContent.trim()) return;
    try {
      const endpoint = importFormat === "yaml" ? "/suites/import/yaml" : "/suites/import/json";
      await api.post(endpoint, importContent, {
        headers: { "Content-Type": importFormat === "yaml" ? "text/yaml" : "application/json" },
      });
      setShowImportDialog(false);
      setImportContent("");
      fetchSuites();
    } catch (error) {
      console.error("Failed to import suite:", error);
    }
  };

  const handleDeleteSuite = async (suiteId: string) => {
    if (!confirm("Are you sure you want to delete this suite?")) return;
    try {
      await api.delete(`/suites/${suiteId}`);
      fetchSuites();
    } catch (error) {
      console.error("Failed to delete suite:", error);
    }
  };

  const filteredSuites = suites.filter((suite) => {
    const matchesSearch = suite.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      suite.description?.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesCategory = !selectedCategory || suite.test_cases.some(tc => tc.category === selectedCategory);
    return matchesSearch && matchesCategory;
  });

  const categories = Array.from(new Set(suites.flatMap(s => s.test_cases.map(tc => tc.category))));

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
          <h1 className="text-3xl font-bold">Test Suites</h1>
          <p className="text-muted-foreground">Manage test suites and test cases</p>
        </div>
        <div className="flex gap-2">
          <Dialog open={showCreateDialog} onOpenChange={setShowCreateDialog}>
            <DialogTrigger asChild>
              <Button><Plus className="mr-2 h-4 w-4" /> New Suite</Button>
            </DialogTrigger>
            <DialogContent>
              <DialogHeader>
                <DialogTitle>Create Test Suite</DialogTitle>
              </DialogHeader>
              <div className="space-y-4 py-4">
                <div>
                  <Label htmlFor="name">Name</Label>
                  <Input
                    id="name"
                    value={newSuiteName}
                    onChange={(e) => setNewSuiteName(e.target.value)}
                    placeholder="Enter suite name"
                  />
                </div>
                <div>
                  <Label htmlFor="description">Description</Label>
                  <Textarea
                    id="description"
                    value={newSuiteDescription}
                    onChange={(e) => setNewSuiteDescription(e.target.value)}
                    placeholder="Enter description"
                  />
                </div>
              </div>
              <DialogFooter>
                <Button variant="outline" onClick={() => setShowCreateDialog(false)}>Cancel</Button>
                <Button onClick={handleCreateSuite}>Create</Button>
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
          <CardTitle>Search & Filter</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col sm:flex-row gap-4">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <Input
              placeholder="Search suites..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-10"
            />
          </div>
          <Select value={selectedCategory} onValueChange={setSelectedCategory}>
            <SelectTrigger className="w-48"><SelectValue placeholder="All categories" /></SelectTrigger>
            <SelectContent>
              <SelectItem value="">All categories</SelectItem>
              {categories.map((cat) => (
                <SelectItem key={cat} value={cat}>{cat}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        </CardContent>
      </Card>

      {loading ? (
        <Card>
          <CardContent className="text-center py-12">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary mx-auto"></div>
            <p className="mt-4 text-muted-foreground">Loading suites...</p>
          </CardContent>
        </Card>
      ) : filteredSuites.length === 0 ? (
        <Card>
          <CardContent className="text-center py-12">
            <FileText className="h-12 w-12 text-muted-foreground mx-auto" />
            <h3 className="mt-4 text-lg font-medium">No suites found</h3>
            <p className="text-muted-foreground">Create your first test suite or import one.</p>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-4">
          {filteredSuites.map((suite) => (
            <Card key={suite.id} className="overflow-hidden">
              <CardHeader className="pb-2">
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center gap-2">
                      <CardTitle>{suite.name}</CardTitle>
                      <Badge variant="secondary">v{suite.version}</Badge>
                      {suite.is_active && <Badge variant="default">Active</Badge>}
                    </div>
                    {suite.description && (
                      <p className="text-sm text-muted-foreground mt-1">{suite.description}</p>
                    )}
                  </div>
                  <div className="flex gap-2">
                    <Button variant="ghost" size="icon" asChild>
                      <a href={`/suites/${suite.id}`}><Eye className="h-4 w-4" /></a>
                    </Button>
                    <Button variant="ghost" size="icon" onClick={() => handleDeleteSuite(suite.id)}>
                      <Trash2 className="h-4 w-4 text-destructive" />
                    </Button>
                  </div>
                </div>
              </CardHeader>
              <CardContent>
                <Tabs defaultValue="overview" className="w-full">
                  <TabsList>
                    <TabsTrigger value="overview">Overview ({suite.test_cases.length} cases)</TabsTrigger>
                    <TabsTrigger value="cases">Test Cases</TabsTrigger>
                  </TabsList>

                  <TabsContent value="overview">
                    <div className="grid gap-4 md:grid-cols-3 mt-4">
                      <div className="p-4 bg-muted rounded-lg">
                        <p className="text-sm text-muted-foreground">Total Test Cases</p>
                        <p className="text-2xl font-bold">{suite.test_cases.length}</p>
                      </div>
                      <div className="p-4 bg-muted rounded-lg">
                        <p className="text-sm text-muted-foreground">Categories</p>
                        <p className="text-2xl font-bold">
                          {new Set(suite.test_cases.map(tc => tc.category)).size}
                        </p>
                      </div>
                      <div className="p-4 bg-muted rounded-lg">
                        <p className="text-sm text-muted-foreground">Schema Version</p>
                        <p className="text-2xl font-bold">{suite.schema_version}</p>
                      </div>
                    </div>

                    <div className="mt-4">
                      <h4 className="font-medium mb-2">By Category</h4>
                      <div className="flex flex-wrap gap-2">
                        {Object.entries(
                          suite.test_cases.reduce((acc, tc) => {
                            acc[tc.category] = (acc[tc.category] || 0) + 1;
                            return acc;
                          }, {} as Record<string, number>)
                        ).map(([cat, count]) => (
                          <Badge key={cat} variant="secondary">{cat}: {count}</Badge>
                        ))}
                      </div>
                    </div>

                    <div className="mt-4">
                      <h4 className="font-medium mb-2">By Severity</h4>
                      <div className="flex flex-wrap gap-2">
                        {Object.entries(
                          suite.test_cases.reduce((acc, tc) => {
                            acc[tc.severity] = (acc[tc.severity] || 0) + 1;
                            return acc;
                          }, {} as Record<string, number>)
                        ).map(([sev, count]) => (
                          <Badge key={sev} className={getSeverityColor(sev)}>{sev}: {count}</Badge>
                        ))}
                      </div>
                    </div>
                  </TabsContent>

                  <TabsContent value="cases">
                    <div className="overflow-x-auto mt-4">
                      <Table>
                        <TableHeader>
                          <TableRow>
                            <TableHead>Test Case ID</TableHead>
                            <TableHead>Category</TableHead>
                            <TableHead>Severity</TableHead>
                            <TableHead>Input Preview</TableHead>
                            <TableHead>Expected Behavior</TableHead>
                            <TableHead>Status</TableHead>
                          </TableRow>
                        </TableHeader>
                        <TableBody>
                          {suite.test_cases.map((tc) => (
                            <TableRow key={tc.id}>
                              <TableCell className="font-mono text-sm">{tc.test_case_id}</TableCell>
                              <TableCell><Badge variant="secondary">{tc.category}</Badge></TableCell>
                              <TableCell><Badge className={getSeverityColor(tc.severity)}>{tc.severity}</Badge></TableCell>
                              <TableCell className="max-w-xs truncate">{tc.input.slice(0, 80)}...</TableCell>
<TableCell className="font-mono text-sm">
                                 {String((tc.expected_behavior as Record<string, unknown>)?.type) || "N/A"}
                               </TableCell>
                              <TableCell>
                                <Badge variant={tc.is_active ? "default" : "secondary"}>
                                  {tc.is_active ? "Active" : "Inactive"}
                                </Badge>
                              </TableCell>
                            </TableRow>
                          ))}
                        </TableBody>
                      </Table>
                    </div>
                  </TabsContent>
                </Tabs>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}