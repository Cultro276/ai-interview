"use client";
import { useDashboard } from "@/context/DashboardContext";
import { apiFetch } from "@/lib/api";
import { useState } from "react";
import { Button } from "@/components/ui/Button";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger, DialogDescription } from "@/components/ui/dialog";
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger, DropdownMenuSeparator } from "@/components/ui/dropdown-menu";
import { Loader } from "@/components/ui/Loader";
import { EmptyState } from "@/components/ui/EmptyState";
import { Badge } from "@/components/ui/Badge";
import { Input } from "@/components/ui/Input";
import { useToast } from "@/context/ToastContext";

interface ConversationMessage {
  id: number;
  role: "assistant" | "user" | "system";
  content: string;
  timestamp: string;
  sequence_number: number;
}

interface InterviewAnalysis {
  id: number;
  interview_id: number;
  overall_score?: number;
  summary?: string;
  strengths?: string;
  weaknesses?: string;
  technical_assessment?: string;
  communication_score?: number;
  technical_score?: number;
  cultural_fit_score?: number;
  model_used?: string;
  created_at: string;
}

export default function InterviewsPage() {
  const { interviews, candidates, jobs, loading } = useDashboard();
  const { error: toastError, success: toastSuccess } = useToast();
  const [selectedInterview, setSelectedInterview] = useState<number | null>(null);
  const [conversationMessages, setConversationMessages] = useState<ConversationMessage[]>([]);
  const [analysis, setAnalysis] = useState<InterviewAnalysis | null>(null);
  const [loadingConversation, setLoadingConversation] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [sendingFinal, setSendingFinal] = useState(false);
  const [transcript, setTranscript] = useState<string>("");
  const [savingTranscript, setSavingTranscript] = useState(false);
  const [search, setSearch] = useState("");

  const viewConversation = async (interviewId: number) => {
    setSelectedInterview(interviewId);
    setLoadingConversation(true);
    try {
      // Get conversation messages
      const messages = await apiFetch<ConversationMessage[]>(`/api/v1/conversations/messages/${interviewId}`);
      setConversationMessages(messages || []);
      
      // Try to get analysis
      try {
        const analysisData = await apiFetch<InterviewAnalysis>(`/api/v1/conversations/analysis/${interviewId}`);
        setAnalysis(analysisData);
      } catch (error) {
        console.log("No analysis found for this interview");
        setAnalysis(null);
      }
    } catch (error: any) {
      console.error("Failed to load conversation:", error);
      toastError(error?.message || "Konuşma verileri yüklenemedi");
    } finally {
      setLoadingConversation(false);
    }
  };

  const regenerateAnalysis = async (interviewId: number) => {
    setGenerating(true);
    try {
      // Recreate analysis via the same endpoint (PUT upsert)
      await apiFetch(`/api/v1/conversations/analysis/${interviewId}`, {
        method: "PUT",
        body: JSON.stringify({ interview_id: interviewId }),
      });
      // Reload analysis panel
      const analysisData = await apiFetch<InterviewAnalysis>(`/api/v1/conversations/analysis/${interviewId}`);
      setAnalysis(analysisData);
    } catch (e: any) {
      toastError(e.message || "Analiz oluşturulamadı");
    } finally {
      setGenerating(false);
    }
  };

  const loadTranscript = async (interviewId: number) => {
    try {
      const res = await apiFetch<{ interview_id: number; text: string }>(`/api/v1/interviews/${interviewId}/transcript`);
      setTranscript(res?.text || "");
    } catch (e) {
      setTranscript("");
    }
  };

  const saveTranscript = async (interviewId: number) => {
    setSavingTranscript(true);
    try {
      await apiFetch(`/api/v1/interviews/${interviewId}/transcript`, {
        method: "POST",
        body: JSON.stringify({ text: transcript, provider: "manual" }),
      });
    } catch (e) {
      // toast can be added via ToastContext if desired
    } finally {
      setSavingTranscript(false);
    }
  };

  const viewCv = async (candidateId: number) => {
    try {
      const { url } = await apiFetch<{ url: string }>(`/api/v1/candidates/${candidateId}/resume-download-url`);
      // Open in new tab for inline view; most browsers will preview PDFs
      window.open(url, "_blank", "noopener,noreferrer");
    } catch (e: any) {
      toastError(e.message || "İndirme başarısız oldu");
    }
  };

  const downloadCv = async (candidateId: number) => {
    try {
      const { url } = await apiFetch<{ url: string }>(`/api/v1/candidates/${candidateId}/resume-download-url`);
      // Force download by adding content-disposition where possible via link trick
      const a = document.createElement('a');
      a.href = url;
      a.download = "cv.pdf";
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
    } catch (e: any) {
      toastError(e.message || "İndirme başarısız oldu");
    }
  };

  const sendFinalInvite = async (candidateId: number) => {
    setSendingFinal(true);
    try {
      await apiFetch(`/api/v1/candidates/${candidateId}/notify-final`, { method: "POST" });
      toastSuccess("Final mülakat daveti gönderildi");
    } catch (e: any) {
      toastError(e.message || "Final davet gönderilemedi");
    } finally {
      setSendingFinal(false);
    }
  };

  if (loading) {
    return <Loader label="Loading interviews..." />;
  }

  if (selectedInterview) {
    const intv = interviews.find(i => i.id === selectedInterview);
    const cand = candidates.find(c => c.id === intv?.candidate_id);
    return (
  <div>
        <div className="flex justify-between items-center mb-6">
          <h1 className="text-2xl font-bold text-gray-900 dark:text-neutral-100">Mülakat Görüşmesi</h1>
          <div className="flex items-center gap-3">
            {cand && cand.resume_url && (
              <div className="flex items-center gap-2">
                <Button
                  onClick={() => viewCv(cand.id)}
                  className="bg-sky-600 hover:bg-sky-700"
                  size="sm"
                >
                  View CV
                </Button>
                <Button
                  onClick={() => downloadCv(cand.id)}
                  className="bg-emerald-600 hover:bg-emerald-700"
                  size="sm"
                >
                  Download CV
                </Button>
              </div>
            )}
            {cand && (
              <Button
                onClick={() => sendFinalInvite(cand.id)}
                disabled={sendingFinal}
                className="bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50"
                size="sm"
              >
                {sendingFinal ? "Sending…" : "Send Final Invite"}
              </Button>
            )}
            <Dialog>
              <DialogTrigger asChild>
                <Button variant="outline" size="sm" onClick={() => loadTranscript(selectedInterview!)}>Transkript</Button>
              </DialogTrigger>
              <DialogContent>
                <DialogHeader>
                  <DialogTitle>Transkript</DialogTitle>
                  <DialogDescription>
                    Bu görüşmeye ait transkript metnini görüntüleyin veya düzenleyin.
                  </DialogDescription>
                </DialogHeader>
                <div className="space-y-3">
                  <textarea
                    value={transcript}
                    onChange={(e) => setTranscript(e.target.value)}
                    rows={8}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md"
                    placeholder="Paste or edit transcript text here"
                  />
                  <div className="flex justify-end gap-2">
                    <Button variant="ghost" onClick={() => loadTranscript(selectedInterview!)}>Yenile</Button>
                    <Button onClick={() => saveTranscript(selectedInterview!)} disabled={savingTranscript}>
                      {savingTranscript ? "Kaydediliyor…" : "Kaydet"}
                    </Button>
                  </div>
                </div>
              </DialogContent>
            </Dialog>
            <Button onClick={() => setSelectedInterview(null)} variant="secondary" size="sm">
              ← Mülakatlara Dön
            </Button>
          </div>
        </div>

        {loadingConversation ? (
          <Loader label="Loading conversation..." />
        ) : (
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Conversation Messages */}
            <div className="lg:col-span-2">
              <div className="bg-white border border-gray-200 rounded-lg">
                <div className="px-6 py-4 border-b border-gray-200">
                  <h3 className="text-lg font-medium text-gray-900">Görüşme Transkripti</h3>
                </div>
                <div className="p-6 max-h-96 overflow-y-auto">
                  {conversationMessages.length === 0 ? (
                    <EmptyState title="Konuşma bulunamadı" description="Bu mülakata ait mesaj henüz yok." />
                  ) : (
                    <div className="space-y-4">
                      {conversationMessages.map((message) => (
                        <div
                          key={message.id}
                          className={`p-3 rounded-lg ${
                            message.role === "assistant"
                              ? "bg-brand-25 border-l-4 border-brand-400"
                              : message.role === "user"
                              ? "bg-green-50 border-l-4 border-green-400"
                              : "bg-gray-50 border-l-4 border-gray-400"
                          }`}
                        >
                          <div className="flex justify-between items-start mb-2">
                            <span className={`text-sm font-medium ${
                              message.role === "assistant" ? "text-brand-700" :
                              message.role === "user" ? "text-green-700" : "text-gray-700"
                            }`}>
                              {message.role === "assistant" ? "🤖 Yapay Zeka" : 
                               message.role === "user" ? "👤 Aday" : "⚙️ Sistem"}
                            </span>
                            <span className="text-xs text-gray-500">
                              {new Date(message.timestamp).toLocaleTimeString()}
                            </span>
                          </div>
                          <p className="text-gray-800">{message.content}</p>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            </div>

            {/* Analysis Panel */}
            <div className="lg:col-span-1">
              <div className="bg-white border border-gray-200 rounded-lg">
                <div className="px-6 py-4 border-b border-gray-200 flex items-center justify-between">
                  <h3 className="text-lg font-medium text-gray-900">AI Analysis</h3>
                  {selectedInterview && (
                    <Dialog>
                      <DialogTrigger asChild>
                        <Button disabled={generating} size="sm">{generating ? "Generating…" : "Regenerate"}</Button>
                      </DialogTrigger>
                      <DialogContent>
                        <DialogHeader>
                          <DialogTitle>Regenerate analysis?</DialogTitle>
                          <DialogDescription>
                            Bu işlem mevcut analizi günceller. Devam etmek istediğinize emin misiniz?
                          </DialogDescription>
                        </DialogHeader>
                        <div className="flex justify-end gap-2">
                          <Button variant="ghost">Cancel</Button>
                          <Button onClick={() => regenerateAnalysis(selectedInterview)} disabled={generating}>
                            {generating ? "Generating…" : "Confirm"}
                          </Button>
                        </div>
                      </DialogContent>
                    </Dialog>
                  )}
                </div>
                <div className="p-6">
                  {/* Meta */}
                  <div className="mb-4 text-sm text-gray-600">
                    {(() => {
                      const intv = interviews.find(i => i.id === selectedInterview);
                      if (!intv) return null;
                      return (
                        <div className="flex gap-6 flex-wrap">
                          <span><strong>Completed At:</strong> {(intv as any)?.completed_at ? new Date((intv as any).completed_at).toLocaleString() : "—"}</span>
                          <span><strong>IP:</strong> {(intv as any)?.completed_ip || "—"}</span>
                        </div>
                      );
                    })()}
                  </div>
                  {analysis ? (
                    <div className="space-y-4">
                      {analysis.overall_score && (
                        <div>
                          <span className="text-sm font-medium text-gray-700">Genel Puan</span>
                          <div className="mt-1">
                            <div className="w-full bg-gray-200 rounded-full h-2">
                              <div 
                                className="bg-brand-600 h-2 rounded-full" 
                                style={{ width: `${analysis.overall_score}%` }}
                              ></div>
                            </div>
                            <span className="text-sm text-gray-600">{analysis.overall_score}/100</span>
                          </div>
                        </div>
                      )}
                      {analysis.communication_score && (
                        <div>
                          <span className="text-sm font-medium text-gray-700">İletişim</span>
                          <p className="text-lg font-semibold text-brand-600">{analysis.communication_score}/100</p>
                        </div>
                      )}
                      {analysis.technical_score && (
                        <div>
                          <span className="text-sm font-medium text-gray-700">Teknik Yetenek</span>
                          <p className="text-lg font-semibold text-green-600">{analysis.technical_score}/100</p>
                        </div>
                      )}
                      {analysis.cultural_fit_score && (
                        <div>
                          <span className="text-sm font-medium text-gray-700">Kültürel Uyum</span>
                          <p className="text-lg font-semibold text-purple-600">{analysis.cultural_fit_score}/100</p>
                        </div>
                      )}
                      {analysis.summary && (
                        <div>
                          <span className="text-sm font-medium text-gray-700">Özet</span>
                          <p className="text-sm text-gray-600 mt-1">{analysis.summary}</p>
                        </div>
                      )}
                      {analysis.strengths && (
                        <div>
                          <span className="text-sm font-medium text-gray-700">Güçlü Yönler</span>
                          <p className="text-sm text-gray-600 mt-1">{analysis.strengths}</p>
                        </div>
                      )}
                      {analysis.weaknesses && (
                        <div>
                          <span className="text-sm font-medium text-gray-700">Gelişim Alanları</span>
                          <p className="text-sm text-gray-600 mt-1">{analysis.weaknesses}</p>
                        </div>
                      )}
                    </div>
                  ) : (
                    <p className="text-gray-500">Analiz bulunamadı. Mülakat tamamlandıktan sonra otomatik oluşturulacaktır.</p>
                  )}
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    );
  }

  return (
    <div>
      <div className="flex justify-between items-center mb-6 gap-4">
        <h1 className="text-2xl font-bold text-gray-900 dark:text-neutral-100">Mülakatlar</h1>
        <div className="w-full max-w-xs ml-auto">
          <Input
            placeholder="ID, aday veya iş ile ara"
            aria-label="Mülakat ara"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
      </div>

      {interviews.length === 0 ? (
        <EmptyState
          title="No interviews yet"
          description="Interviews will appear here once candidates start interviewing."
          actionLabel="Go to Jobs"
          onAction={() => (window.location.href = "/jobs")}
        />
      ) : (
      <div className="bg-white dark:bg-neutral-900 border border-gray-200 dark:border-neutral-800 rounded-lg overflow-hidden">
        <div className="w-full overflow-x-auto">
        <table className="min-w-full divide-y divide-gray-200 dark:divide-neutral-800">
          <thead className="bg-gray-50">
            <tr>
              <th className="sticky top-0 z-10 bg-gray-50 dark:bg-neutral-900 px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                Mülakat ID
              </th>
              <th className="sticky top-0 z-10 bg-gray-50 dark:bg-neutral-900 px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                Aday
              </th>
              <th className="sticky top-0 z-10 bg-gray-50 dark:bg-neutral-900 px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider hidden sm:table-cell">
                Pozisyon
              </th>
              <th className="sticky top-0 z-10 bg-gray-50 dark:bg-neutral-900 px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                Durum
              </th>
              <th className="sticky top-0 z-10 bg-gray-50 dark:bg-neutral-900 px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider hidden md:table-cell">
                Tarih
              </th>
              <th className="sticky top-0 z-10 bg-gray-50 dark:bg-neutral-900 px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                İşlemler
              </th>
            </tr>
          </thead>
          <tbody className="bg-white dark:bg-neutral-900 divide-y divide-gray-200 dark:divide-neutral-800">
            {interviews
              .filter((interview) => {
                const q = search.trim().toLowerCase();
                if (!q) return true;
                const candidate = candidates.find(c => c.id === interview.candidate_id);
                const job = jobs.find(j => j.id === interview.job_id);
                return (
                  String(interview.id).includes(q) ||
                  (candidate?.name || "").toLowerCase().includes(q) ||
                  (job?.title || "").toLowerCase().includes(q)
                );
              })
              .map((interview) => {
              const candidate = candidates.find(c => c.id === interview.candidate_id);
              const job = jobs.find(j => j.id === interview.job_id);
              return (
                <tr key={interview.id} className="hover:bg-gray-50 dark:hover:bg-neutral-800">
                  <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900 dark:text-neutral-100">
                    #{interview.id}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-300">
                    {candidate?.name || "Unknown"}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-300 hidden sm:table-cell">
                    {job?.title || "Unknown"}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <Badge variant={interview.status === "completed" ? "success" : "warning"}>{interview.status}</Badge>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-300 hidden md:table-cell">
                    {new Date(interview.created_at).toLocaleDateString('tr-TR')}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm font-medium">
                    <DropdownMenu>
                      <DropdownMenuTrigger asChild>
                        <Button variant="outline" size="sm">İşlemler</Button>
                      </DropdownMenuTrigger>
                      <DropdownMenuContent align="end">
                        <DropdownMenuItem onSelect={() => viewConversation(interview.id)}>Detayları Gör</DropdownMenuItem>
                        <DropdownMenuItem
                          onSelect={async () => {
                            try {
                              const { audio_url, video_url } = await apiFetch<{ audio_url?: string; video_url?: string }>(`/api/v1/interviews/${interview.id}/media-download-urls`);
                              if (audio_url) window.open(audio_url, "_blank", "noopener,noreferrer");
                              if (video_url) window.open(video_url, "_blank", "noopener,noreferrer");
                              if (!audio_url && !video_url) alert("No media available");
                            } catch (e: any) {
                              alert(e.message || "Failed to open media");
                            }
                          }}
                        >
                          Medyayı Aç
                        </DropdownMenuItem>
                      </DropdownMenuContent>
                    </DropdownMenu>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
        </div>
      </div>
      )}
    </div>
  );
} 