"use client";

import { useEffect, useState, useCallback } from "react";
import { DashboardLayout } from "@/components/ui/dashboard-layout";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { Shield, Bug, AlertTriangle, CheckCircle, Clock, FileSearch, Code2, Loader2 } from "lucide-react";

export default function CodeScanPage() {
  const { isAuthenticated, isLoading } = useAuth();
  const [findings, setFindings] = useState<any[]>([]);
  const [summary, setSummary] = useState({ critical: 0, high: 0, medium: 0, low: 0 });
  const [loading, setLoading] = useState(false);
  const [scanning, setScanning] = useState(false);
  const [scanInfo, setScanInfo] = useState<any>(null);

  const fetchFindings = useCallback(async () => {
    setLoading(true);
    try {
      const res = await api.get("/code-scan/findings").catch(() => ({ data: { findings: [] } }));
      const data = res.data.findings || res.data;
      const list = Array.isArray(data) ? data : [];
      setFindings(list);
      const s = { critical: 0, high: 0, medium: 0, low: 0 };
      list.forEach((f: any) => { if (s[f.severity as keyof typeof s] !== undefined) (s as any)[f.severity]++; });
      setSummary(s);
    } catch (e) { console.error(e); } finally { setLoading(false); }
  }, []);

  const runScan = async () => {
    setScanning(true);
    try {
      const res = await api.post("/security/code-scan", null, { params: { project_path: "." } }).catch(() => api.get("/code-scan/"));
      setScanInfo(res.data);
      fetchFindings();
    } catch (e: any) {
      try {
        const res = await api.get("/code-scan/");
        setScanInfo(res.data);
      } catch {}
    } finally { setScanning(false); }
  };

  useEffect(() => {
    if (!isLoading) {
      if (!isAuthenticated) window.location.href = "/login";
      else fetchFindings();
    }
  }, [isAuthenticated, isLoading, fetchFindings]);

  if (isLoading || !isAuthenticated) return <DashboardLayout><div className="flex h-[calc(100vh-4rem)] items-center justify-center"><div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div></div></DashboardLayout>;

  return (
    <DashboardLayout>
      <div className="space-y-6">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <h1 className="text-3xl font-bold flex items-center gap-2"><Code2 className="h-8 w-8 text-primary" />Code Scanning</h1>
            <p className="text-muted-foreground">Find LLM vulnerabilities in your IDE and CI/CD — promptfoo style</p>
          </div>
          <Button onClick={runScan} disabled={scanning}>{scanning ? <><Loader2 className="mr-2 h-4 w-4 animate-spin" />Scanning...</> : <><FileSearch className="mr-2 h-4 w-4" />Run Scan</>}</Button>
        </div>

        <div className="grid gap-4 md:grid-cols-4">
          <Card><CardHeader className="pb-2 flex flex-row items-center justify-between"><CardTitle className="text-sm">Critical</CardTitle><AlertTriangle className="h-4 w-4 text-red-600" /></CardHeader><CardContent><div className="text-2xl font-bold text-red-600">{summary.critical}</div></CardContent></Card>
          <Card><CardHeader className="pb-2 flex flex-row items-center justify-between"><CardTitle className="text-sm">High</CardTitle><Bug className="h-4 w-4 text-orange-600" /></CardHeader><CardContent><div className="text-2xl font-bold text-orange-600">{summary.high}</div></CardContent></Card>
          <Card><CardHeader className="pb-2 flex flex-row items-center justify-between"><CardTitle className="text-sm">Medium</CardTitle><Shield className="h-4 w-4 text-yellow-600" /></CardHeader><CardContent><div className="text-2xl font-bold text-yellow-600">{summary.medium}</div></CardContent></Card>
          <Card><CardHeader className="pb-2 flex flex-row items-center justify-between"><CardTitle className="text-sm">Low</CardTitle><CheckCircle className="h-4 w-4 text-blue-600" /></CardHeader><CardContent><div className="text-2xl font-bold text-blue-600">{summary.low}</div></CardContent></Card>
        </div>

        <Card>
          <CardHeader><CardTitle>CLI Usage</CardTitle></CardHeader>
          <CardContent>
            <pre className="bg-muted p-4 rounded text-sm overflow-auto">{`# Install & run locally (like promptfoo)
pip install artef
artef security scan-model ./my-model
artef code-scan --path ./src

# CI/CD — add to your pipeline
- uses: artef/scan-action@v1
  with:
    path: .
    fail-on: critical`}</pre>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between"><CardTitle>Findings ({findings.length})</CardTitle><Badge>{findings.length} issues</Badge></CardHeader>
          <CardContent>
            {loading ? <p>Loading...</p> : findings.length === 0 ? (
              <div className="text-center py-8 text-muted-foreground"><CheckCircle className="h-12 w-12 mx-auto mb-2 opacity-30 text-green-600" /><p>No vulnerabilities found</p><p className="text-sm">Run a scan to check for prompt injection, secret exposure, data leakage</p></div>
            ) : (
              <div className="space-y-2 max-h-[600px] overflow-auto">
                {findings.map((f: any, i: number) => (
                  <div key={i} className="p-3 border rounded">
                    <div className="flex items-center gap-2"><Badge variant={f.severity === "critical" ? "destructive" : f.severity === "high" ? "destructive" : "secondary"}>{f.severity}</Badge><Badge variant="outline">{f.category}</Badge></div>
                    <p className="text-sm mt-2">{f.description}</p>
                    <p className="text-xs text-muted-foreground mt-1 font-mono">{f.file_path}:{f.line_number}</p>
                    {f.evidence && <pre className="text-xs bg-muted p-2 rounded mt-1 overflow-auto">{f.evidence}</pre>}
                  </div>
                ))}
              </div>
            )}
            {scanInfo && <pre className="text-xs bg-muted p-3 rounded mt-4 overflow-auto max-h-32">{JSON.stringify(scanInfo, null, 2)}</pre>}
          </CardContent>
        </Card>
      </div>
    </DashboardLayout>
  );
}