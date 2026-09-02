"use client";

import { useEffect, useState, useCallback } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger, DialogFooter } from "@/components/ui/dialog";
import { Textarea } from "@/components/ui/textarea";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { api } from "@/lib/api";
import { formatDate, getSeverityColor } from "@/lib/utils";
import { useAuth } from "@/lib/auth";
import { Plus, Edit, Trash2, Eye, CheckCircle, XCircle, Wifi, WifiOff } from "lucide-react";

interface TargetAgent {
  id: string;
  name: string;
  description: string | null;
  endpoint_url: string;
  auth_config: Record<string, unknown>;
  request_template: Record<string, unknown> | null;
  response_extraction: Record<string, unknown> | null;
  timeout_seconds: number;
  max_retries: number;
  allowed: boolean;
  status: string;
  created_at: string;
  updated_at: string;
  created_by: string | null;
}

export default function AgentsPage() {
  const { isAuthenticated, isLoading } = useAuth();
  const [agents, setAgents] = useState<TargetAgent[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState("");
  const [showCreateDialog, setShowCreateDialog] = useState(false);
  const [editingAgent, setEditingAgent] = useState<TargetAgent | null>(null);
  const [testingAgent, setTestingAgent] = useState<TargetAgent | null>(null);
  const [testInput, setTestInput] = useState("");
  const [testResult, setTestResult] = useState<string | null>(null);
  const [testLoading, setTestLoading] = useState(false);
  const [newAgent, setNewAgent] = useState({
    name: "",
    description: "",
    endpoint_url: "",
    auth_config: {} as Record<string, unknown>,
    request_template: { input: "{input}" },
    response_extraction: { response: "response" },
    timeout_seconds: 30,
    max_retries: 3,
    allowed: true,
  });

  const fetchAgents = useCallback(async () => {
    try {
      const res = await api.get("/agents");
      setAgents(res.data);
    } catch (error) {
      console.error("Failed to fetch agents:", error);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (!isLoading) {
      if (!isAuthenticated) {
        window.location.href = "/login";
      } else {
        fetchAgents();
      }
    }
  }, [isAuthenticated, isLoading, fetchAgents]);

  const handleCreateAgent = async () => {
    if (!newAgent.name || !newAgent.endpoint_url) return;
    try {
      await api.post("/agents", newAgent);
      setShowCreateDialog(false);
      setNewAgent({
        name: "",
        description: "",
        endpoint_url: "",
        auth_config: {},
        request_template: { input: "{input}" },
        response_extraction: { response: "response" },
        timeout_seconds: 30,
        max_retries: 3,
        allowed: true,
      });
      fetchAgents();
    } catch (error) {
      console.error("Failed to create agent:", error);
    }
  };

  const handleUpdateAgent = async () => {
    if (!editingAgent) return;
    try {
      await api.put(`/agents/${editingAgent.id}`, editingAgent);
      setEditingAgent(null);
      fetchAgents();
    } catch (error) {
      console.error("Failed to update agent:", error);
    }
  };

  const handleDeleteAgent = async (agentId: string) => {
    if (!confirm("Are you sure you want to delete this agent?")) return;
    try {
      await api.delete(`/agents/${agentId}`);
      fetchAgents();
    } catch (error) {
      console.error("Failed to delete agent:", error);
    }
  };

  const handleTestAgent = async (agent: TargetAgent) => {
    setTestingAgent(agent);
    setTestInput("Hello, how are you?");
    setTestResult(null);
  };

  const handleRunTest = async () => {
    if (!testingAgent || !testInput.trim()) return;
    setTestLoading(true);
    setTestResult(null);
    try {
      const res = await api.post(`/agents/${testingAgent.id}/test`, { input: testInput });
      setTestResult(JSON.stringify(res.data, null, 2));
    } catch (error: unknown) {
      const err = error as { response?: { data?: { message?: string } } };
      setTestResult(`Error: ${err.response?.data?.message || "Unknown error"}`);
    } finally {
      setTestLoading(false);
    }
  };

  const filteredAgents = agents.filter((agent) =>
    agent.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    agent.description?.toLowerCase().includes(searchQuery.toLowerCase()) ||
    agent.endpoint_url.toLowerCase().includes(searchQuery.toLowerCase())
  );

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
          <h1 className="text-3xl font-bold">Target Agents</h1>
          <p className="text-muted-foreground">Manage target agents for evaluation</p>
        </div>
        <Dialog open={showCreateDialog} onOpenChange={setShowCreateDialog}>
          <DialogTrigger asChild>
            <Button><Plus className="mr-2 h-4 w-4" /> New Agent</Button>
          </DialogTrigger>
          <DialogContent className="max-w-2xl">
            <DialogHeader>
              <DialogTitle>Create Target Agent</DialogTitle>
            </DialogHeader>
            <div className="space-y-4 py-4">
              <div className="grid gap-4 md:grid-cols-2">
                <div>
                  <Label htmlFor="name">Name</Label>
                  <Input
                    id="name"
                    value={newAgent.name}
                    onChange={(e) => setNewAgent({...newAgent, name: e.target.value})}
                    placeholder="Agent name"
                  />
                </div>
                <div>
                  <Label htmlFor="endpoint_url">Endpoint URL</Label>
                  <Input
                    id="endpoint_url"
                    value={newAgent.endpoint_url}
                    onChange={(e) => setNewAgent({...newAgent, endpoint_url: e.target.value})}
                    placeholder="https://api.example.com/v1/chat"
                  />
                </div>
                <div>
                  <Label htmlFor="timeout_seconds">Timeout (seconds)</Label>
                  <Input
                    id="timeout_seconds"
                    type="number"
                    value={newAgent.timeout_seconds}
                    onChange={(e) => setNewAgent({...newAgent, timeout_seconds: parseInt(e.target.value)})}
                  />
                </div>
                <div>
                  <Label htmlFor="max_retries">Max Retries</Label>
                  <Input
                    id="max_retries"
                    type="number"
                    value={newAgent.max_retries}
                    onChange={(e) => setNewAgent({...newAgent, max_retries: parseInt(e.target.value)})}
                  />
                </div>
              </div>
              <div>
                <Label htmlFor="description">Description</Label>
                <Textarea
                  id="description"
                  value={newAgent.description}
                  onChange={(e) => setNewAgent({...newAgent, description: e.target.value})}
                  placeholder="Agent description"
                  rows={2}
                />
              </div>
              <div>
                <Label htmlFor="request_template">Request Template (JSON)</Label>
                <Textarea
                  id="request_template"
                  value={JSON.stringify(newAgent.request_template, null, 2)}
                  onChange={(e) => {
                    try {
                      setNewAgent({...newAgent, request_template: JSON.parse(e.target.value)});
                    } catch {}
                  }}
                  rows={4}
                  className="font-mono text-sm"
                />
              </div>
              <div>
                <Label htmlFor="response_extraction">Response Extraction (JSON)</Label>
                <Textarea
                  id="response_extraction"
                  value={JSON.stringify(newAgent.response_extraction, null, 2)}
                  onChange={(e) => {
                    try {
                      setNewAgent({...newAgent, response_extraction: JSON.parse(e.target.value)});
                    } catch {}
                  }}
                  rows={3}
                  className="font-mono text-sm"
                />
              </div>
              <div>
                <Label htmlFor="auth_config">Auth Config (JSON)</Label>
                <Textarea
                  id="auth_config"
                  value={JSON.stringify(newAgent.auth_config, null, 2)}
                  onChange={(e) => {
                    try {
                      setNewAgent({...newAgent, auth_config: JSON.parse(e.target.value)});
                    } catch {}
                  }}
                  rows={3}
                  className="font-mono text-sm"
                />
              </div>
              <div className="flex items-center gap-2">
                <Input type="checkbox" id="allowed" checked={newAgent.allowed} onChange={(e) => setNewAgent({...newAgent, allowed: e.target.checked})} />
                <Label htmlFor="allowed">Allowed</Label>
              </div>
            </div>
            <DialogFooter>
              <Button variant="outline" onClick={() => setShowCreateDialog(false)}>Cancel</Button>
              <Button onClick={handleCreateAgent}>Create</Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Search</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="relative max-w-md">
            <Wifi className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <Input
              placeholder="Search agents..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-10"
            />
          </div>
        </CardContent>
      </Card>

      {loading ? (
        <Card>
          <CardContent className="text-center py-12">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary mx-auto"></div>
            <p className="mt-4 text-muted-foreground">Loading agents...</p>
          </CardContent>
        </Card>
      ) : filteredAgents.length === 0 ? (
        <Card>
          <CardContent className="text-center py-12">
            <WifiOff className="h-12 w-12 text-muted-foreground mx-auto" />
            <h3 className="mt-4 text-lg font-medium">No agents found</h3>
            <p className="text-muted-foreground">Create your first target agent.</p>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-4">
          {filteredAgents.map((agent) => (
            <Card key={agent.id} className="overflow-hidden">
              <CardHeader className="pb-2">
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center gap-2">
                      <CardTitle>{agent.name}</CardTitle>
                      <Badge variant={agent.allowed ? "default" : "secondary"}>
                        {agent.allowed ? "Allowed" : "Blocked"}
                      </Badge>
                      <Badge variant={agent.status === "active" ? "default" : agent.status === "testing" ? "secondary" : "destructive"}>
                        {agent.status}
                      </Badge>
                    </div>
                    {agent.description && (
                      <p className="text-sm text-muted-foreground mt-1">{agent.description}</p>
                    )}
                    <p className="text-sm font-mono text-muted-foreground mt-1">{agent.endpoint_url}</p>
                  </div>
                  <div className="flex gap-2">
                    <Button variant="ghost" size="icon" onClick={() => handleTestAgent(agent)}>
                      <Wifi className="h-4 w-4" />
                    </Button>
                    <Button variant="ghost" size="icon" onClick={() => setEditingAgent(agent)}>
                      <Edit className="h-4 w-4" />
                    </Button>
                    <Button variant="ghost" size="icon" onClick={() => handleDeleteAgent(agent.id)}>
                      <Trash2 className="h-4 w-4 text-destructive" />
                    </Button>
                  </div>
                </div>
              </CardHeader>
              <CardContent>
                <Tabs defaultValue="config" className="w-full">
                  <TabsList>
                    <TabsTrigger value="config">Configuration</TabsTrigger>
                    <TabsTrigger value="test">Test Connection</TabsTrigger>
                  </TabsList>

                  <TabsContent value="config">
                    <div className="grid gap-4 md:grid-cols-2 mt-4">
                      <div>
                        <h4 className="font-medium mb-2">Request Template</h4>
                        <pre className="bg-muted p-4 rounded text-sm font-mono overflow-auto max-h-64">
                          {JSON.stringify(agent.request_template, null, 2)}
                        </pre>
                      </div>
                      <div>
                        <h4 className="font-medium mb-2">Response Extraction</h4>
                        <pre className="bg-muted p-4 rounded text-sm font-mono overflow-auto max-h-64">
                          {JSON.stringify(agent.response_extraction, null, 2)}
                        </pre>
                      </div>
                      <div>
                        <h4 className="font-medium mb-2">Auth Config</h4>
                        <pre className="bg-muted p-4 rounded text-sm font-mono overflow-auto max-h-64">
                          {JSON.stringify(agent.auth_config, null, 2)}
                        </pre>
                      </div>
                      <div>
                        <h4 className="font-medium mb-2">Settings</h4>
                        <dl className="space-y-2 text-sm">
                          <div className="grid grid-cols-2 gap-2">
                            <dt className="text-muted-foreground">Timeout</dt>
                            <dd>{agent.timeout_seconds}s</dd>
                            <dt className="text-muted-foreground">Max Retries</dt>
                            <dd>{agent.max_retries}</dd>
                            <dt className="text-muted-foreground">Created</dt>
                            <dd>{formatDate(agent.created_at)}</dd>
                            <dt className="text-muted-foreground">Updated</dt>
                            <dd>{formatDate(agent.updated_at)}</dd>
                          </div>
                        </dl>
                      </div>
                    </div>
                  </TabsContent>

                  <TabsContent value="test">
                    <div className="space-y-4 mt-4">
                      <div>
                        <Label htmlFor="testInput">Test Input</Label>
                        <Textarea
                          id="testInput"
                          value={testInput}
                          onChange={(e) => setTestInput(e.target.value)}
                          placeholder="Enter test input..."
                          rows={3}
                        />
                      </div>
                      <Button onClick={handleRunTest} disabled={testLoading || !testingAgent}>
                        {testLoading ? "Testing..." : "Run Test"}
                      </Button>
                      {testResult && (
                        <div>
                          <h4 className="font-medium mb-2">Result</h4>
                          <pre className="bg-muted p-4 rounded text-sm font-mono overflow-auto max-h-96">
                            {testResult}
                          </pre>
                        </div>
                      )}
                    </div>
                  </TabsContent>
                </Tabs>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {editingAgent && (
        <Dialog open={true} onOpenChange={(open) => !open && setEditingAgent(null)}>
          <DialogContent className="max-w-2xl">
            <DialogHeader>
              <DialogTitle>Edit Agent: {editingAgent.name}</DialogTitle>
            </DialogHeader>
            <div className="space-y-4 py-4">
              <div className="grid gap-4 md:grid-cols-2">
                <div>
                  <Label htmlFor="edit_name">Name</Label>
                  <Input
                    id="edit_name"
                    value={editingAgent.name}
                    onChange={(e) => setEditingAgent({...editingAgent, name: e.target.value})}
                  />
                </div>
                <div>
                  <Label htmlFor="edit_endpoint">Endpoint URL</Label>
                  <Input
                    id="edit_endpoint"
                    value={editingAgent.endpoint_url}
                    onChange={(e) => setEditingAgent({...editingAgent, endpoint_url: e.target.value})}
                  />
                </div>
                <div>
                  <Label htmlFor="edit_timeout">Timeout (seconds)</Label>
                  <Input
                    id="edit_timeout"
                    type="number"
                    value={editingAgent.timeout_seconds}
                    onChange={(e) => setEditingAgent({...editingAgent, timeout_seconds: parseInt(e.target.value)})}
                  />
                </div>
                <div>
                  <Label htmlFor="edit_retries">Max Retries</Label>
                  <Input
                    id="edit_retries"
                    type="number"
                    value={editingAgent.max_retries}
                    onChange={(e) => setEditingAgent({...editingAgent, max_retries: parseInt(e.target.value)})}
                  />
                </div>
              </div>
              <div>
                <Label htmlFor="edit_description">Description</Label>
                <Textarea
                  id="edit_description"
                  value={editingAgent.description || ""}
                  onChange={(e) => setEditingAgent({...editingAgent, description: e.target.value})}
                  rows={2}
                />
              </div>
              <div>
                <Label htmlFor="edit_request_template">Request Template (JSON)</Label>
                <Textarea
                  id="edit_request_template"
                  value={JSON.stringify(editingAgent.request_template, null, 2)}
                  onChange={(e) => {
                    try {
                      setEditingAgent({...editingAgent!, request_template: JSON.parse(e.target.value)});
                    } catch {}
                  }}
                  rows={4}
                  className="font-mono text-sm"
                />
              </div>
              <div>
                <Label htmlFor="edit_response_extraction">Response Extraction (JSON)</Label>
                <Textarea
                  id="edit_response_extraction"
                  value={JSON.stringify(editingAgent.response_extraction, null, 2)}
                  onChange={(e) => {
                    try {
                      setEditingAgent({...editingAgent!, response_extraction: JSON.parse(e.target.value)});
                    } catch {}
                  }}
                  rows={3}
                  className="font-mono text-sm"
                />
              </div>
              <div>
                <Label htmlFor="edit_auth_config">Auth Config (JSON)</Label>
                <Textarea
                  id="edit_auth_config"
                  value={JSON.stringify(editingAgent.auth_config, null, 2)}
                  onChange={(e) => {
                    try {
                      setEditingAgent({...editingAgent!, auth_config: JSON.parse(e.target.value)});
                    } catch {}
                  }}
                  rows={3}
                  className="font-mono text-sm"
                />
              </div>
              <div className="flex items-center gap-2">
                <Input type="checkbox" id="edit_allowed" checked={editingAgent.allowed} onChange={(e) => setEditingAgent({...editingAgent!, allowed: e.target.checked})} />
                <Label htmlFor="edit_allowed">Allowed</Label>
              </div>
            </div>
            <DialogFooter>
              <Button variant="outline" onClick={() => setEditingAgent(null)}>Cancel</Button>
              <Button onClick={handleUpdateAgent}>Save</Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      )}
    </div>
  );
}