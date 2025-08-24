"use client";
import { useState, useEffect, useRef, useMemo } from "react";
import { useParams, useSearchParams, useRouter } from "next/navigation";
import { useDashboard } from "@/context/DashboardContext";
import { apiFetch } from "@/lib/api";
import { useToast } from "@/context/ToastContext";
import { Button } from "@/components/ui/Button";
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from "@/components/ui/dropdown-menu";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger, DialogDescription, DialogClose } from "@/components/ui/dialog";
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

  const jobInterviews = interviews.filter((i) => i.job_id === jobId);
  const jobCandidateIds = jobInterviews.map((i) => i.candidate_id);
  const jobCandidates = candidates.filter((c) => jobCandidateIds.includes(c.id));
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState<"all" | "completed" | "pending">("all");
  const [hasCvOnly, setHasCvOnly] = useState(false);
  const [hasMediaOnly, setHasMediaOnly] = useState(false);
  const [dateFrom, setDateFrom] = useState<string>("");
  const [dateTo, setDateTo] = useState<string>("");
  const [minDurationMin, setMinDurationMin] = useState<string>("");
  const [maxDurationMin, setMaxDurationMin] = useState<string>("");
  const [sortBy, setSortBy] = useState<
    | "created"
    | "score"
    | "last_update_desc"
    | "last_update_asc"
    | "duration_desc"
    | "duration_asc"
  >("score");
  const [pageNum, setPageNum] = useState<number>(1);

  // URL params <-> state sync
  const sp = useSearchParams();
  const router = useRouter();
  const didInitFromUrlRef = useRef(false);

  // 1) On mount: initialize state from URL once
  useEffect(() => {
    if (didInitFromUrlRef.current) return;
    const get = (k: string) => sp.get(k);
    const truthy = (v: string | null) => v === "1" || v === "true";
    const q = get("q");
    const statusP = get("status") as any;
    const cv = get("cv");
    const media = get("media");
    const from = get("from");
    const to = get("to");
    const minD = get("minDur");
    const maxD = get("maxDur");
    const sortP = get("sort") as any;
    const pageP = parseInt(get("page") || "1", 10);

    if (q !== null) setSearch(q);
    if (statusP && ["all","completed","pending"].includes(statusP)) setStatusFilter(statusP);
    if (cv !== null) setHasCvOnly(truthy(cv));
    if (media !== null) setHasMediaOnly(truthy(media));
    if (from !== null) setDateFrom(from);
    if (to !== null) setDateTo(to);
    if (minD !== null) setMinDurationMin(minD);
    if (maxD !== null) setMaxDurationMin(maxD);
    if (sortP && [
      "created","score","last_update_desc","last_update_asc","duration_desc","duration_asc"
    ].includes(sortP)) setSortBy(sortP);
    if (!isNaN(pageP) && pageP > 0) setPageNum(pageP);

    didInitFromUrlRef.current = true;
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // 2) Whenever filters change, reflect into URL
  useEffect(() => {
    if (!didInitFromUrlRef.current) return;
    const params = new URLSearchParams();
    if (search.trim()) params.set("q", search.trim());
    if (statusFilter !== "all") params.set("status", statusFilter);
    if (hasCvOnly) params.set("cv", "1");
    if (hasMediaOnly) params.set("media", "1");
    if (dateFrom) params.set("from", dateFrom);
    if (dateTo) params.set("to", dateTo);
    if (minDurationMin) params.set("minDur", String(minDurationMin));
    if (maxDurationMin) params.set("maxDur", String(maxDurationMin));
    if (sortBy !== "created") params.set("sort", sortBy);
    if (pageNum !== 1) params.set("page", String(pageNum));

    const qs = params.toString();
    const path = typeof window !== 'undefined' ? window.location.pathname : `/jobs/${jobId}/candidates`;
    router.replace(qs ? `${path}?${qs}` : path, { scroll: false });
  }, [search, statusFilter, hasCvOnly, hasMediaOnly, dateFrom, dateTo, minDurationMin, maxDurationMin, sortBy, pageNum, jobId, router]);

  // Report modal state
  const [reportOpen, setReportOpen] = useState(false);
  const [reportLoading, setReportLoading] = useState(false);
  const [reportAnalysis, setReportAnalysis] = useState<any | null>(null);
  const [reportInterviewId, setReportInterviewId] = useState<number | null>(null);
  // Invite link modal state
  const [inviteOpen, setInviteOpen] = useState(false);
  const [inviteUrl, setInviteUrl] = useState<string | null>(null);
  const [inviteLoading, setInviteLoading] = useState(false);

  const findLatestInterviewId = (candidateId: number): number | null => {
    const list = jobInterviews.filter((i) => i.candidate_id === candidateId);
    if (list.length === 0) return null;
    // pick the newest by created_at
    const sorted = [...list].sort((a: any, b: any) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime());
    return sorted[0].id;
  };
  const findLatestInterview = (candidateId: number) => {
    const list = jobInterviews.filter((i) => i.candidate_id === candidateId);
    if (list.length === 0) return null as any;
    return [...list].sort((a: any, b: any) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())[0];
  };
  const formatDuration = (startIso?: string, endIso?: string) => {
    if (!startIso || !endIso) return "—";
    const ms = new Date(endIso).getTime() - new Date(startIso).getTime();
    if (!isFinite(ms) || ms <= 0) return "—";
    const totalSec = Math.floor(ms / 1000);
    const h = Math.floor(totalSec / 3600);
    const m = Math.floor((totalSec % 3600) / 60);
    const s = totalSec % 60;
    const pad = (n: number) => String(n).padStart(2, '0');
    return (h > 0 ? pad(h) + ":" : "") + pad(m) + ":" + pad(s);
  };

  const [videoOpen, setVideoOpen] = useState(false);
  const [videoSrc, setVideoSrc] = useState<string | null>(null);
  const [audioSrc, setAudioSrc] = useState<string | null>(null);
  const openVideoForCandidate = async (candId: number) => {
    try {
      const intId = findLatestInterviewId(candId);
      if (!intId) return toastError("Bu aday için mülakat bulunamadı");
      const { audio_url, video_url } = await apiFetch<{ audio_url?: string; video_url?: string }>(`/api/v1/interviews/${intId}/media-download-urls`);
      setVideoSrc(video_url || null);
      setAudioSrc(audio_url || null);
      if (!video_url && !audio_url) return toastError("Medya bulunamadı");
      setVideoOpen(true);
    } catch (e: any) {
      toastError(e.message || "Medya açılamadı");
    }
  };

  const openReportForCandidate = async (candId: number) => {
    const intId = findLatestInterviewId(candId);
    if (!intId) return toastError("Bu aday için mülakat bulunamadı");
    setReportInterviewId(intId);
    setReportLoading(true);
    setReportOpen(true);
    try {
      const data = await apiFetch<any>(`/api/v1/conversations/analysis/${intId}`);
      setReportAnalysis(data);
    } catch (e: any) {
      setReportAnalysis(null);
      toastError(e.message || "Rapor yüklenemedi");
    } finally {
      setReportLoading(false);
    }
  };

  // Inline component definitions must be before return; define TranscriptBlock here
  const TranscriptBlock = ({ interviewId }: { interviewId: number }) => {
    const [text, setText] = useState<string | null>(null);
    const [loadingT, setLoadingT] = useState(false);
    const [errT, setErrT] = useState<string | null>(null);
    useEffect(() => {
      let mounted = true;
      setLoadingT(true);
      apiFetch<{ text: string }>(`/api/v1/interviews/${interviewId}/transcript`)
        .then((res) => { if (mounted) setText(res.text || ""); })
        .catch((e:any) => { if (mounted) setErrT(e.message || "Transkript alınamadı"); })
        .finally(() => { if (mounted) setLoadingT(false); });
      return () => { mounted = false; };
    }, [interviewId]);
    if (loadingT) return <div className="py-3 text-sm text-gray-500">Yükleniyor…</div>;
    if (errT) return <div className="py-3 text-sm text-rose-600">{errT}</div>;
    if (!text) return <div className="py-3 text-sm text-gray-500">Transkript yok</div>;
    return (
      <pre className="mt-2 whitespace-pre-wrap text-sm bg-gray-50 p-3 rounded border border-gray-200 max-h-[40vh] overflow-y-auto">{text}</pre>
    );
  };
  
  // (removed duplicate TranscriptBlock definition)
  // Scorecard UI kaldırıldı

  const exportReportPdf = () => {
    // Simple client-side print for now; can be replaced with server-side Puppeteer
    try {
      window.print();
    } catch {}
  };

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
        // 3) Save S3 key directly; backend presigns on demand
        resumeUrl = presign.key;
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

  const viewCv = async (candId: number) => {
    try {
      const { url } = await apiFetch<{ url: string }>(`/api/v1/candidates/${candId}/resume-download-url`);
      window.open(url, "_blank", "noopener,noreferrer");
    } catch (e: any) {
      toastError(e.message || "Open failed");
    }
  };

  const openInviteLinkForCandidate = async (candId: number) => {
    try {
      setInviteLoading(true);
      setInviteOpen(true);
      const { url } = await apiFetch<{ url: string }>(`/api/v1/candidates/${candId}/invite-link`);
      setInviteUrl(url);
    } catch (e: any) {
      setInviteUrl(null);
      toastError(e.message || "Link alınamadı");
    } finally {
      setInviteLoading(false);
    }
  };

  // Removed explicit download; browser preview allows easy download already

  // Compute filtered and sorted candidates to derive pagination bounds
  const filteredSortedCandidates = useMemo(() => {
    return jobCandidates
      .filter((c) => {
        const q = search.trim().toLowerCase();
        if (!q) return true;
        return (
          (c.name || "").toLowerCase().includes(q) ||
          (c.email || "").toLowerCase().includes(q)
        );
      })
      .filter((c) => {
        const it = findLatestInterview(c.id) as any;
        if (statusFilter !== "all") {
          if (!it || it.status !== statusFilter) return false;
        }
        if (hasCvOnly && !c.resume_url) return false;
        if (hasMediaOnly) {
          if (!it || (!it.audio_url && !it.video_url)) return false;
        }
        const lastIso = it?.completed_at || it?.created_at;
        if (dateFrom) {
          if (!lastIso || new Date(lastIso) < new Date(dateFrom)) return false;
        }
        if (dateTo) {
          if (!lastIso || new Date(lastIso) > new Date(dateTo + "T23:59:59")) return false;
        }
        const minM = minDurationMin ? Number(minDurationMin) : null;
        const maxM = maxDurationMin ? Number(maxDurationMin) : null;
        if (minM !== null || maxM !== null) {
          if (!it || !it.created_at || !it.completed_at) return false;
          const ms = new Date(it.completed_at).getTime() - new Date(it.created_at).getTime();
          const durMin = ms > 0 ? ms / 60000 : 0;
          if (minM !== null && durMin < minM) return false;
          if (maxM !== null && durMin > maxM) return false;
        }
        return true;
      })
      .sort((a, b) => {
        if (sortBy === "created") return 0;
        const itA = findLatestInterview(a.id) as any;
        const itB = findLatestInterview(b.id) as any;
        if (sortBy === "score") {
          const scoreA = itA?.overall_score || 0;
          const scoreB = itB?.overall_score || 0;
          return scoreB - scoreA;
        }
        if (sortBy === "last_update_desc" || sortBy === "last_update_asc") {
          const lastA = itA?.completed_at || itA?.created_at || null;
          const lastB = itB?.completed_at || itB?.created_at || null;
          const tA = lastA ? new Date(lastA).getTime() : 0;
          const tB = lastB ? new Date(lastB).getTime() : 0;
          return sortBy === "last_update_desc" ? tB - tA : tA - tB;
        }
        if (sortBy === "duration_desc" || sortBy === "duration_asc") {
          const hasA = itA?.created_at && itA?.completed_at;
          const hasB = itB?.created_at && itB?.completed_at;
          const dA = hasA ? (new Date(itA.completed_at).getTime() - new Date(itA.created_at).getTime()) : null;
          const dB = hasB ? (new Date(itB.completed_at).getTime() - new Date(itB.created_at).getTime()) : null;
          const normA = dA === null ? (sortBy === "duration_desc" ? -1 : Number.MAX_SAFE_INTEGER) : dA;
          const normB = dB === null ? (sortBy === "duration_desc" ? -1 : Number.MAX_SAFE_INTEGER) : dB;
          return sortBy === "duration_desc" ? normB - normA : normA - normB;
        }
        return 0;
      })
      .slice(0, 1000);
  }, [jobCandidates, search, statusFilter, hasCvOnly, hasMediaOnly, dateFrom, dateTo, minDurationMin, maxDurationMin, sortBy]);

  const totalPages = Math.max(1, Math.ceil(filteredSortedCandidates.length / 10));

  // Clamp current page within [1, totalPages]
  useEffect(() => {
    if (pageNum < 1) setPageNum(1);
    else if (pageNum > totalPages) setPageNum(totalPages);
  }, [pageNum, totalPages]);

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
          <div className="flex items-center gap-4 ml-4 flex-wrap">
            <label className="text-sm text-gray-600 flex items-center gap-2">
              Durum:
              <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value as any)} className="border rounded px-2 py-1 text-sm">
                <option value="all">Tümü</option>
                <option value="completed">Tamamlanan</option>
                <option value="pending">Bekleyen</option>
              </select>
            </label>
            <label className="text-sm text-gray-600 flex items-center gap-2">
              <input type="checkbox" checked={hasCvOnly} onChange={(e) => setHasCvOnly(e.target.checked)} />
              Sadece CV’si olanlar
            </label>
            <label className="text-sm text-gray-600 flex items-center gap-2">
              <input type="checkbox" checked={hasMediaOnly} onChange={(e) => setHasMediaOnly(e.target.checked)} />
              Sadece medyası olanlar
            </label>
            <label className="text-sm text-gray-600 flex items-center gap-2">
              Son güncelleme:
              <input type="date" value={dateFrom} onChange={(e) => setDateFrom(e.target.value)} className="border rounded px-2 py-1 text-sm" />
              –
              <input type="date" value={dateTo} onChange={(e) => setDateTo(e.target.value)} className="border rounded px-2 py-1 text-sm" />
            </label>
            <label className="text-sm text-gray-600 flex items-center gap-2">
              Süre (dk):
              <input
                type="number"
                placeholder="min"
                className="w-20 border rounded px-2 py-1 text-sm"
                value={minDurationMin}
                onChange={(e) => setMinDurationMin(e.target.value)}
              />
              –
              <input
                type="number"
                placeholder="max"
                className="w-20 border rounded px-2 py-1 text-sm"
                value={maxDurationMin}
                onChange={(e) => setMaxDurationMin(e.target.value)}
              />
            </label>
            <label className="text-sm text-gray-600 flex items-center gap-2">
              Sırala:
              <select value={sortBy} onChange={(e) => setSortBy(e.target.value as any)} className="border rounded px-2 py-1 text-sm">
                <option value="score">Genel Puan (yüksek→düşük)</option>
                <option value="created">Varsayılan</option>
                <option value="last_update_desc">Son güncelleme (en yeni)</option>
                <option value="last_update_asc">Son güncelleme (en eski)</option>
                <option value="duration_desc">Süre (en uzun)</option>
                <option value="duration_asc">Süre (en kısa)</option>
              </select>
            </label>
          </div>
        </div>

        {filteredSortedCandidates.length === 0 ? (
          <EmptyState title="Henüz aday yok" description="CV yükleyin veya aday oluşturarak davet göndermeye başlayın." />
        ) : (
        <div className="w-full overflow-x-auto">
        <table className="min-w-full divide-y divide-gray-200 dark:divide-neutral-800">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">ID</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">Ad Soyad</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">E-posta</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">View CV</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">Link</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">Durum</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">Süre</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">Son Güncelleme</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">Video</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">Rapor</th>
              {/* Scorecard kaldırıldı */}
            </tr>
          </thead>
          <tbody className="bg-white dark:bg-neutral-900 divide-y divide-gray-200 dark:divide-neutral-800">
            {filteredSortedCandidates
              .slice((pageNum-1)*10, (pageNum-1)*10 + 10)
              .map((c) => (
              <tr key={c.id} className="hover:bg-gray-50 dark:hover:bg-neutral-800">
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-300">#{c.id}</td>
                <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900 dark:text-neutral-100 flex items-center gap-2">
                  <span>{c.name}</span>
                  {(() => {
                    const it: any = findLatestInterview(c.id);
                    const score = typeof it?.overall_score === 'number' ? Math.round(it.overall_score) : null;
                    if (score === null) return null;
                    return <span className="ml-2 inline-flex items-center px-2 py-0.5 rounded-full text-xs bg-gray-100 text-gray-700">{score}/100</span>;
                  })()}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-300">{c.email}</td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-300">
                  {c.resume_url ? (
                    <Button variant="ghost" onClick={() => viewCv(c.id)} className="text-brand-700 hover:text-brand-900 p-0 h-auto">View CV</Button>
                  ) : (
                    <span className="text-gray-400">—</span>
                  )}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-300">
                  <Button variant="ghost" onClick={() => openInviteLinkForCandidate(c.id)} className="p-0 h-auto">Link</Button>
                </td>
                {(() => {
                  const it: any = findLatestInterview(c.id);
                  const status = it?.status || "—";
                  const dur = it?.completed_at ? formatDuration(it?.created_at, it?.completed_at) : "—";
                  const last = it?.completed_at || it?.created_at || null;
                  const badgeColor = status === "completed" ? "bg-emerald-100 text-emerald-700" : status === "pending" ? "bg-amber-100 text-amber-700" : "bg-gray-100 text-gray-600";
                  return (
                    <>
                      <td className="px-6 py-4 whitespace-nowrap text-xs"><span className={`px-2 py-1 rounded ${badgeColor}`}>{status}</span></td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-300">{dur}</td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-300">{last ? new Date(last).toLocaleString('tr-TR') : "—"}</td>
                    </>
                  );
                })()}
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-300">
                  <Button variant="ghost" onClick={() => openVideoForCandidate(c.id)} className="p-0 h-auto">Video</Button>
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-300 flex items-center gap-3">
                  <Button variant="ghost" onClick={() => openReportForCandidate(c.id)} className="p-0 h-auto">Rapor</Button>
                  {/* Delete candidate with confirm */}
                  <Dialog>
                    <DialogTrigger asChild>
                      <Button variant="ghost" className="p-0 h-auto" aria-label="Adayı sil">✕</Button>
                    </DialogTrigger>
                    <DialogContent>
                      <DialogHeader>
                        <DialogTitle>Adayı silmek istiyor musunuz?</DialogTitle>
                        <DialogDescription>Bu işlem geri alınamaz.</DialogDescription>
                      </DialogHeader>
                      <div className="flex justify-end gap-2">
                        <DialogClose asChild>
                          <Button variant="outline">Vazgeç</Button>
                        </DialogClose>
                        <Button
                          variant="outline"
                          className="bg-rose-600 text-white hover:bg-rose-700 border-rose-600"
                          onClick={async () => {
                            try {
                              await apiFetch(`/api/v1/candidates/${c.id}`, { method: 'DELETE' });
                              await refreshData();
                            } catch (err) {
                              toastError((err as any)?.message || 'Silme başarısız');
                            }
                          }}
                        >Sil</Button>
                      </div>
                    </DialogContent>
                  </Dialog>
                </td>
                {/* Scorecard aksiyonu kaldırıldı */}
              </tr>
            ))}
          </tbody>
        </table>
        </div>
        )}
      </div>

      {/* Pagination controls */}
      <div className="flex items-center justify-end gap-2 mt-4">
        <Button variant="outline" size="sm" onClick={() => setPageNum((p)=> Math.max(1, p-1))} disabled={pageNum<=1}>Önceki</Button>
        <span className="text-sm text-gray-500">Sayfa {pageNum} / {totalPages}</span>
        <Button variant="outline" size="sm" onClick={() => setPageNum((p)=> Math.min(totalPages, p+1))} disabled={pageNum>=totalPages}>Sonraki</Button>
      </div>

      {/* Report Modal */}
      <Dialog open={reportOpen} onOpenChange={setReportOpen}>
        <DialogContent className="max-w-4xl w-[90vw]">
          <DialogHeader>
            <DialogTitle>Aday Raporu</DialogTitle>
            <DialogDescription>
              İşe uygunluk, HR kriterleri ve soft-skill özetleri.
            </DialogDescription>
          </DialogHeader>
          <div className="flex justify-end mb-2 print:hidden">
            <Button variant="outline" onClick={exportReportPdf}>PDF Olarak Kaydet</Button>
          </div>
          {reportLoading ? (
            <div className="py-6 text-sm text-gray-500">Yükleniyor…</div>
          ) : reportAnalysis ? (
            <div className="space-y-4 max-h-[70vh] overflow-y-auto">
              {(() => {
                const a = reportAnalysis;
                return (
                  <div className="space-y-6">
                    {a.overall_score && (
                      <div>
                        <span className="text-sm font-medium text-gray-700">Genel Puan</span>
                        <div className="mt-1">
                          <div className="w-full bg-gray-200 rounded-full h-2">
                            <div className="bg-brand-600 h-2 rounded-full" style={{ width: `${a.overall_score}%` }}></div>
                          </div>
                          <span className="text-sm text-gray-600">{a.overall_score}/100</span>
                        </div>
                      </div>
                    )}
                    {/* AI Opinion */}
                    {(() => {
                      try {
                        const ta = a.technical_assessment ? JSON.parse(a.technical_assessment) : null;
                        const op = ta && ta.ai_opinion ? ta.ai_opinion : null;
                        if (!op || !(op.opinion_label || op.opinion_text)) return null;
                        return (
                          <div className="p-3 rounded-md bg-amber-50 border border-amber-200">
                            <div className="text-sm font-medium text-amber-900">Yapay Zeka Görüşü: {op.opinion_label || '—'}</div>
                            {op.opinion_text && <p className="text-sm text-amber-900 mt-1">{op.opinion_text}</p>}
                          </div>
                        );
                      } catch { return null; }
                    })()}
                    {a.summary && (
                      <div>
                        <span className="text-sm font-medium text-gray-700">Özet</span>
                        <p className="text-sm text-gray-600 mt-1">{a.summary}</p>
                      </div>
                    )}
                    {(typeof a.communication_score === 'number' || typeof a.technical_score === 'number' || typeof a.cultural_fit_score === 'number') && (
                      <div>
                        <span className="text-sm font-medium text-gray-700">Yetkinlik Puanları</span>
                        <div className="mt-2 space-y-2">
                          {typeof a.communication_score === 'number' && (
                            <div>
                              <div className="flex justify-between text-xs text-gray-600"><span>İletişim</span><span>{a.communication_score}/100</span></div>
                              <div className="w-full bg-gray-200 rounded-full h-2"><div className="bg-brand-600 h-2 rounded-full" style={{ width: `${a.communication_score}%` }}></div></div>
                            </div>
                          )}
                          {typeof a.technical_score === 'number' && (
                            <div>
                              <div className="flex justify-between text-xs text-gray-600"><span>Teknik</span><span>{a.technical_score}/100</span></div>
                              <div className="w-full bg-gray-200 rounded-full h-2"><div className="bg-brand-600 h-2 rounded-full" style={{ width: `${a.technical_score}%` }}></div></div>
                            </div>
                          )}
                          {typeof a.cultural_fit_score === 'number' && (
                            <div>
                              <div className="flex justify-between text-xs text-gray-600"><span>Kültürel Uyum</span><span>{a.cultural_fit_score}/100</span></div>
                              <div className="w-full bg-gray-200 rounded-full h-2"><div className="bg-brand-600 h-2 rounded-full" style={{ width: `${a.cultural_fit_score}%` }}></div></div>
                            </div>
                          )}
                        </div>
                        {/* HR ortalaması (görüntüleme için, varsa) */}
                        {(() => {
                          try {
                            const ta = a.technical_assessment ? JSON.parse(a.technical_assessment) : null;
                            const arr = ta && ta.hr_criteria && Array.isArray(ta.hr_criteria.criteria) ? ta.hr_criteria.criteria : [];
                            if (!arr.length) return null;
                            const valid = arr.filter((c:any)=> typeof c.score_0_100 === 'number');
                            if (!valid.length) return null;
                            const avg = Math.round(valid.reduce((s:any,c:any)=> s + c.score_0_100, 0) / valid.length);
                            return (
                              <div className="mt-4">
                                <span className="text-sm font-medium text-gray-700">HR Ortalama</span>
                                <div className="w-full bg-gray-200 rounded-full h-2 mt-1"><div className="bg-brand-600 h-2 rounded-full" style={{ width: `${avg}%` }}></div></div>
                                <span className="text-sm text-gray-600">{avg}/100</span>
                              </div>
                            );
                          } catch {
                            return null;
                          }
                        })()}
                      </div>
                    )}
                    {(() => {
                      try {
                        const ta = a.technical_assessment ? JSON.parse(a.technical_assessment) : null;
                        if (!ta) return null;
                        return (
                          <div className="space-y-6">
                            {Array.isArray(ta.soft_skills) && ta.soft_skills.length > 0 && (
                              <div>
                                <span className="text-sm font-medium text-gray-700">Soft Skills</span>
                                <ul className="mt-2 space-y-1 list-disc list-inside text-sm text-gray-700">
                                  {ta.soft_skills.map((s: any, idx: number) => (
                                    <li key={idx}><strong>{s.label}</strong>{typeof s.confidence === 'number' ? ` (${Math.round(s.confidence*100)}%)` : ''}{s.evidence ? ` — ${s.evidence}` : ''}</li>
                                  ))}
                                </ul>
                              </div>
                            )}
                            {ta.hr_criteria && Array.isArray(ta.hr_criteria.criteria) && (
                              <div>
                                <span className="text-sm font-medium text-gray-700">HR Kriterleri</span>
                                <ul className="mt-2 space-y-1 list-disc list-inside text-sm text-gray-700">
                                  {ta.hr_criteria.criteria.map((c: any, idx: number) => (
                                    <li key={idx}><strong>{c.label}</strong>{typeof c.score_0_100 === 'number' ? `: ${c.score_0_100}/100` : ''}{c.evidence ? ` — ${c.evidence}` : ''}</li>
                                  ))}
                                </ul>
                                {ta.hr_criteria.summary && <p className="text-sm text-gray-600 mt-1">{ta.hr_criteria.summary}</p>}
                              </div>
                            )}
                            {ta.job_fit && Array.isArray(ta.job_fit.recommendations) && ta.job_fit.recommendations.length > 0 && (
                              <div>
                                <span className="text-sm font-medium text-gray-700">Öneriler</span>
                                <ul className="mt-2 space-y-1 list-disc list-inside text-sm text-gray-700">
                                  {ta.job_fit.recommendations.map((r: any, idx: number) => (<li key={idx}>{r}</li>))}
                                </ul>
                              </div>
                            )}
                            {ta.job_fit && (
                              <div>
                                <span className="text-sm font-medium text-gray-700">İşe Uygunluk</span>
                                {ta.job_fit.job_fit_summary && <p className="text-sm text-gray-600 mt-1">{ta.job_fit.job_fit_summary}</p>}
                                {Array.isArray(ta.job_fit.requirements_matrix) && ta.job_fit.requirements_matrix.length > 0 && (
                                  <div className="mt-2">
                                    <span className="text-xs font-medium text-gray-600">Gereksinim Karşılama</span>
                                    <div className="mt-2 grid grid-cols-1 md:grid-cols-2 gap-2">
                                      {ta.job_fit.requirements_matrix.map((r:any, i:number) => (
                                        <div key={i} className="text-sm">
                                          <div className="flex items-center justify-between">
                                            <span className="font-medium">{r.label}</span>
                                            <span className={`${r.meets==='yes'?'bg-emerald-100 text-emerald-700':r.meets==='partial'?'bg-amber-100 text-amber-700':'bg-rose-100 text-rose-700'} text-xs px-2 py-0.5 rounded-full`}>{r.meets}</span>
                                          </div>
                                          {r.evidence && <div className="text-xs text-gray-600 mt-1">{r.evidence}</div>}
                                        </div>
                                      ))}
                                    </div>
                                  </div>
                                )}
                                {Array.isArray(ta.job_fit.key_matches) && ta.job_fit.key_matches.length > 0 && (
                                  <div className="mt-2">
                                    <span className="text-xs font-medium text-gray-600">Eşleşen Yönler</span>
                                    <ul className="list-disc list-inside text-sm text-gray-700">{ta.job_fit.key_matches.map((m: any, i: number) => (<li key={i}>{m}</li>))}</ul>
                                  </div>
                                )}
                                {Array.isArray(ta.job_fit.gaps) && ta.job_fit.gaps.length > 0 && (
                                  <div className="mt-2">
                                    <span className="text-xs font-medium text-gray-600">Açık Kalan Alanlar</span>
                                    <ul className="list-disc list-inside text-sm text-gray-700">{ta.job_fit.gaps.map((g: any, i: number) => (<li key={i}>{g}</li>))}</ul>
                                  </div>
                                )}
                                {Array.isArray(ta.job_fit.recommendations) && ta.job_fit.recommendations.length > 0 && (
                                  <div className="mt-2">
                                    <span className="text-xs font-medium text-gray-600">Öneriler</span>
                                    <ul className="list-disc list-inside text-sm text-gray-700">{ta.job_fit.recommendations.map((r: any, i: number) => (<li key={i}>{r}</li>))}</ul>
                                  </div>
                                )}
                              </div>
                            )}
                            {/* Gereksinim Karşılama kaldırıldı */}
                            {ta.meta && (
                              <div>
                                <span className="text-sm font-medium text-gray-700">Konuşma İstatistikleri</span>
                                <div className="mt-2 grid grid-cols-1 md:grid-cols-2 gap-3 text-sm text-gray-700">
                                  <div>Toplam Soru: <strong>{ta.meta.question_count ?? '—'}</strong></div>
                                  <div>Toplam Cevap: <strong>{ta.meta.answer_count ?? '—'}</strong></div>
                                  <div>Ortalama Cevap Uzunluğu: <strong>{ta.meta.avg_answer_length_words ?? '—'}</strong> kelime</div>
                                  <div>Dolgu Sözcük Sayısı: <strong>{ta.meta.filler_word_count ?? '—'}</strong></div>
                                  {typeof ta.meta.avg_answer_latency_seconds === 'number' && (
                                    <div>Ortalama Cevap Latency: <strong>{Math.round(ta.meta.avg_answer_latency_seconds)} sn</strong></div>
                                  )}
                                  {typeof ta.meta.avg_inter_question_gap_seconds === 'number' && (
                                    <div>Sorular Arası Ortalama Süre: <strong>{Math.round(ta.meta.avg_inter_question_gap_seconds)} sn</strong></div>
                                  )}
                                  {Array.isArray(ta.meta.top_keywords) && ta.meta.top_keywords.length > 0 && (
                                    <div className="md:col-span-2">Öne Çıkan Anahtar Kelimeler: <span>{ta.meta.top_keywords.join(', ')}</span></div>
                                  )}
                                </div>
                              </div>
                            )}
                          </div>
                        );
                      } catch (e) {
                        return null;
                      }
                    })()}
                  </div>
                );
              })()}
            </div>
          ) : (
            <div className="py-6 text-sm text-gray-500">Rapor bulunamadı</div>
          )}
          {/* Transcript toggle */}
          {reportInterviewId && (
            <details className="mt-4">
              <summary className="cursor-pointer text-sm text-brand-700">Transkripti Göster</summary>
              <TranscriptBlock interviewId={reportInterviewId} />
            </details>
          )}
        </DialogContent>
      </Dialog>
      {/* Scorecard Modal kaldırıldı */}

      {/* Invite Link Modal */}
      <Dialog open={inviteOpen} onOpenChange={setInviteOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Davet Linki</DialogTitle>
            <DialogDescription>Mail servisi devre dışı iken geçici olarak buradan kopyalayın.</DialogDescription>
          </DialogHeader>
          {inviteLoading ? (
            <div className="py-6 text-sm text-gray-500">Yükleniyor…</div>
          ) : inviteUrl ? (
            <div className="space-y-3">
              <input
                readOnly
                value={inviteUrl}
                className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm"
              />
              <div className="text-right">
                <Button
                  variant="outline"
                  onClick={async () => {
                    try { await navigator.clipboard.writeText(inviteUrl); success("Link kopyalandı"); } catch { /* ignore */ }
                  }}
                >Kopyala</Button>
              </div>
            </div>
          ) : (
            <div className="py-6 text-sm text-gray-500">Link alınamadı</div>
          )}
        </DialogContent>
      </Dialog>

      {/* Video Modal */}
      <Dialog open={videoOpen} onOpenChange={setVideoOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Video Mülakat</DialogTitle>
            <DialogDescription>Tarayıcıda oynatılır; isterseniz yeni sekmede de açabilirsiniz.</DialogDescription>
          </DialogHeader>
          {(() => {
            // Local refs via inline IIFE for brevity
            return (
              <div>
                {videoSrc ? (
                  <video id="admin-video-player" controls src={videoSrc} className="w-full max-h-[60vh] rounded" />
                ) : audioSrc ? (
                  <audio id="admin-audio-player" controls src={audioSrc} className="w-full" />
                ) : (
                  <div className="py-6 text-sm text-gray-500">Medya bulunamadı</div>
                )}
                {(videoSrc || audioSrc) && (
                  <div className="mt-2 flex items-center gap-3 text-sm">
                    <span>Zaman:</span>
                    <span id="time-display" className="min-w-[64px] inline-block">00:00</span>
                    <span className="ml-4">Hız:</span>
                    <select
                      onChange={(e) => {
                        const rate = Number(e.target.value);
                        const v = document.getElementById("admin-video-player") as HTMLVideoElement | null;
                        const a = document.getElementById("admin-audio-player") as HTMLAudioElement | null;
                        if (v) v.playbackRate = rate;
                        if (a) a.playbackRate = rate;
                      }}
                      className="border rounded px-2 py-1"
                    >
                      {[0.5, 0.75, 1, 1.25, 1.5, 2].map((r) => (
                        <option key={r} value={r}>{r}x</option>
                      ))}
                    </select>
                  </div>
                )}
                <script dangerouslySetInnerHTML={{ __html: `
                  (function(){
                    function fmt(t){
                      var m = Math.floor(t/60); var s = Math.floor(t%60);
                      return String(m).padStart(2,'0')+':'+String(s).padStart(2,'0');
                    }
                    var v = document.getElementById('admin-video-player');
                    var a = document.getElementById('admin-audio-player');
                    var t = document.getElementById('time-display');
                    function tick(){ if(!t) return; var cur = 0; var dur = 0; if(v){cur=v.currentTime; dur=v.duration||0;} if(a){cur=a.currentTime; dur=a.duration||0;} t.textContent = fmt(cur)+' / '+(isFinite(dur)?fmt(dur):'--:--'); }
                    if(v){ v.addEventListener('timeupdate', tick); v.addEventListener('loadedmetadata', tick); }
                    if(a){ a.addEventListener('timeupdate', tick); a.addEventListener('loadedmetadata', tick); }
                    tick();
                  })();
                `}} />
              </div>
            );
          })()}
          {(videoSrc || audioSrc) && (
            <div className="mt-2 text-right">
              <a href={videoSrc || audioSrc || "#"} target="_blank" rel="noreferrer" className="text-brand-700">Yeni sekmede aç</a>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
} 