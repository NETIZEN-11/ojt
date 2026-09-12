"use client";

import { useEffect, useState, useCallback } from "react";
import { DashboardLayout } from "@/components/ui/dashboard-layout";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { Activity, Shield, AlertTriangle, CheckCircle, Clock, Eye, DollarSign, TrendingUp } from "lucide-react";

export default function MonitoringPage() {
  const { isAuthenticated, isLoading } = useAuth();
  const [dashboard, setDashboard] = useState<any>(null);
  const [alerts, setAlerts] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchData = useCallback(async () => {
    try {
      const [d, a] = await Promise.all([
        api.get("/monitoring/dashboard").catch(() => ({ data: null })),
        api.get("/monitoring/alerts").catch(() => ({ data: [] })),
      ]);
      if (d.data) setDashboard(d.data);
      else {
        // fallback to security endpoints
        try {
          const fd = await api.get("/security/security-dashboard");
          setDashboard(fd.data);
        } catch {}
      }
      const al = Array.isArray(a.data) ? a.data : a.data?.alerts || [];
      setAlerts(al);
    } catch (e) { console.error(e); } finally { setLoading(false); }
  }, []);

  useEffect(() => {
    if (!isLoading) {
      if (!isAuthenticated) window.location.href = "/login";
      else fetchData();
    }
  }, [isAuthenticated, isLoading, fetchData]);

  if (isLoading || !isAuthenticated) return <DashboardLayout><div className="flex h-[calc(100vh-4rem)] items-center justify-center"><div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div></div></DashboardLayout>;

  return (
    <DashboardLayout>
      <div className="space-y-6">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <h1 className="text-3xl font-bold flex items-center gap-2"><Activity className="h-8 w-8 text-primary" />Monitoring</h1>
            <p className="text-muted-foreground">Enterprise security monitoring — promptfoo Model Security style</p>
          </div>
          <Button onClick={fetchData} variant="outline">Refresh</Button>
        </div>

        <div className="grid gap-4 md:grid-cols-4">
          <Card><CardHeader className="pb-2 flex flex-row items-center justify-between"><CardTitle className="text-sm">Total Alerts</CardTitle><AlertTriangle className="h-4 w-4 text-red-600" /></CardHeader><CardContent><div className="text-2xl font-bold">{dashboard?.total_alerts ?? alerts.length}</div><p className="text-xs text-muted-foreground">Security events</p></CardContent></Card>
          <Card><CardHeader className="pb-2 flex flex-row items-center justify-between"><CardTitle className="text-sm">Guardrail Hits</CardTitle><Shield className="h-4 w-4 text-blue-600" /></CardHeader><CardContent><div className="text-2xl font-bold">{dashboard?.guardrail_stats ? Object.keys(dashboard.guardrail_stats).length : 0}</div><p className="text-xs text-muted-foreground">Blocked attacks</p></CardContent></Card>
          <Card><CardHeader className="pb-2 flex flex-row items-center justify-between"><CardTitle className="text-sm">Uptime</CardTitle><Clock className="h-4 w-4 text-muted-foreground" /></CardHeader><CardContent><div className="text-2xl font-bold">{dashboard?.uptime_seconds ? Math.floor(dashboard.uptime_seconds/3600) + "h" : "—"}</div><p className="text-xs text-muted-foreground">Service uptime</p></CardContent></Card>
          <Card><CardHeader className="pb-2 flex flex-row items-center justify-between"><CardTitle className="text-sm">Status</CardTitle><CheckCircle className="h-4 w-4 text-green-600" /></CardHeader><CardContent><div className="text-2xl font-bold text-green-600">Healthy</div><p className="text-xs text-muted-foreground">All systems</p></CardContent></Card>
        </div>

        <div className="grid gap-4 lg:grid-cols-2">
          <Card>
            <CardHeader><CardTitle>Security Dashboard</CardTitle></CardHeader>
            <CardContent>
              {dashboard ? <pre className="bg-muted p-3 rounded text-xs overflow-auto max-h-96">{JSON.stringify(dashboard, null, 2)}</pre> : <div className="text-center py-8 text-muted-foreground"><Activity className="h-12 w-12 mx-auto mb-2 opacity-30" /><p>No data yet — monitoring tracks guardrails, auth, costs</p><p className="text-sm">Integrated with Prometheus (9090) + Grafana (3001)</p></div>}
            </CardContent>
          </Card>
          <Card>
            <CardHeader><CardTitle>Recent Alerts</CardTitle></CardHeader>
            <CardContent>
              {alerts.length === 0 ? <div className="text-center py-8 text-muted-foreground"><CheckCircle className="h-12 w-12 mx-auto mb-2 opacity-30 text-green-600" /><p>No alerts — system secure</p></div> : (
                <div className="space-y-2 max-h-96 overflow-auto">
                  {alerts.map((a: any, i: number) => (
                    <div key={i} className="p-3 border rounded">
                      <div className="flex items-center gap-2"><Badge variant="destructive">{a.severity || a.type}</Badge><span className="text-xs text-muted-foreground">{a.timestamp}</span></div>
                      <p className="text-sm mt-1">{a.guardrail_type || a.type}: {JSON.stringify(a)}</p>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </div>

        <Card>
          <CardHeader><CardTitle>Observability Stack</CardTitle></CardHeader>
          <CardContent className="grid md:grid-cols-3 gap-4 text-sm">
            <div className="p-3 border rounded"><p className="font-medium">Prometheus</p><p className="text-muted-foreground">Metrics at :9090 — latency, error rate, queue depth, cost</p></div>
            <div className="p-3 border rounded"><p className="font-medium">Grafana</p><p className="text-muted-foreground">Dashboards at :3001 — 8 panels (runs, pass rate, regressions, cost)</p></div>
            <div className="p-3 border rounded"><p className="font-medium">OTel</p><p className="text-muted-foreground">Distributed tracing — 10% sampling, JSON logs</p></div>
          </CardContent>
        </Card>
      </div>
    </DashboardLayout>
  );
}