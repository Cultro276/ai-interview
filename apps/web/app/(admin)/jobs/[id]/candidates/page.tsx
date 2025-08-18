"use client";
import { useState, useEffect } from "react";
import { useParams } from "next/navigation";
import { useDashboard } from "@/context/DashboardContext";
import { apiFetch } from "@/lib/api";
import { useToast } from "@/context/ToastContext";
import { Button } from "@/components/ui/Button";
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from "@/components/ui/dropdown-menu";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger, DialogDescription } from "@/components/ui/dialog";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Loader } from "@/components/ui/Loader";
import { EmptyState } from "@/components/ui/EmptyState";
import { Skeleton } from "@/components/ui/Skeleton";

export default function JobCandidatesPage() {
  const params = useParams();
  const jobId = Number(params?.id);
  const { candidates, interviews, loading, refreshData } = useDashboard();
  const { success, error: toastError, info } = useToast();
  const [files, setFiles] = useState<File[]>([]);
  const [uploading, setUploading] = useState(false);
  const [expiresDays, setExpiresDays] = useState(7);
  const [singleFile, setSingleFile] = useState<File | null>(null);
  const [singleName, setSingleName] = useState("");
  const [singleEmail, setSingleEmail] = useState("");
  const [creating, setCreating] = useState(false);
  const [singleExpiry, setSingleExpiry] = useState(7);
  const [presigning, setPresigning] = useState(false);

  const jobCandidateIds = interviews
    .filter((i) => i.job_id === jobId)
    .map((i) => i.candidate_id);
  const jobCandidates = candidates.filter((c) => jobCandidateIds.includes(c.id));
  const [search, setSearch] = useState("");

  const onUpload = async () => {
    if (!files.length) return;
    setUploading(true);
    try {
      const form = new FormData();
      files.forEach((f) => form.append("files", f));
      form.append("expires_in_days", String(expiresDays));
      await apiFetch(`/api/v1/jobs/${jobId}/candidates/bulk-upload`, {
        method: "POST",
        body: form,
      });
      await refreshData();
      success("Upload completed");
    } catch (e: any) {
      toastError(e.message || "Upload failed");
    } finally {
      setUploading(false);
    }
  };

  const isValidEmail = (email: string) => /.+@.+\..+/.test(email);

  const createSingleCandidate = async () => {
    if (!singleName || !singleEmail) {
      toastError("Name and Email are required");
      return;
    }
    if (!isValidEmail(singleEmail)) {
      toastError("Please enter a valid email address");
      return;
    }
    // Optional: If a CV file is selected, upload first and use the resulting key/url
    setCreating(true);
    try {
      let resumeUrl: string | undefined = undefined;
      if (singleFile) {
        setPresigning(true);
        // 1) Presign to cvs/{jobId}/...
        const presign = await apiFetch<{ url: string; key: string }>(`/api/v1/jobs/${jobId}/candidates/presign-cv`, {
          method: "POST",
          body: JSON.stringify({ file_name: singleFile.name, content_type: singleFile.type || "application/octet-stream" }),
        });
        // 2) Upload file to presigned URL
        await fetch(presign.url, { method: "PUT", body: singleFile, headers: { "Content-Type": singleFile.type || "application/octet-stream" } });
        // 3) Save the public/proxied location
        resumeUrl = `s3://${presign.key}`;
        setPresigning(false);
      }
      await apiFetch<any>(`/api/v1/jobs/${jobId}/candidates`, {
        method: "POST",
        body: JSON.stringify({ name: singleName, email: singleEmail, expires_in_days: singleExpiry, resume_url: resumeUrl }),
      });
      setSingleName("");
      setSingleEmail("");
      setSingleFile(null);
      await refreshData();
      success("Candidate created and linked to job");
    } catch (e: any) {
      toastError(e.message || "Create failed");
    } finally {
      setCreating(false);
    }
  };

  const sendLink = async (candId: number) => {
    try {
      await apiFetch(`/api/v1/candidates/${candId}/send-link?expires_in_days=${expiresDays}`, { method: "POST" });
      const { url } = await apiFetch<{ url: string }>(`/api/v1/candidates/${candId}/invite-link`);
      info(`Link sent. Click to open: ${url}`);
    } catch (e: any) {
      toastError(e.message);
    }
  };

  const sendAll = async () => {
    try {
      const ids = jobCandidates.map(c => c.id);
      // Batch in chunks of 10 to avoid burst
      for (let i = 0; i < ids.length; i += 10) {
        const batch = ids.slice(i, i + 10);
        await Promise.all(batch.map(id => apiFetch(`/api/v1/candidates/${id}/send-link?expires_in_days=${expiresDays}`, { method: "POST" })));
        info(`Sent ${Math.min(i + 10, ids.length)}/${ids.length}`);
      }
      info("All links sent");
    } catch (e: any) {
      toastError(e.message || "Failed to send all links");
    }
  };

  const downloadCv = async (candId: number) => {
    try {
      const { url } = await apiFetch<{ url: string }>(`/api/v1/candidates/${candId}/resume-download-url`);
      window.open(url, "_blank");
    } catch (e: any) {
      toastError(e.message || "Download failed");
    }
  };

  if (loading) {
    return (
      <div>
        <div className="flex items-center justify-between mb-6">
          <div className="h-8 w-56"><Skeleton className="h-8 w-56" /></div>
          <div className="h-5 w-24"><Skeleton className="h-9 w-24" /></div>
        </div>
        <div className="bg-white dark:bg-neutral-900 border border-gray-200 dark:border-neutral-800 rounded-lg p-6 mb-8">
          <div className="flex items-center justify-between mb-4">
            <Skeleton className="h-6 w-40" />
            <Skeleton className="h-9 w-40" />
          </div>
          <div className="grid gap-4 md:grid-cols-3">
            <Skeleton className="h-10" />
            <Skeleton className="h-10" />
            <Skeleton className="h-10" />
          </div>
        </div>
        <div className="bg-white dark:bg-neutral-900 border border-gray-200 dark:border-neutral-800 rounded-lg overflow-hidden">
          <div className="px-6 py-4 border-b border-gray-200 dark:border-neutral-800">
            <Skeleton className="h-6 w-64" />
          </div>
          <div className="p-6 space-y-3">
            {Array.from({ length: 5 }).map((_, i) => (
              <div key={i} className="grid grid-cols-4 gap-4">
                <Skeleton className="h-5" />
                <Skeleton className="h-5" />
                <Skeleton className="h-5" />
                <Skeleton className="h-9" />
              </div>
            ))}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-gray-900 dark:text-neutral-100">İş Adayları</h1>
        <a href="/jobs" className="text-brand-700">← İlanlara Geri Dön</a>
      </div>

      <div className="bg-white dark:bg-neutral-900 border border-gray-200 dark:border-neutral-800 rounded-lg p-6 mb-8">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-medium text-gray-900 dark:text-neutral-100">Toplu CV Yükleme</h3>
          <Dialog>
            <DialogTrigger asChild>
              <Button variant="outline">Send Links to All</Button>
            </DialogTrigger>
            <DialogContent>
              <DialogHeader>
                <DialogTitle>Davet Linki Gönder</DialogTitle>
                <DialogDescription>
                  Seçilen geçerlilik süresiyle bu ilana bağlı tüm adaylara davet linki göndereceksiniz.
                </DialogDescription>
              </DialogHeader>
              <div className="space-y-3">
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Link Süresi</label>
                  <Select value={String(expiresDays)} onValueChange={(v) => setExpiresDays(Number(v))}>
                    <SelectTrigger>
                      <SelectValue placeholder="Select" />
                    </SelectTrigger>
                    <SelectContent>
                      {[1,3,7,14,30].map((d) => (
                        <SelectItem key={d} value={String(d)}>{d} gün</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <Button onClick={sendAll}>Tümüne Gönder</Button>
              </div>
            </DialogContent>
          </Dialog>
        </div>
        <div className="grid gap-4 md:grid-cols-3">
          <div className="md:col-span-2">
            <input type="file" multiple accept=".pdf,.doc,.docx,.txt" onChange={(e) => setFiles(Array.from(e.target.files || []))} className="block w-full text-sm text-gray-600 dark:text-gray-300" />
            {files.length > 0 && (<p className="text-sm text-gray-500 dark:text-gray-300 mt-2">{files.length} dosya seçildi</p>)}
          </div>
          <div className="flex items-end">
            <Button onClick={onUpload} disabled={uploading || files.length === 0}>
              {uploading ? "Yükleniyor…" : "Yükle & Ayrıştır"}
            </Button>
          </div>
        </div>
      </div>

      <div className="bg-white dark:bg-neutral-900 border border-gray-200 dark:border-neutral-800 rounded-lg p-6 mb-8">
        <h3 className="text-lg font-medium text-gray-900 dark:text-neutral-100 mb-4">Tekil Aday Oluştur</h3>
        <div className="grid gap-4 md:grid-cols-3">
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Ad Soyad</label>
            <input
              value={singleName}
              onChange={(e) => setSingleName(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md"
              placeholder="Furkan Ünal"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">E-posta</label>
            <input
              type="email"
              value={singleEmail}
              onChange={(e) => setSingleEmail(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md"
              placeholder="furkan@example.com"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Geçerlilik (gün)</label>
            <input
              type="number"
              min={1}
              max={365}
              value={singleExpiry}
              onChange={(e) => setSingleExpiry(Number(e.target.value))}
              className="w-full px-3 py-2 border border-gray-300 rounded-md"
            />
          </div>
          <div className="md:col-span-1">
            <label className="block text-sm font-medium text-gray-700 mb-1">Upload CV (optional)</label>
            <input type="file" accept=".pdf,.doc,.docx,.txt" onChange={(e) => setSingleFile((e.target.files && e.target.files[0]) || null)} className="block w-full text-sm text-gray-600" />
            {singleFile && <p className="text-xs text-gray-500 mt-1">{singleFile.name}</p>}
          </div>
        </div>
        <div className="flex gap-3 mt-4">
          <Button onClick={createSingleCandidate} disabled={creating}>
            {creating ? (presigning ? "CV yükleniyor…" : "Oluşturuluyor…") : "Aday Oluştur"}
          </Button>
        </div>
      </div>

      <div className="bg-white dark:bg-neutral-900 border border-gray-200 dark:border-neutral-800 rounded-lg overflow-hidden">
        <div className="px-6 py-4 border-b border-gray-200 dark:border-neutral-800 flex items-center gap-4">
          <h3 className="text-lg font-medium text-gray-900 dark:text-neutral-100">Bu İlanın Adayları</h3>
          <div className="ml-auto w-full max-w-xs">
            <input
              placeholder="Ad veya e-posta ile ara"
              aria-label="Aday ara"
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-600"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
          </div>
        </div>
        {jobCandidates.length === 0 ? (
          <EmptyState title="Henüz aday yok" description="CV yükleyin veya aday oluşturarak davet göndermeye başlayın." />
        ) : (
        <div className="w-full overflow-x-auto">
        <table className="min-w-full divide-y divide-gray-200 dark:divide-neutral-800">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">Ad Soyad</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">E-posta</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">Özgeçmiş</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">İşlemler</th>
            </tr>
          </thead>
          <tbody className="bg-white dark:bg-neutral-900 divide-y divide-gray-200 dark:divide-neutral-800">
            {jobCandidates
              .filter((c) => {
                const q = search.trim().toLowerCase();
                if (!q) return true;
                return (
                  (c.name || "").toLowerCase().includes(q) ||
                  (c.email || "").toLowerCase().includes(q)
                );
              })
              .map((c) => (
              <tr key={c.id} className="hover:bg-gray-50 dark:hover:bg-neutral-800">
                <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900 dark:text-neutral-100">{c.name}</td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-300">{c.email}</td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-300">
                  {c.resume_url ? (
                    <Button variant="ghost" onClick={() => downloadCv(c.id)} className="text-brand-700 hover:text-brand-900 p-0 h-auto">CV'yi Gör</Button>
                  ) : (
                    <span className="text-gray-400">—</span>
                  )}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm font-medium">
                  <DropdownMenu>
                    <DropdownMenuTrigger asChild>
                      <Button variant="outline">İşlemler</Button>
                    </DropdownMenuTrigger>
                    <DropdownMenuContent align="end">
                      <DropdownMenuItem onClick={() => sendLink(c.id)}>Davet Gönder</DropdownMenuItem>
                      {c.resume_url && (
                        <DropdownMenuItem onClick={() => downloadCv(c.id)}>CV'yi Gör</DropdownMenuItem>
                      )}
                    </DropdownMenuContent>
                  </DropdownMenu>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        </div>
        )}
      </div>
    </div>
  );
} 