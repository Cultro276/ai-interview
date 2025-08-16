"use client";
import { useDashboard } from "@/context/DashboardContext";
import { useToast } from "@/context/ToastContext";
import { apiFetch } from "@/lib/api";
import { useState } from "react";

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
  const { error: toastError, success, info } = useToast();
  const [transcriptText, setTranscriptText] = useState("");
  const [transcriptLoading, setTranscriptLoading] = useState(false);
  const [transcriptSaving, setTranscriptSaving] = useState(false);

  const viewConversation = async (interviewId: number) => {
    setSelectedInterview(interviewId);
    setLoadingConversation(true);
    setTranscriptText("");
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
      toastError("Failed to load conversation data");
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
      toastError(e.message || "Failed to (re)generate analysis");
    } finally {
      setGenerating(false);
    }
  };

  const loadTranscript = async (interviewId: number) => {
    setTranscriptLoading(true);
    try {
      const data = await apiFetch<{ interview_id: number; text: string }>(`/api/v1/interviews/${interviewId}/transcript`);
      setTranscriptText(data.text || "");
      success("Transcript loaded");
    } catch (e: any) {
      const local = typeof window !== 'undefined' ? localStorage.getItem(`transcript:${interviewId}`) : null;
      if (local) {
        setTranscriptText(local);
        info("Loaded transcript from local cache");
      } else {
        toastError(e.message || "Transcript not available yet");
      }
    } finally {
      setTranscriptLoading(false);
    }
  };

  const saveTranscript = async (interviewId: number) => {
    setTranscriptSaving(true);
    try {
      await apiFetch(`/api/v1/interviews/${interviewId}/transcript`, {
        method: "POST",
        body: JSON.stringify({ text: transcriptText, provider: "manual" }),
      });
      success("Transcript saved");
      if (typeof window !== 'undefined') localStorage.removeItem(`transcript:${interviewId}`);
    } catch (e: any) {
      if (typeof window !== 'undefined') localStorage.setItem(`transcript:${interviewId}`, transcriptText || "");
      info("Transcript saved locally (backend pending)");
    } finally {
      setTranscriptSaving(false);
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

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
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
              <button
                onClick={() => downloadCv(cand.id)}
                className="px-3 py-1 text-sm bg-emerald-600 text-white rounded-md hover:bg-emerald-700"
              >
                Download CV
              </button>
            )}
            <button
              onClick={() => setSelectedInterview(null)}
              className="px-4 py-2 bg-gray-600 text-white rounded-lg hover:bg-gray-700 font-medium"
            >
              ← Back to Interviews
            </button>
          </div>
        </div>

        {loadingConversation ? (
          <div className="text-center py-8">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto mb-4"></div>
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
                              ? "bg-blue-50 border-l-4 border-blue-400"
                              : message.role === "user"
                              ? "bg-green-50 border-l-4 border-green-400"
                              : "bg-gray-50 border-l-4 border-gray-400"
                          }`}
                        >
                          <div className="flex justify-between items-start mb-2">
                            <span className={`text-sm font-medium ${
                              message.role === "assistant" ? "text-blue-700" :
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
            <div className="lg:col-span-1 space-y-6">
              <div className="bg-white border border-gray-200 rounded-lg">
                <div className="px-6 py-4 border-b border-gray-200 flex items-center justify-between">
                  <h3 className="text-lg font-medium text-gray-900">AI Analysis</h3>
                  {selectedInterview && (
                    <button
                      onClick={() => regenerateAnalysis(selectedInterview)}
                      disabled={generating}
                      className="px-3 py-1 text-sm bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50"
                    >
                      {generating ? "Generating…" : "Regenerate"}
                    </button>
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
                                className="bg-blue-600 h-2 rounded-full" 
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
                          <p className="text-lg font-semibold text-blue-600">{analysis.communication_score}/100</p>
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

                      {/* Recommendation badge */}
                      {typeof analysis.overall_score === 'number' && (
                        <div>
                          <span className="text-sm font-medium text-gray-700">Recommended Decision</span>
                          <div className="mt-1">
                            {(() => {
                              const s = analysis.overall_score || 0;
                              const dec = s >= 75 ? 'Proceed' : s >= 60 ? 'Consider' : 'Review';
                              const cls = s >= 75 ? 'bg-green-100 text-green-800' : s >= 60 ? 'bg-yellow-100 text-yellow-800' : 'bg-rose-100 text-rose-800';
                              return <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${cls}`}>{dec}</span>;
                            })()}
                          </div>
                        </div>
                      )}
                    </div>
                  ) : (
                    <p className="text-gray-500">No analysis available. Analysis will be generated automatically after interview completion.</p>
                  )}
                </div>
              </div>
              {/* Transcript Stub */}
              <div className="bg-white border border-gray-200 rounded-lg">
                <div className="px-6 py-4 border-b border-gray-200 flex items-center justify-between">
                  <h3 className="text-lg font-medium text-gray-900">Transcript (Manual)</h3>
                  {selectedInterview && (
                    <div className="flex items-center gap-2">
                      <button
                        onClick={() => loadTranscript(selectedInterview)}
                        disabled={transcriptLoading}
                        className="px-3 py-1 text-sm bg-gray-100 text-gray-800 rounded-md hover:bg-gray-200 disabled:opacity-50"
                      >
                        {transcriptLoading ? "Loading…" : "Load"}
                      </button>
                      <button
                        onClick={async () => {
                          try {
                            await navigator.clipboard.writeText(transcriptText || "");
                            success("Transcript copied");
                          } catch {
                            toastError("Copy failed");
                          }
                        }}
                        className="px-3 py-1 text-sm bg-indigo-600 text-white rounded-md hover:bg-indigo-700"
                      >
                        Copy
                      </button>
                      <button
                        onClick={() => saveTranscript(selectedInterview)}
                        disabled={transcriptSaving}
                        className="px-3 py-1 text-sm bg-emerald-600 text-white rounded-md hover:bg-emerald-700 disabled:opacity-50"
                      >
                        {transcriptSaving ? "Saving…" : "Save"}
                      </button>
                    </div>
                  )}
                </div>
                <div className="p-6">
                  <textarea
                    value={transcriptText}
                    onChange={(e) => setTranscriptText(e.target.value)}
                    rows={10}
                    placeholder="Paste or type transcript here…"
                    className="w-full px-3 py-2 border border-gray-300 rounded-md"
                  />
                  <p className="text-xs text-gray-500 mt-2">This is a temporary manual transcript input. When backend transcript API is live, data will be stored server-side.</p>
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
                      className="text-blue-600 hover:text-blue-900 mr-4"
                    >
                      View Info
                    </button>
                    {interview.audio_url && (
                      <a 
                        href={interview.audio_url} 
                        target="_blank" 
                        rel="noopener noreferrer"
                        className="text-green-600 hover:text-green-900 mr-4"
                      >
                        Audio
                      </a>
                    )}
                    {interview.video_url && (
                      <a 
                        href={interview.video_url} 
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