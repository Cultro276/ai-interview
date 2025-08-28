"use client";
import { useEffect, useState } from "react";
import { apiFetch } from "@/lib/api";
import { Button } from "@/components/ui/Button";
import { Card, CardContent, CardHeader } from "@/components/ui/Card";
import { Input } from "@/components/ui/Input";
import { useRouter } from "next/navigation";

type Member = {
  id: number;
  email: string;
  first_name?: string | null;
  last_name?: string | null;
  is_admin: boolean;
  owner_user_id?: number | null;
  role?: string | null;
  can_manage_jobs: boolean;
  can_manage_candidates: boolean;
  can_view_interviews: boolean;
  can_manage_members: boolean;
  is_active: boolean;
};

export default function TeamPage() {
  const router = useRouter();
  const [members, setMembers] = useState<Member[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = async () => {
    setLoading(true);
    try {
      const res = await apiFetch<Member[]>("/api/v1/team/members");
      setMembers(res);
    } catch (e: any) {
      setError(e.message || "Failed to load team");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []);

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold">Ekip</h1>
        <div className="flex items-center gap-2">
          <CreateMember onCreated={load} />
          <LogoutButton onLogout={() => router.replace("/login")} />
        </div>
      </div>
      {error && <div className="text-red-600 mb-4 text-sm">{error}</div>}
      <Card className="bg-white dark:bg-neutral-900 border border-neutral-200 dark:border-neutral-800">
        <CardHeader>
          <h3 className="text-lg font-semibold">Üyeler</h3>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div>Yükleniyor...</div>
          ) : (
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200 dark:divide-neutral-800 text-sm">
                <thead className="bg-gray-50 dark:bg-neutral-900">
                  <tr>
                    <th className="px-4 py-2 text-left">Kullanıcı</th>
                    <th className="px-4 py-2 text-left">Rol</th>
                    <th className="px-4 py-2 text-left">İşler</th>
                    <th className="px-4 py-2 text-left">Adaylar</th>
                    <th className="px-4 py-2 text-left">Mülakatlar</th>
                    <th className="px-4 py-2 text-left">Üyeler</th>
                    <th className="px-4 py-2"></th>
                  </tr>
                </thead>
                <tbody>
                  {members.map((m) => (
                    <MemberRow key={m.id} member={m} onChanged={load} />
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

function MemberRow({ member, onChanged }: { member: Member; onChanged: () => Promise<void> }) {
  const [saving, setSaving] = useState(false);
  const toggle = async (field: keyof Member) => {
    setSaving(true);
    try {
      await apiFetch(`/api/v1/team/members/${member.id}`, {
        method: "PUT",
        body: JSON.stringify({ [field]: !member[field] }),
      });
      await onChanged();
    } catch {}
    setSaving(false);
  };
  const del = async () => {
    setSaving(true);
    try {
      await apiFetch(`/api/v1/team/members/${member.id}`, { method: "DELETE" });
      await onChanged();
    } catch {}
    setSaving(false);
  };
  return (
    <tr className="border-b border-gray-200 dark:border-neutral-800">
      <td className="px-4 py-3">
        <div className="font-medium">{member.first_name || member.last_name ? `${member.first_name || ""} ${member.last_name || ""}`.trim() : member.email}</div>
        <div className="text-gray-500 text-xs">{member.email}</div>
      </td>
      <td className="px-4 py-3">{member.is_admin ? "Sahip/Yönetici" : (member.role || "Asistan")}</td>
      <td className="px-4 py-3">
        <Toggle value={member.is_admin || member.owner_user_id == null ? true : member.can_manage_jobs} onChange={() => toggle("can_manage_jobs")} disabled={member.is_admin || member.owner_user_id == null} />
      </td>
      <td className="px-4 py-3">
        <Toggle value={member.is_admin || member.owner_user_id == null ? true : member.can_manage_candidates} onChange={() => toggle("can_manage_candidates")} disabled={member.is_admin || member.owner_user_id == null} />
      </td>
      <td className="px-4 py-3">
        <Toggle value={member.is_admin || member.owner_user_id == null ? true : member.can_view_interviews} onChange={() => toggle("can_view_interviews")} disabled={member.is_admin || member.owner_user_id == null} />
      </td>
      <td className="px-4 py-3">
        <Toggle value={member.is_admin || member.owner_user_id == null ? true : member.can_manage_members} onChange={() => toggle("can_manage_members")} disabled={member.is_admin || member.owner_user_id == null} />
      </td>
      <td className="px-4 py-3 text-right space-x-2">
        {!member.is_admin && (
          <Button variant="secondary" onClick={del} disabled={saving}>Kaldır</Button>
        )}
      </td>
    </tr>
  );
}

function Toggle({ value, onChange, disabled }: { value: boolean; onChange: () => void; disabled?: boolean }) {
  return (
    <button
      onClick={onChange}
      disabled={disabled}
      className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors focus:outline-none ${value ? "bg-green-500" : "bg-red-500"}`}
    >
      <span
        className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${value ? "translate-x-6" : "translate-x-1"}`}
      />
    </button>
  );
}

function CreateMember({ onCreated }: { onCreated: () => Promise<void> }) {
  const [open, setOpen] = useState(false);
  const [saving, setSaving] = useState(false);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [firstName, setFirstName] = useState("");
  const [lastName, setLastName] = useState("");
  const [role, setRole] = useState("");
  const [perms, setPerms] = useState({ jobs: true, candidates: true, interviews: true, members: false });

  const submit = async () => {
    setSaving(true);
    try {
      await apiFetch("/api/v1/team/members", {
        method: "POST",
        body: JSON.stringify({
          email,
          password,
          first_name: firstName || undefined,
          last_name: lastName || undefined,
          role: role || undefined,
          can_manage_jobs: perms.jobs,
          can_manage_candidates: perms.candidates,
          can_view_interviews: perms.interviews,
          can_manage_members: perms.members,
        }),
      });
      setOpen(false);
      setEmail("");
      setPassword("");
      setFirstName("");
      setLastName("");
      setRole("");
      setPerms({ jobs: true, candidates: true, interviews: true, members: false });
      await onCreated();
    } catch {}
    setSaving(false);
  };

  return (
    <div>
      <Button onClick={() => setOpen(true)}>Üye Ekle</Button>
      {open && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30">
          <div className="bg-white dark:bg-neutral-900 rounded-lg border border-neutral-200 dark:border-neutral-800 w-full max-w-lg p-6">
            <h3 className="text-lg font-semibold mb-4">Üye Oluştur</h3>
            <div className="grid grid-cols-1 gap-4">
              <Input placeholder="E‑posta" value={email} onChange={(e) => setEmail(e.target.value)} />
              <Input placeholder="Geçici Parola" type="password" value={password} onChange={(e) => setPassword(e.target.value)} />
              <div className="grid grid-cols-2 gap-4">
                <Input placeholder="Ad" value={firstName} onChange={(e) => setFirstName(e.target.value)} />
                <Input placeholder="Soyad" value={lastName} onChange={(e) => setLastName(e.target.value)} />
              </div>
              <Input placeholder="Rol (opsiyonel)" value={role} onChange={(e) => setRole(e.target.value)} />
              <div className="grid grid-cols-2 gap-4 mt-2">
                <LabeledToggle label="İlanları yönet" value={perms.jobs} onChange={() => setPerms(p => ({ ...p, jobs: !p.jobs }))} />
                <LabeledToggle label="Adayları yönet" value={perms.candidates} onChange={() => setPerms(p => ({ ...p, candidates: !p.candidates }))} />
                <LabeledToggle label="Mülakatları görüntüle" value={perms.interviews} onChange={() => setPerms(p => ({ ...p, interviews: !p.interviews }))} />
                <LabeledToggle label="Üyeleri yönet" value={perms.members} onChange={() => setPerms(p => ({ ...p, members: !p.members }))} />
              </div>
              <div className="flex justify-end gap-2 mt-4">
                <Button variant="secondary" onClick={() => setOpen(false)}>İptal</Button>
                <Button onClick={submit} disabled={saving || !email || !password}>Oluştur</Button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function LabeledToggle({ label, value, onChange }: { label: string; value: boolean; onChange: () => void }) {
  return (
    <div className="flex items-center justify-between py-2">
      <span className="text-sm">{label}</span>
      <Toggle value={value} onChange={onChange} />
    </div>
  );
}

function LogoutButton({ onLogout }: { onLogout: () => void }) {
  const [working, setWorking] = useState(false);
  const doLogout = () => {
    setWorking(true);
    try {
      if (typeof window !== "undefined") {
        localStorage.removeItem("token");
      }
    } catch {}
    onLogout();
    setWorking(false);
  };
  return (
    <Button variant="secondary" onClick={doLogout} disabled={working}>Çıkış Yap</Button>
  );
}


