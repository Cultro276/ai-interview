"use client";
import { useEffect, useState } from "react";
import { apiFetch } from "@/lib/api";
import { Card, CardContent, CardHeader } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";

type Tenant = { id: number; email: string; is_admin: boolean; is_active?: boolean; created_at: string };

export default function InternalAdmin() {
  // Do not render in production unless the path is known; no link is provided anywhere.
  const [tenants, setTenants] = useState<Tenant[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [creating, setCreating] = useState(false);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [firstName, setFirstName] = useState("");
  const [lastName, setLastName] = useState("");

  const load = async () => {
    setLoading(true);
    try {
      const data = await apiFetch<Tenant[]>("/api/v1/internal/tenants");
      setTenants(data);
    } catch (e: any) {
      setError(e.message || "Failed to load tenants");
    } finally {
      setLoading(false);
    }
  };
  useEffect(() => { load(); }, []);

  const deactivate = async (ownerId: number) => {
    if (!confirm("Deactivate this tenant?")) return;
    try {
      await apiFetch(`/api/v1/internal/tenant/${ownerId}`, { method: "DELETE" });
      await load();
    } catch {}
  };
  const reactivate = async (ownerId: number) => {
    try {
      await apiFetch(`/api/v1/internal/tenant/${ownerId}/reactivate`, { method: "POST" });
      await load();
    } catch {}
  };
  const overview = async (ownerId: number) => {
    try {
      const data = await apiFetch<{jobs:number;candidates:number;interviews:number}>(`/api/v1/internal/tenant/${ownerId}/overview`);
      alert(`Jobs: ${data.jobs}\nCandidates: ${data.candidates}\nInterviews: ${data.interviews}`);
    } catch {}
  };
  const createOwner = async () => {
    setCreating(true);
    try {
      await apiFetch(`/api/v1/internal/tenant`, { method: "POST", body: JSON.stringify({ email, password, first_name: firstName || undefined, last_name: lastName || undefined }) });
      setEmail(""); setPassword(""); setFirstName(""); setLastName("");
      await load();
    } catch (e:any) {
      alert(e.message || "Failed to create owner");
    } finally {
      setCreating(false);
    }
  };
  const resetPassword = async (ownerId: number) => {
    const np = prompt("New password");
    if (!np) return;
    try { await apiFetch(`/api/v1/internal/tenant/${ownerId}/reset-password`, { method: "POST", body: JSON.stringify({ new_password: np }) }); alert("Password reset"); } catch {}
  };
  const impersonate = async (ownerId: number) => {
    try {
      const res = await apiFetch<{access_token:string}>(`/api/v1/internal/tenant/${ownerId}/impersonate`, { method: "POST" });
      localStorage.setItem("token", res.access_token);
      alert("Impersonated. Refreshing as owner...");
      window.location.href = "/dashboard";
    } catch {}
  };

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">Founders Console</h1>
      {error && <div className="text-sm text-red-600 mb-3">{error}</div>}
      <Card className="bg-white dark:bg-neutral-900 border border-neutral-200 dark:border-neutral-800">
        <CardHeader>
          <div className="flex items-center justify-between">
            <h3 className="text-lg font-semibold">Tenants</h3>
            <div className="flex items-center gap-2">
              <Button onClick={load}>Refresh</Button>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <div className="mb-4 grid grid-cols-1 md:grid-cols-4 gap-3">
            <Input placeholder="Owner email" value={email} onChange={(e)=>setEmail(e.target.value)} />
            <Input placeholder="Temp password" value={password} type="password" onChange={(e)=>setPassword(e.target.value)} />
            <Input placeholder="First name (opt)" value={firstName} onChange={(e)=>setFirstName(e.target.value)} />
            <Input placeholder="Last name (opt)" value={lastName} onChange={(e)=>setLastName(e.target.value)} />
            <div>
              <Button onClick={createOwner} disabled={creating || !email || !password}>Create owner</Button>
            </div>
          </div>
          {loading ? (
            <div>Loading...</div>
          ) : (
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200 dark:divide-neutral-800 text-sm">
                <thead>
                  <tr>
                    <th className="px-4 py-2 text-left">ID</th>
                    <th className="px-4 py-2 text-left">Email</th>
                    <th className="px-4 py-2 text-left">Owner?</th>
                    <th className="px-4 py-2 text-left">Created</th>
                    <th className="px-4 py-2"></th>
                  </tr>
                </thead>
                <tbody>
                  {tenants.map(t => (
                    <tr key={t.id} className="border-b border-gray-200 dark:border-neutral-800">
                      <td className="px-4 py-3">{t.id}</td>
                      <td className="px-4 py-3">{t.email}</td>
                      <td className="px-4 py-3">{t.is_admin ? "Yes" : "No"}</td>
                      <td className="px-4 py-3">{new Date(t.created_at).toLocaleString()}</td>
                      <td className="px-4 py-3 text-right space-x-2">
                        <Button variant="secondary" onClick={() => overview(t.id)}>Overview</Button>
                        <Button variant="secondary" onClick={() => resetPassword(t.id)}>Reset PW</Button>
                        <Button variant="secondary" onClick={() => impersonate(t.id)}>Impersonate</Button>
                        {t.is_active !== false ? (
                          <Button variant="secondary" onClick={() => deactivate(t.id)}>Deactivate</Button>
                        ) : (
                          <Button variant="secondary" onClick={() => reactivate(t.id)}>Reactivate</Button>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}


