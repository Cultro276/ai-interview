"use client";
import { useDashboard } from "@/context/DashboardContext";
import { apiFetch } from "@/lib/api";
import { useState } from "react";
import { Button } from "@/components/ui/Button";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger, DropdownMenuSeparator } from "@/components/ui/dropdown-menu";

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
  const [selectedInterview, setSelectedInterview] = useState<number | null>(null);
  const [conversationMessages, setConversationMessages] = useState<ConversationMessage[]>([]);
  const [analysis, setAnalysis] = useState<InterviewAnalysis | null>(null);
  const [loadingConversation, setLoadingConversation] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [sendingFinal, setSendingFinal] = useState(false);
  const [transcript, setTranscript] = useState<string>("");
  const [savingTranscript, setSavingTranscript] = useState(false);

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
    } catch (error) {
      console.error("Failed to load conversation:", error);
      alert("Failed to load conversation data");
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
      alert(e.message || "Failed to (re)generate analysis");
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

  const downloadCv = async (candidateId: number) => {
    try {
      const { url } = await apiFetch<{ url: string }>(`/api/v1/candidates/${candidateId}/resume-download-url`);
      window.open(url, "_blank");
    } catch (e: any) {
      alert(e.message || "Download failed");
    }
  };

  const sendFinalInvite = async (candidateId: number) => {
    setSendingFinal(true);
    try {
      await apiFetch(`/api/v1/candidates/${candidateId}/notify-final`, { method: "POST" });
      alert("Final interview invite sent");
    } catch (e: any) {
      alert(e.message || "Failed to send final invite");
    } finally {
      setSendingFinal(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-brand-600 mx-auto mb-4"></div>
          <p className="text-gray-600">Loading interviews...</p>
        </div>
      </div>
    );
  }

  if (selectedInterview) {
    const intv = interviews.find(i => i.id === selectedInterview);
    const cand = candidates.find(c => c.id === intv?.candidate_id);
    return (
  <div>
        <div className="flex justify-between items-center mb-6">
          <h1 className="text-2xl font-bold text-gray-900">Interview Conversation</h1>
          <div className="flex items-center gap-3">
            {cand && cand.resume_url && (
              <Button
                onClick={() => downloadCv(cand.id)}
                className="bg-emerald-600 hover:bg-emerald-700"
                size="sm"
              >
                Download CV
              </Button>
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
                <Button variant="outline" size="sm" onClick={() => loadTranscript(selectedInterview!)}>Transcript</Button>
              </DialogTrigger>
              <DialogContent>
                <DialogHeader>
                  <DialogTitle>Transcript</DialogTitle>
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
                    <Button variant="ghost" onClick={() => loadTranscript(selectedInterview!)}>Reload</Button>
                    <Button onClick={() => saveTranscript(selectedInterview!)} disabled={savingTranscript}>
                      {savingTranscript ? "Saving…" : "Save"}
                    </Button>
                  </div>
                </div>
              </DialogContent>
            </Dialog>
            <Button onClick={() => setSelectedInterview(null)} variant="secondary" size="sm">
              ← Back to Interviews
            </Button>
          </div>
        </div>

        {loadingConversation ? (
          <div className="text-center py-8">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-brand-600 mx-auto mb-4"></div>
            <p>Loading conversation...</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Conversation Messages */}
            <div className="lg:col-span-2">
              <div className="bg-white border border-gray-200 rounded-lg">
                <div className="px-6 py-4 border-b border-gray-200">
                  <h3 className="text-lg font-medium text-gray-900">Conversation Transcript</h3>
                </div>
                <div className="p-6 max-h-96 overflow-y-auto">
                  {conversationMessages.length === 0 ? (
                    <p className="text-gray-500">No conversation data found.</p>
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
                              {message.role === "assistant" ? "🤖 AI" : 
                               message.role === "user" ? "👤 Candidate" : "⚙️ System"}
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
                  <h3 className="text-lg font_medium text-gray-900">AI Analysis</h3>
                  {selectedInterview && (
                    <Dialog>
                      <DialogTrigger asChild>
                        <Button disabled={generating} size="sm">{generating ? "Generating…" : "Regenerate"}</Button>
                      </DialogTrigger>
                      <DialogContent>
                        <DialogHeader>
                          <DialogTitle>Regenerate analysis?</DialogTitle>
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
                          <span className="text-sm font-medium text-gray-700">Overall Score</span>
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
                          <span className="text-sm font-medium text-gray-700">Communication</span>
                          <p className="text-lg font-semibold text-brand-600">{analysis.communication_score}/100</p>
                        </div>
                      )}
                      
                      {analysis.technical_score && (
                        <div>
                          <span className="text-sm font-medium text-gray-700">Technical Skills</span>
                          <p className="text-lg font-semibold text-green-600">{analysis.technical_score}/100</p>
                        </div>
                      )}
                      
                      {analysis.cultural_fit_score && (
                        <div>
                          <span className="text-sm font-medium text-gray-700">Cultural Fit</span>
                          <p className="text-lg font-semibold text-purple-600">{analysis.cultural_fit_score}/100</p>
                        </div>
                      )}
                      
                      {analysis.summary && (
                        <div>
                          <span className="text-sm font-medium text-gray-700">Summary</span>
                          <p className="text-sm text-gray-600 mt-1">{analysis.summary}</p>
                        </div>
                      )}
                      
                      {analysis.strengths && (
                        <div>
                          <span className="text-sm font-medium text-gray-700">Strengths</span>
                          <p className="text-sm text-gray-600 mt-1">{analysis.strengths}</p>
                        </div>
                      )}
                      
                      {analysis.weaknesses && (
                        <div>
                          <span className="text-sm font-medium text-gray-700">Areas for Improvement</span>
                          <p className="text-sm text-gray-600 mt-1">{analysis.weaknesses}</p>
                        </div>
                      )}
                    </div>
                  ) : (
                    <p className="text-gray-500">No analysis available. Analysis will be generated automatically after interview completion.</p>
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
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Interviews</h1>
      </div>

      <div className="bg-white border border-gray-200 rounded-lg overflow-hidden">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Interview ID
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Candidate
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Job Position
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Status
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Date
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Actions
              </th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {interviews.map((interview) => {
              const candidate = candidates.find(c => c.id === interview.candidate_id);
              const job = jobs.find(j => j.id === interview.job_id);
              return (
                <tr key={interview.id} className="hover:bg-gray-50">
                  <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                    #{interview.id}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    {candidate?.name || "Unknown"}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    {job?.title || "Unknown"}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${
                      interview.status === "completed" 
                        ? "bg-green-100 text-green-800"
                        : "bg-yellow-100 text-yellow-800"
                    }`}>
                      {interview.status}
                    </span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    {new Date(interview.created_at).toLocaleDateString()}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm font-medium">
                    <button 
                      onClick={() => viewConversation(interview.id)}
                      className="text-brand-700 hover:text-brand-900 mr-4"
                    >
                      View Info
                    </button>
                    {(interview as any).audio_url && (
                      <a 
                        href={(interview as any).audio_url} 
                        target="_blank" 
                        rel="noopener noreferrer"
                        className="text-green-600 hover:text-green-900 mr-4"
                      >
                        Audio
                      </a>
                    )}
                    {(interview as any).video_url && (
                      <a 
                        href={(interview as any).video_url} 
                        target="_blank" 
                        rel="noopener noreferrer"
                        className="text-purple-600 hover:text-purple-900"
                      >
                        Video
                      </a>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
  </div>
 );
} 