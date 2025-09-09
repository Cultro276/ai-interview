"use client";
import { useEffect, useState } from "react";
import { apiFetch } from "@/lib/api";
import { Card, CardContent, CardHeader, Button, Input, Select, SelectTrigger, SelectValue, SelectContent, SelectItem } from "@/components/ui";

type Tenant = { id: number; email: string; is_admin: boolean; is_active?: boolean; created_at: string; company_name?: string };

export default function InternalAdmin() {
  // Do not render in production unless the path is known; no link is provided anywhere.
  const [tenants, setTenants] = useState<Tenant[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  
  // Auto-setup founders secret if missing
  useEffect(() => {
    if (typeof window !== 'undefined') {
      const foundersSecret = localStorage.getItem('founders_secret');
      if (!foundersSecret) {
        localStorage.setItem('founders_secret', 'dev-internal-secret-change-in-production-super-secure');
        console.log('✅ Founders secret automatically configured');
      }
    }
  }, []);
  const [creating, setCreating] = useState(false);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [companyName, setCompanyName] = useState("");
  // Activity filters/state
  const [actOwnerId, setActOwnerId] = useState<number | null>(null);
  const [actType, setActType] = useState<string>("all");
  const [actLimit, setActLimit] = useState<number>(50);
  const [actLogs, setActLogs] = useState<Array<{timestamp:string; event_type:string; message:string}> | null>(null);
  const [actQ, setActQ] = useState<string>("");
  const [actStart, setActStart] = useState<string>("");
  const [actEnd, setActEnd] = useState<string>("");
  
  // Company name editing state
  const [editingTenant, setEditingTenant] = useState<number | null>(null);
  const [editCompanyName, setEditCompanyName] = useState<string>("");

  const load = async () => {
    setLoading(true);
    try {
      // Debug: Check if secret is set before API call
      const secret = localStorage.getItem('founders_secret');
      console.log('🔍 Debug - founders_secret:', secret ? 'SET' : 'MISSING');
      
      const data = await apiFetch<Tenant[]>("/api/v1/internal/tenants");
      setTenants(data);
      setError(null); // Clear any previous errors
    } catch (e: any) {
      console.error('❌ Internal API Error:', e);
      if (e.message.includes('Forbidden') || e.message.includes('403')) {
        const secret = localStorage.getItem('founders_secret');
        setError(`❌ Erişim reddedildi. Secret durumu: ${secret ? 'MEVCUT' : 'EKSİK'}. Token durumu: ${localStorage.getItem('token') ? 'MEVCUT' : 'EKSİK'}`);
      } else {
        setError(e.message || "Failed to load tenants");
      }
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
  const activity = async (ownerId: number) => {
    try {
      setActOwnerId(ownerId);
      const params = new URLSearchParams();
      params.set('limit', String(actLimit));
      if (actQ.trim()) params.set('q', actQ.trim());
      if (actType !== 'all') params.set('etype', actType);
      if (actStart) params.set('start', actStart);
      if (actEnd) params.set('end', actEnd);
      const logs = await apiFetch<Array<{timestamp:string; event_type:string; message:string}>>(`/api/v1/internal/tenant/${ownerId}/activity?${params.toString()}`);
      setActLogs(logs);
    } catch (e:any) {
      alert(e?.message || 'Aktivite alınamadı');
    }
  };
  const createOwner = async () => {
    setCreating(true);
    try {
      await apiFetch(`/api/v1/internal/tenant`, { method: "POST", body: JSON.stringify({ email, password, company_name: companyName || undefined }) });
      setEmail(""); setPassword(""); setCompanyName("");
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
  
  const startEditCompany = (tenant: Tenant) => {
    setEditingTenant(tenant.id);
    setEditCompanyName(tenant.company_name || '');
  };
  
  const saveCompanyName = async (ownerId: number) => {
    try {
      await apiFetch(`/api/v1/internal/tenant/${ownerId}`, { 
        method: "PATCH", 
        body: JSON.stringify({ company_name: editCompanyName || null }) 
      });
      setEditingTenant(null);
      setEditCompanyName('');
      await load();
    } catch (e: any) {
      alert(e.message || "Failed to update company name");
    }
  };
  
  const cancelEdit = () => {
    setEditingTenant(null);
    setEditCompanyName('');
  };

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">Kurucular Konsolu</h1>
      {error && (
        <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4 mb-4">
          <div className="text-sm text-red-600 dark:text-red-400 mb-2">{error}</div>
          {error.includes('Erişim reddedildi') && (
            <div className="text-xs text-red-500 dark:text-red-400 space-y-2">
              <div>💡 <strong>Çözüm:</strong> Browser konsolunda <code>localStorage.setItem(&quot;founders_secret&quot;,&quot;dev-internal-secret-change-in-production-super-secure&quot;)</code> komutunu çalıştırın.</div>
              <button 
                onClick={() => {
                  localStorage.setItem("founders_secret","dev-internal-secret-change-in-production-super-secure");
                  console.log('✅ Founders secret set manually');
                  setTimeout(load, 100); // Retry after a short delay
                }}
                className="px-3 py-1 text-xs bg-blue-600 text-white rounded hover:bg-blue-700"
              >
                🔧 Secret&rsquo;ı Ayarla ve Tekrar Dene
              </button>
            </div>
          )}
        </div>
      )}
      <Card className="bg-white dark:bg-neutral-900 border border-neutral-200 dark:border-neutral-800">
        <CardHeader>
          <div className="flex items-center justify-between">
            <h3 className="text-lg font-semibold">Kiracılar</h3>
            <div className="flex items-center gap-2">
              <Button onClick={load}>Yenile</Button>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <div className="mb-4 grid grid-cols-1 md:grid-cols-4 gap-3">
            <Input placeholder="Sahip e‑postası" value={email} onChange={(e)=>setEmail(e.target.value)} />
            <Input placeholder="Geçici şifre" value={password} type="password" onChange={(e)=>setPassword(e.target.value)} />
            <Input placeholder="Şirket Adı" value={companyName} onChange={(e)=>setCompanyName(e.target.value)} />
            <div>
              <Button onClick={createOwner} disabled={creating || !email || !password}>Sahip oluştur</Button>
            </div>
          </div>
          {loading ? (
            <div>Yükleniyor...</div>
          ) : (
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200 dark:divide-neutral-800 text-sm">
                <thead>
                  <tr>
                    <th className="px-4 py-2 text-left">ID</th>
                    <th className="px-4 py-2 text-left">E‑posta</th>
                    <th className="px-4 py-2 text-left">Şirket</th>
                    <th className="px-4 py-2 text-left">Sahip?</th>
                    <th className="px-4 py-2 text-left">Oluşturma</th>
                    <th className="px-4 py-2"></th>
                  </tr>
                </thead>
                <tbody>
                  {tenants.map(t => (
                    <tr key={t.id} className="border-b border-gray-200 dark:border-neutral-800">
                      <td className="px-4 py-3">{t.id}</td>
                      <td className="px-4 py-3">{t.email}</td>
                      <td className="px-4 py-3">
                        {editingTenant === t.id ? (
                          <div className="flex items-center gap-2">
                            <Input 
                              value={editCompanyName} 
                              onChange={(e) => setEditCompanyName(e.target.value)}
                              placeholder="Şirket adı"
                              className="h-8 text-sm"
                            />
                            <Button 
                              size="sm" 
                              onClick={() => saveCompanyName(t.id)}
                              className="h-8 px-2"
                            >
                              ✓
                            </Button>
                            <Button 
                              size="sm" 
                              variant="ghost" 
                              onClick={cancelEdit}
                              className="h-8 px-2"
                            >
                              ✗
                            </Button>
                          </div>
                        ) : (
                          <div className="flex items-center gap-2">
                            <span className="text-sm">{t.company_name || '—'}</span>
                            <Button 
                              size="sm" 
                              variant="ghost" 
                              onClick={() => startEditCompany(t)}
                              className="h-6 px-1 text-xs"
                            >
                              ✏️
                            </Button>
                          </div>
                        )}
                      </td>
                      <td className="px-4 py-3">{t.is_admin ? "Evet" : "Hayır"}</td>
                      <td className="px-4 py-3">{new Date(t.created_at).toLocaleString('tr-TR')}</td>
                      <td className="px-4 py-3 text-right space-x-2">
                        <Button variant="secondary" onClick={() => overview(t.id)}>Genel Bakış</Button>
                        <Button variant="secondary" onClick={() => activity(t.id)}>Aktivite</Button>
                        <Button variant="secondary" onClick={() => resetPassword(t.id)}>Şifre Sıfırla</Button>
                        <Button variant="secondary" onClick={() => impersonate(t.id)}>Taklit et</Button>
                        {t.is_active !== false ? (
                          <Button variant="secondary" onClick={() => deactivate(t.id)}>Devre dışı bırak</Button>
                        ) : (
                          <Button variant="secondary" onClick={() => reactivate(t.id)}>Yeniden etkinleştir</Button>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
          {actLogs && (
            <div className="mt-6 border-t border-neutral-200 dark:border-neutral-800 pt-4">
              <div className="flex flex-wrap items-center gap-3 mb-3">
                <div className="text-sm text-gray-700 dark:text-gray-300">Hesap: {actOwnerId}</div>
                <Select value={actType} onValueChange={setActType as any}>
                  <SelectTrigger className="w-[220px]"><SelectValue placeholder="Olay türü" /></SelectTrigger>
                  <SelectContent>
                    {['all','job','candidate','interview','file','auth','data'].map(v => (
                      <SelectItem key={v} value={v}>{v}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                <Select value={String(actLimit)} onValueChange={(v)=> setActLimit(Number(v))}>
                  <SelectTrigger className="w-[120px]"><SelectValue placeholder="Limit" /></SelectTrigger>
                  <SelectContent>
                    {[20,50,100,200].map(v => (<SelectItem key={v} value={String(v)}>{v}</SelectItem>))}
                  </SelectContent>
                </Select>
                <Input placeholder="Ara (mesaj/olay)" value={actQ} onChange={(e)=> setActQ(e.target.value)} />
                <div className="flex items-center gap-2">
                  <label className="text-xs text-gray-500">Başlangıç</label>
                  <Input type="datetime-local" value={actStart} onChange={(e)=> setActStart(e.target.value)} />
                </div>
                <div className="flex items-center gap-2">
                  <label className="text-xs text-gray-500">Bitiş</label>
                  <Input type="datetime-local" value={actEnd} onChange={(e)=> setActEnd(e.target.value)} />
                </div>
                <Button onClick={() => { if (actOwnerId) activity(actOwnerId); }}>Filtrele</Button>
                <Button variant="outline" onClick={() => setActLogs(null)}>Kapat</Button>
              </div>
              <div className="max-h-[50vh] overflow-y-auto text-sm">
                {actLogs.length === 0 ? (
                  <div className="text-gray-500">Kayıt yok</div>
                ) : (
                  <ul className="space-y-1">
                    {actLogs.map((l, i) => (
                      <li key={i} className="flex items-center justify-between border-b border-neutral-200 dark:border-neutral-800 py-1">
                        <span className="text-gray-500 w-48">{new Date(l.timestamp).toLocaleString('tr-TR')}</span>
                        <span className="text-gray-700 dark:text-gray-300 flex-1 px-3">{l.message}</span>
                        <span className="text-xs px-2 py-0.5 rounded-full bg-gray-100 dark:bg-neutral-800 text-gray-600 dark:text-gray-300 border border-gray-200 dark:border-neutral-700">{l.event_type}</span>
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}


