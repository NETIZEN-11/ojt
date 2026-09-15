"use client";

import { useEffect, useState } from "react";
import { DashboardLayout } from "@/components/ui/dashboard-layout";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { Plus, Loader2, Download, Shield, Zap, FileText, RefreshCw } from "lucide-react";

interface AttackCandidate {
  test_case_id: string;
  category: string;
  severity: string;
  prompt: string;
  expected_behavior: Record<string, unknown>;
  metadata: Record<string, unknown>;
}

interface RedTeamSession {
  id: string;
  target_agent_id: string;
  status: string;
  strategy: Record<string, unknown>;
  turns: Array<{
    turn_number: number;
    prompt: string;
    response: string;
    judge_verdict: string | null;
    judge_rationale: string | null;
  }>;
  final_verdict: string | null;
  created_at: string;
}

interface TargetAgent {
  id: string;
  name: string;
  description: string | null;
  endpoint_url: string;
  status: string;
}

export default function RedTeamPage() {
  const { isAuthenticated, isLoading } = useAuth();
  const [agents, setAgents] = useState<TargetAgent[]>([]);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [runningAttack, setRunningAttack] = useState(false);

  const [category, setCategory] = useState("jailbreak");
  const [batchSize, setBatchSize] = useState(10);
  const [generatedAttacks, setGeneratedAttacks] = useState<any[]>([]);
  const [selectedAgent, setSelectedAgent] = useState("");
  const [maxTurns, setMaxTurns] = useState(8);
  const [attackHistory, setAttackHistory] = useState<RedTeamSession[]>([]);
  const [loadingHistory, setLoadingHistory] = useState(false);

  const fetchData = async () => {
    try {
      const [agentsRes] = await Promise.all([
        api.get("/agents"),
      ]);
      setAgents(agentsRes.data);
    } catch (error) {
      console.error("Failed to fetch agents:", error);
    } finally {
      setLoading(false);
    }
  };

  const fetchAttackHistory = async () => {
    setLoadingHistory(true);
    try {
      // TODO: Backend endpoint /redteam/history not implemented yet
      // const res = await api.get("/redteam/history");
      // setAttackHistory(res.data);
      setAttackHistory([]);
    } catch (error) {
      console.error("Failed to fetch attack history:", error);
    } finally {
      setLoadingHistory(false);
    }
  };

  useEffect(() => {
    if (!isLoading) {
      if (!isAuthenticated) {
        window.location.href = "/login";
      } else {
        fetchData();
        fetchAttackHistory();
      }
    }
  }, [isAuthenticated, isLoading]);

  const handleGenerate = async () => {
    if (!category) return;
    setGenerating(true);
    try {
      const res = await api.post("/redteam/generate", {
        category,
        batch_size: batchSize,
      });
      setGeneratedAttacks(res.data);
    } catch (error) {
      console.error("Failed to generate attacks:", error);
    } finally {
      setGenerating(false);
    }
  };

  const handleRunAttack = async () => {
    if (!selectedAgent) return;
    setRunningAttack(true);
    try {
      const res = await api.post("/redteam/run", {
        agent_id: selectedAgent,
        max_turns: maxTurns,
      });
      console.log("Attack result:", res.data);
      fetchAttackHistory();
    } catch (error) {
      console.error("Failed to run attack:", error);
    } finally {
      setRunningAttack(false);
    }
  };

  const handleExport = () => {
    const data = { test_cases: generatedAttacks };
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `attacks-${Date.now()}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const categories = [
    { value: "jailbreak", label: "Jailbreak" },
    { value: "prompt_injection", label: "Prompt Injection" },
    { value: "pii", label: "PII" },
    { value: "safety", label: "Safety" },
    { value: "rag_poisoning", label: "RAG Poisoning" },
    { value: "agent_tool_abuse", label: "Agent Tool Abuse" },
    { value: "privilege_escalation", label: "Privilege Escalation" },
  ];

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
            <h1 className="text-3xl font-bold">Red Teaming</h1>
            <p className="text-muted-foreground">Generate and run adversarial attacks against target agents</p>
          </div>
        </div>

        <Tabs defaultValue="generate" className="space-y-4">
          <TabsList>
            <TabsTrigger value="generate">
              <Zap className="mr-2 h-4 w-4" /> Generate Attacks
            </TabsTrigger>
            <TabsTrigger value="run">
              <Shield className="mr-2 h-4 w-4" /> Run Attacks
            </TabsTrigger>
            <TabsTrigger value="history">
              <FileText className="mr-2 h-4 w-4" /> Attack History
            </TabsTrigger>
          </TabsList>

          <TabsContent value="generate">
            <div className="grid gap-4 lg:grid-cols-2">
              <Card>
                <CardHeader className="flex flex-row items-center justify-between">
                  <CardTitle>Generate Adversarial Attacks</CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="space-y-2">
                    <Label htmlFor="category">Attack Category</Label>
                    <Select value={category} onValueChange={setCategory}>
                      <SelectTrigger><SelectValue placeholder="Select category" /></SelectTrigger>
                      <SelectContent>
                        {categories.map((cat) => (
                          <SelectItem key={cat.value} value={cat.value}>{cat.label}</SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="batchSize">Number of Attacks</Label>
                    <Input
                      id="batchSize"
                      type="number"
                      value={batchSize}
                      onChange={(e) => setBatchSize(parseInt(e.target.value) || 10)}
                      min={1}
                      max={50}
                      className="w-32"
                    />
                  </div>

                  <Button onClick={handleGenerate} disabled={generating || !category}>
                    {generating ? (
                      <>
                        <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                        Generating...
                      </>
                    ) : (
                      <>
                        <Zap className="mr-2 h-4 w-4" />
                        Generate Attacks
                      </>
                    )}
                  </Button>

                  {generatedAttacks.length > 0 ? (
                    <div className="space-y-2">
                      <div className="flex items-center justify-between">
                        <h4 className="font-medium">Generated Attacks ({generatedAttacks.length})</h4>
                        <Button variant="outline" size="sm" onClick={handleExport}>
                          <Download className="mr-2 h-4 w-4" />
                          Export JSON
                        </Button>
                      </div>
                      <div className="max-h-96 overflow-y-auto space-y-2">
                        {generatedAttacks.slice(0, 10).map((attack, idx) => (
                          <div key={idx} className="p-3 bg-muted/50 rounded border">
                            <div className="flex items-center justify-between">
                              <span className="font-mono text-sm">{attack.test_case_id}</span>
                              <span className="px-2 py-0.5 text-xs rounded bg-muted text-muted-foreground">
                                {attack.category}
                              </span>
                            </div>
                            <p className="text-sm mt-1 line-clamp-2">{attack.prompt}</p>
                          </div>
                        ))}
                        {generatedAttacks.length > 10 ? (
                          <p className="text-sm text-muted-foreground text-center">
                            And {generatedAttacks.length - 10} more...
                          </p>
                        ) : null}
                      </div>
                    </div>
                  ) : null}
                </CardContent>
              </Card>
            </div>
          </TabsContent>

          <TabsContent value="run">
                <div className="grid gap-4 lg:grid-cols-2">
                  <Card>
                    <CardHeader>
                      <CardTitle>Run Red Team Attack</CardTitle>
                    </CardHeader>
                    <CardContent className="space-y-4">
                      <div className="space-y-2">
                        <Label htmlFor="agent">Target Agent</Label>
                        <Select value={selectedAgent} onValueChange={setSelectedAgent}>
                          <SelectTrigger><SelectValue placeholder="Select target agent" /></SelectTrigger>
                          <SelectContent>
                            {agents.map((agent) => (
                              <SelectItem key={agent.id} value={agent.id}>
                                {agent.name} ({agent.status})
                              </SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                      </div>

                      <div className="space-y-2">
                        <Label htmlFor="maxTurns">Max Turns</Label>
                        <Input
                          id="maxTurns"
                          type="number"
                          value={maxTurns}
                          onChange={(e) => setMaxTurns(parseInt(e.target.value) || 8)}
                          min={1}
                          max={20}
                          className="w-32"
                        />
                      </div>

                      <Button onClick={handleRunAttack} disabled={runningAttack || !selectedAgent} className="w-full">
                        {runningAttack ? (
                          <>
                            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                            Running Attack...
                          </>
                        ) : (
                          <>
                            <Shield className="mr-2 h-4 w-4" />
                            Start Attack
                          </>
                        )}
                      </Button>
                    </CardContent>
                  </Card>

                  <Card>
                    <CardHeader>
                      <CardTitle>Selected Agent</CardTitle>
                    </CardHeader>
                    <CardContent>
                      {selectedAgent ? (
                        (() => {
                          const agent = agents.find(a => a.id === selectedAgent);
                          if (!agent) return null;
                          return (
                            <div className="space-y-2">
                              <p className="font-medium">{agent.name}</p>
                              <p className="text-sm text-muted-foreground">{agent.endpoint_url}</p>
                              <p className="text-sm">Status: <span className="font-medium">{agent.status}</span></p>
                              <p className="text-sm">Max Turns: {maxTurns}</p>
                            </div>
                          );
                        })()
                      ) : (
                        <p className="text-muted-foreground">Select an agent to run attacks</p>
                      )}
                    </CardContent>
                  </Card>
                </div>
              </TabsContent>

              <TabsContent value="history">
                <Card>
                  <CardHeader className="flex flex-row items-center justify-between">
                    <CardTitle>Attack History</CardTitle>
                    <Button variant="outline" size="sm" onClick={fetchAttackHistory} disabled={loadingHistory}>
                      {loadingHistory ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <RefreshCw className="mr-2 h-4 w-4" />}
                      Refresh
                    </Button>
                  </CardHeader>
                  <CardContent>
                    {loadingHistory ? (
                      <div className="text-center py-8">
                        <Loader2 className="h-8 w-8 animate-spin mx-auto" />
                      </div>
                    ) : attackHistory.length === 0 ? (
                      <div className="text-center py-8 text-muted-foreground">
                        <Shield className="h-12 w-12 mx-auto mb-4 opacity-50" />
                        <p>No attack history yet</p>
                        <p className="text-sm">Run your first red team attack to see history</p>
                      </div>
                    ) : (
                      <div className="overflow-x-auto">
                        <table className="w-full">
                          <thead>
                            <tr className="border-b">
                              <th className="text-left p-4">Session ID</th>
                              <th className="text-left p-4">Agent</th>
                              <th className="text-left p-4">Status</th>
                              <th className="text-left p-4">Verdict</th>
                              <th className="text-left p-4">Turns</th>
                              <th className="text-left p-4">Created</th>
                            </tr>
                          </thead>
                          <tbody>
                            {attackHistory.map((session) => (
                              <tr key={session.id} className="border-b hover:bg-muted/50">
                                <td className="p-4 font-mono text-sm">{session.id.slice(0, 8)}...</td>
                                <td className="p-4 font-mono text-sm">{session.target_agent_id.slice(0, 8)}...</td>
                                <td className="p-4">
                                  <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                                    session.status === "completed" ? "bg-green-100 text-green-800" :
                                    session.status === "failed" ? "bg-red-100 text-red-800" :
                                    "bg-yellow-100 text-yellow-800"
                                  }`}>
                                    {session.status}
                                  </span>
                                </td>
                                <td className="p-4">
                                  {session.final_verdict ? (
                                    <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                                      session.final_verdict === "FAIL" ? "bg-red-100 text-red-800" :
                                      session.final_verdict === "PASS" ? "bg-green-100 text-green-800" :
                                      "bg-yellow-100 text-yellow-800"
                                    }`}>
                                      {session.final_verdict}
                                    </span>
                                  ) : "N/A"}
                                </td>
                                <td className="p-4">{session.turns.length}</td>
                                <td className="p-4 text-sm text-muted-foreground">{new Date(session.created_at).toLocaleString()}</td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    )}
                  </CardContent>
                </Card>
          </TabsContent>
        </Tabs>
      </div>
    </DashboardLayout>
  );
}