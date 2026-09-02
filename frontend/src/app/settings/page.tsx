"use client";

import { useEffect, useState, useCallback } from "react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label"
import { Switch } from "@/components/ui/switch";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger, DialogFooter } from "@/components/ui/dialog";
import { Textarea } from "@/components/ui/textarea";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { api } from "@/lib/api";
import { formatDate } from "@/lib/utils";
import { useAuth } from "@/lib/auth";
import { User, Shield, Key, Database, Server, Bell, Save, Loader2, Badge as BadgeIcon, Edit, Trash2, Plus } from "lucide-react";

interface UserInfo {
  id: string;
  email: string;
  username: string;
  full_name: string | null;
  is_active: boolean;
  is_superuser: boolean;
  last_login: string | null;
  created_at: string;
  roles: string[];
}

interface FeatureFlag {
  id: string;
  name: string;
  description: string | null;
  enabled: boolean;
  rollout_percentage: number;
  target_roles: string[];
  created_at: string;
  updated_at: string;
}

interface AuditLog {
  id: string;
  user_id: string | null;
  action: string;
  resource_type: string | null;
  resource_id: string | null;
  details: Record<string, unknown>;
  ip_address: string | null;
  user_agent: string | null;
  created_at: string;
}

export default function SettingsPage() {
  const { isAuthenticated, isLoading, user } = useAuth();
  const [userInfo, setUserInfo] = useState<UserInfo | null>(null);
  const [featureFlags, setFeatureFlags] = useState<FeatureFlag[]>([]);
  const [auditLogs, setAuditLogs] = useState<AuditLog[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [activeTab, setActiveTab] = useState("profile");
  const [showCreateFlagDialog, setShowCreateFlagDialog] = useState(false);
  const [newFlag, setNewFlag] = useState({ name: "", description: "", enabled: false, rollout_percentage: 0, target_roles: [] });
  const [editingFlag, setEditingFlag] = useState<FeatureFlag | null>(null);

  const fetchUserInfo = useCallback(async () => {
    try {
      const res = await api.get("/users/me");
      setUserInfo(res.data);
    } catch (error) {
      console.error("Failed to fetch user info:", error);
    }
  }, []);

  const fetchFeatureFlags = useCallback(async () => {
    try {
      const res = await api.get("/settings/feature-flags");
      setFeatureFlags(res.data);
    } catch (error) {
      console.error("Failed to fetch feature flags:", error);
    }
  }, []);

  const fetchAuditLogs = useCallback(async () => {
    try {
      const res = await api.get("/settings/audit-logs?limit=100");
      setAuditLogs(res.data);
    } catch (error) {
      console.error("Failed to fetch audit logs:", error);
    }
  }, []);

  useEffect(() => {
    if (!isLoading) {
      if (!isAuthenticated) {
        window.location.href = "/login";
      } else {
        fetchUserInfo();
        fetchFeatureFlags();
        fetchAuditLogs();
      }
    }
  }, [isAuthenticated, isLoading, fetchUserInfo, fetchFeatureFlags, fetchAuditLogs]);

  const handleUpdateProfile = async (data: Partial<UserInfo>) => {
    setSaving(true);
    try {
      await api.patch("/users/me", data);
      setUserInfo(prev => prev ? { ...prev, ...data } : null);
    } catch (error) {
      console.error("Failed to update profile:", error);
    } finally {
      setSaving(false);
    }
  };

  const handleCreateFlag = async () => {
    if (!newFlag.name) return;
    setSaving(true);
    try {
      await api.post("/settings/feature-flags", newFlag);
      setShowCreateFlagDialog(false);
      setNewFlag({ name: "", description: "", enabled: false, rollout_percentage: 0, target_roles: [] });
      fetchFeatureFlags();
    } catch (error) {
      console.error("Failed to create feature flag:", error);
    } finally {
      setSaving(false);
    }
  };

  const handleUpdateFlag = async () => {
    if (!editingFlag) return;
    setSaving(true);
    try {
      await api.put(`/settings/feature-flags/${editingFlag.id}`, editingFlag);
      setEditingFlag(null);
      fetchFeatureFlags();
    } catch (error) {
      console.error("Failed to update feature flag:", error);
    } finally {
      setSaving(false);
    }
  };

  const handleDeleteFlag = async (flagId: string) => {
    if (!confirm("Are you sure you want to delete this feature flag?")) return;
    try {
      await api.delete(`/settings/feature-flags/${flagId}`);
      fetchFeatureFlags();
    } catch (error) {
      console.error("Failed to delete feature flag:", error);
    }
  };

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
          <h1 className="text-3xl font-bold">Settings</h1>
          <p className="text-muted-foreground">Manage your profile and system settings</p>
        </div>
      </div>

      <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-6">
        <TabsList>
          <TabsTrigger value="profile"><User className="mr-2 h-4 w-4" /> Profile</TabsTrigger>
          <TabsTrigger value="security"><Shield className="mr-2 h-4 w-4" /> Security</TabsTrigger>
          <TabsTrigger value="features"><Key className="mr-2 h-4 w-4" /> Feature Flags</TabsTrigger>
          <TabsTrigger value="audit"><Database className="mr-2 h-4 w-4" /> Audit Logs</TabsTrigger>
        </TabsList>

        <TabsContent value="profile">
          <div className="grid gap-6 md:grid-cols-3">
            <Card>
              <CardHeader>
                <CardTitle>Profile Information</CardTitle>
                <CardDescription>Update your personal information</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div>
                  <Label htmlFor="email">Email</Label>
                  <Input
                    id="email"
                    value={userInfo?.email || ""}
                    onChange={(e) => handleUpdateProfile({ email: e.target.value })}
                    disabled={!userInfo}
                  />
                </div>
                <div>
                  <Label htmlFor="username">Username</Label>
                  <Input
                    id="username"
                    value={userInfo?.username || ""}
                    onChange={(e) => handleUpdateProfile({ username: e.target.value })}
                    disabled={!userInfo}
                  />
                </div>
                <div>
                  <Label htmlFor="full_name">Full Name</Label>
                  <Input
                    id="full_name"
                    value={userInfo?.full_name || ""}
                    onChange={(e) => handleUpdateProfile({ full_name: e.target.value })}
                    disabled={!userInfo}
                  />
                </div>
                <div className="flex items-center gap-2">
                  <Switch
                    id="is_active"
                    checked={userInfo?.is_active || false}
                    onCheckedChange={(checked) => handleUpdateProfile({ is_active: checked })}
                  />
                  <Label htmlFor="is_active">Active</Label>
                </div>
                {userInfo && (
                  <div className="border-t pt-4 space-y-2">
                    <p className="text-sm text-muted-foreground">Account Details</p>
                    <dl className="grid grid-cols-2 gap-2 text-sm">
                      <dt className="text-muted-foreground">User ID</dt>
                      <dd className="font-mono text-xs">{userInfo.id}</dd>
                      <dt className="text-muted-foreground">Superuser</dt>
                      <dd>{userInfo.is_superuser ? "Yes" : "No"}</dd>
                      <dt className="text-muted-foreground">Last Login</dt>
                      <dd>{userInfo.last_login ? formatDate(userInfo.last_login) : "Never"}</dd>
                      <dt className="text-muted-foreground">Created</dt>
                      <dd>{formatDate(userInfo.created_at)}</dd>
                      <dt className="text-muted-foreground">Roles</dt>
                      <dd>{userInfo.roles.join(", ") || "None"}</dd>
                    </dl>
                  </div>
                )}
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Security</CardTitle>
                <CardDescription>Manage authentication settings</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div>
                  <Label htmlFor="password">Change Password</Label>
                  <Input
                    id="password"
                    type="password"
                    placeholder="Enter new password"
                    autoComplete="new-password"
                  />
                  <p className="text-sm text-muted-foreground mt-1">Leave blank to keep current password</p>
                </div>
                <Button>
                  <Save className="mr-2 h-4 w-4" /> Update Password
                </Button>
                <div className="border-t pt-4">
                  <h4 className="font-medium mb-2">API Keys</h4>
                  <p className="text-sm text-muted-foreground">Manage your API keys for programmatic access</p>
                  <Button variant="outline" className="mt-2"><Key className="mr-2 h-4 w-4" /> Generate API Key</Button>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Preferences</CardTitle>
                <CardDescription>Customize your experience</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="font-medium">Dark Mode</p>
                    <p className="text-sm text-muted-foreground">Use dark theme</p>
                  </div>
                  <Switch defaultChecked={false} />
                </div>
                <div className="flex items-center justify-between">
                  <div>
                    <p className="font-medium">Email Notifications</p>
                    <p className="text-sm text-muted-foreground">Receive email alerts</p>
                  </div>
                  <Switch defaultChecked={true} />
                </div>
                <div className="flex items-center justify-between">
                  <div>
                    <p className="font-medium">Auto-refresh Dashboard</p>
                    <p className="text-sm text-muted-foreground">Automatically refresh data</p>
                  </div>
                  <Switch defaultChecked={false} />
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        <TabsContent value="security">
          <Card>
            <CardHeader>
              <CardTitle>System Security Settings</CardTitle>
              <CardDescription>Configure security policies</CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              <div>
                <h4 className="font-medium mb-4">Rate Limiting</h4>
                <div className="grid gap-4 md:grid-cols-2">
                  <div>
                    <Label htmlFor="rate_limit_requests">Requests per Window</Label>
                    <Input id="rate_limit_requests" type="number" defaultValue={100} />
                  </div>
                  <div>
                    <Label htmlFor="rate_limit_window">Window (seconds)</Label>
                    <Input id="rate_limit_window" type="number" defaultValue={60} />
                  </div>
                </div>
              </div>
              <div>
                <h4 className="font-medium mb-4">SSRF Protection</h4>
                <div className="flex items-center justify-between">
                  <div>
                    <p className="font-medium">Block Private IPs</p>
                    <p className="text-sm text-muted-foreground">Prevent requests to private IP ranges</p>
                  </div>
                  <Switch defaultChecked={true} />
                </div>
                <div className="flex items-center justify-between mt-4">
                  <div>
                    <p className="font-medium">Allowed Hosts</p>
                    <p className="text-sm text-muted-foreground">Comma-separated list of allowed hosts</p>
                  </div>
                  <Input placeholder="example.com, api.example.com" className="w-64" />
                </div>
              </div>
              <div>
                <h4 className="font-medium mb-4">Cost Limits</h4>
                <div className="grid gap-4 md:grid-cols-2">
                  <div>
                    <Label htmlFor="cost_per_run">Per Run Limit (USD)</Label>
                    <Input id="cost_per_run" type="number" step="0.01" defaultValue={5.0} />
                  </div>
                  <div>
                    <Label htmlFor="cost_daily">Daily Limit (USD)</Label>
                    <Input id="cost_daily" type="number" step="0.01" defaultValue={100.0} />
                  </div>
                </div>
              </div>
              <Button><Save className="mr-2 h-4 w-4" /> Save Security Settings</Button>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="features">
          <div className="flex items-center justify-between">
            <Card>
              <CardHeader>
                <CardTitle>Feature Flags</CardTitle>
                <CardDescription>Toggle features without deploying</CardDescription>
              </CardHeader>
              <CardContent>
                {featureFlags.length === 0 ? (
                  <div className="text-center py-8">
                    <p className="text-muted-foreground">No feature flags configured</p>
                  </div>
                ) : (
                  <div className="space-y-4">
                    {featureFlags.map((flag) => (
                      <div key={flag.id} className="flex items-center justify-between p-4 border rounded-lg">
                        <div className="flex-1">
                          <div className="flex items-center gap-2">
                            <p className="font-medium">{flag.name}</p>
                            {flag.enabled && <Badge variant="default">Enabled</Badge>}
                            {!flag.enabled && <Badge variant="secondary">Disabled</Badge>}
                          </div>
                          {flag.description && <p className="text-sm text-muted-foreground">{flag.description}</p>}
                          <div className="flex items-center gap-4 text-sm text-muted-foreground mt-1">
                            <span>Rollout: {flag.rollout_percentage}%</span>
                            <span>Target Roles: {flag.target_roles.length > 0 ? flag.target_roles.join(", ") : "All"}</span>
                          </div>
                        </div>
                        <div className="flex items-center gap-2">
                          <Switch
                            checked={flag.enabled}
                            onCheckedChange={(checked) => {
                              setEditingFlag({ ...flag, enabled: checked });
                              handleUpdateFlag();
                            }}
                          />
                          <Button variant="ghost" size="icon" onClick={() => setEditingFlag(flag)}>
                            <Edit className="h-4 w-4" />
                          </Button>
                          <Button variant="ghost" size="icon" onClick={() => handleDeleteFlag(flag.id)}>
                            <Trash2 className="h-4 w-4 text-destructive" />
                          </Button>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>
            <Dialog open={showCreateFlagDialog} onOpenChange={setShowCreateFlagDialog}>
              <DialogTrigger asChild>
                <Button><Plus className="mr-2 h-4 w-4" /> New Feature Flag</Button>
              </DialogTrigger>
              <DialogContent>
                <DialogHeader>
                  <DialogTitle>Create Feature Flag</DialogTitle>
                </DialogHeader>
                <div className="space-y-4 py-4">
                  <div>
                    <Label htmlFor="flag_name">Name</Label>
                    <Input
                      id="flag_name"
                      value={newFlag.name}
                      onChange={(e) => setNewFlag({...newFlag, name: e.target.value})}
                      placeholder="feature_name"
                    />
                  </div>
                  <div>
                    <Label htmlFor="flag_description">Description</Label>
                    <Textarea
                      id="flag_description"
                      value={newFlag.description}
                      onChange={(e) => setNewFlag({...newFlag, description: e.target.value})}
                      rows={2}
                    />
                  </div>
                  <div className="grid gap-4 md:grid-cols-2">
                    <div>
                      <Label htmlFor="flag_rollout">Rollout Percentage</Label>
                      <Input
                        id="flag_rollout"
                        type="number"
                        min={0}
                        max={100}
                        value={newFlag.rollout_percentage}
                        onChange={(e) => setNewFlag({...newFlag, rollout_percentage: parseInt(e.target.value)})}
                      />
                    </div>
                    <div className="flex items-center gap-2">
                      <Switch
                        id="flag_enabled"
                        checked={newFlag.enabled}
                        onCheckedChange={(checked) => setNewFlag({...newFlag, enabled: checked})}
                      />
                      <Label htmlFor="flag_enabled">Enabled by Default</Label>
                    </div>
                  </div>
                </div>
                <DialogFooter>
                  <Button variant="outline" onClick={() => setShowCreateFlagDialog(false)}>Cancel</Button>
                  <Button onClick={handleCreateFlag} disabled={saving || !newFlag.name}>
                    {saving ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : "Create"}
                  </Button>
                </DialogFooter>
              </DialogContent>
            </Dialog>
          </div>
        </TabsContent>

        <TabsContent value="audit">
          <Card>
            <CardHeader>
              <CardTitle>Audit Logs</CardTitle>
              <CardDescription>System activity and changes</CardDescription>
            </CardHeader>
            <CardContent>
              {auditLogs.length === 0 ? (
                <div className="text-center py-8">
                  <p className="text-muted-foreground">No audit logs found</p>
                </div>
              ) : (
                <div className="overflow-x-auto">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Timestamp</TableHead>
                        <TableHead>User</TableHead>
                        <TableHead>Action</TableHead>
                        <TableHead>Resource</TableHead>
                        <TableHead>IP Address</TableHead>
                        <TableHead>Details</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {auditLogs.map((log) => (
                        <TableRow key={log.id}>
                          <TableCell className="text-sm text-muted-foreground">{formatDate(log.created_at)}</TableCell>
                          <TableCell className="font-mono text-xs">{log.user_id?.slice(0, 8) || "System"}</TableCell>
                          <TableCell><Badge variant="secondary">{log.action}</Badge></TableCell>
                          <TableCell>
                            {log.resource_type && log.resource_id && (
                              <span className="font-mono text-xs">
                                {log.resource_type}:{log.resource_id.toString().slice(0, 8)}
                              </span>
                            )}
                          </TableCell>
                          <TableCell className="font-mono text-xs">{log.ip_address || "N/A"}</TableCell>
                          <TableCell>
                            <pre className="text-xs font-mono max-w-xs overflow-auto">
                              {JSON.stringify(log.details, null, 2).slice(0, 200)}
                            </pre>
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}